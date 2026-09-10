-- GuildPilot core schema. The browser never receives direct access to these tables.
create extension if not exists pgcrypto;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

alter default privileges for role postgres in schema public
  revoke select, insert, update, delete on tables from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke usage, select on sequences from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated;

create table public.guilds (
  id text primary key,
  owner_id text not null default '',
  name text not null check (char_length(name) between 1 and 100),
  bot_installed boolean not null default false,
  configuration_state text not null default 'not_started'
    check (configuration_state in ('not_started', 'in_progress', 'valid', 'paused')),
  config_version integer not null default 0 check (config_version >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.guild_memberships (
  guild_id text not null references public.guilds(id) on delete cascade,
  user_id text not null,
  capability text not null
    check (capability in ('owner', 'administrator', 'moderator', 'community_manager', 'viewer')),
  source text not null default 'discord' check (source in ('discord', 'delegated')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (guild_id, user_id, capability)
);

create table public.module_configs (
  id uuid primary key default gen_random_uuid(),
  guild_id text not null references public.guilds(id) on delete cascade,
  module_key text not null check (module_key in ('welcome', 'tickets', 'safety', 'insights')),
  enabled boolean not null default false,
  version integer not null default 1 check (version > 0),
  config jsonb not null default '{}'::jsonb,
  created_by text,
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (guild_id, module_key)
);

create table public.tickets (
  id uuid primary key default gen_random_uuid(),
  guild_id text not null references public.guilds(id) on delete cascade,
  requester_id text not null,
  subject text not null check (char_length(subject) between 1 and 100),
  details text not null check (char_length(details) between 1 and 1000),
  status text not null default 'open' check (status in ('open', 'claimed', 'closed')),
  assigned_to text,
  discord_channel_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  closed_at timestamptz
);

create table public.audit_log (
  id uuid primary key default gen_random_uuid(),
  guild_id text references public.guilds(id) on delete set null,
  actor_id text,
  action text not null check (char_length(action) between 1 and 120),
  resource_type text not null check (char_length(resource_type) between 1 and 80),
  resource_id text,
  request_id text not null,
  before_state jsonb,
  after_state jsonb,
  occurred_at timestamptz not null default now(),
  unique (request_id, action)
);

create table public.analytics_events (
  event_id uuid primary key,
  guild_id text references public.guilds(id) on delete set null,
  actor_id text,
  event_name text not null check (event_name ~ '^[a-z][a-z0-9_]{1,79}$'),
  event_version smallint not null default 1 check (event_version > 0),
  properties jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now(),
  received_at timestamptz not null default now()
);

create table public.outbox (
  id uuid primary key default gen_random_uuid(),
  aggregate_type text not null,
  aggregate_id text not null,
  event_name text not null,
  event_version smallint not null default 1,
  idempotency_key text not null unique,
  payload jsonb not null,
  status text not null default 'pending' check (status in ('pending', 'processing', 'published', 'failed')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  available_at timestamptz not null default now(),
  published_at timestamptz,
  last_error text,
  created_at timestamptz not null default now()
);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null,
  idempotency_key text not null unique,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  max_attempts integer not null default 5 check (max_attempts between 1 and 25),
  available_at timestamptz not null default now(),
  locked_at timestamptz,
  locked_by text,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index guild_memberships_user_guild_idx on public.guild_memberships (user_id, guild_id);
create index module_configs_guild_enabled_idx on public.module_configs (guild_id, enabled);
create index tickets_guild_status_created_idx on public.tickets (guild_id, status, created_at desc);
create index audit_log_guild_occurred_idx on public.audit_log (guild_id, occurred_at desc);
create index analytics_events_guild_occurred_idx on public.analytics_events (guild_id, occurred_at desc);
create index analytics_events_name_occurred_idx on public.analytics_events (event_name, occurred_at desc);
create index outbox_dispatch_idx on public.outbox (status, available_at) where status in ('pending', 'failed');
create index jobs_poll_idx on public.jobs (status, available_at) where status in ('queued', 'failed');

create or replace function private.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke all on function private.set_updated_at() from public, anon, authenticated;
grant usage on schema private to service_role;
grant execute on function private.set_updated_at() to service_role;

create trigger guilds_set_updated_at before update on public.guilds
for each row execute function private.set_updated_at();
create trigger guild_memberships_set_updated_at before update on public.guild_memberships
for each row execute function private.set_updated_at();
create trigger module_configs_set_updated_at before update on public.module_configs
for each row execute function private.set_updated_at();
create trigger tickets_set_updated_at before update on public.tickets
for each row execute function private.set_updated_at();
create trigger jobs_set_updated_at before update on public.jobs
for each row execute function private.set_updated_at();

alter table public.guilds enable row level security;
alter table public.guild_memberships enable row level security;
alter table public.module_configs enable row level security;
alter table public.tickets enable row level security;
alter table public.audit_log enable row level security;
alter table public.analytics_events enable row level security;
alter table public.outbox enable row level security;
alter table public.jobs enable row level security;

revoke all on all tables in schema public from anon, authenticated;
grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to service_role;

comment on table public.analytics_events is
  'Immutable product and reliability events written by trusted server processes.';
comment on table public.audit_log is
  'Append-only record of high-risk or security-relevant changes.';
comment on table public.outbox is
  'Transactional integration events dispatched asynchronously and idempotently.';
