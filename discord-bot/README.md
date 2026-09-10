# GuildPilot

GuildPilot is a Discord community operations platform built as a process-separated modular monolith. One repository contains:

- a production Sites dashboard with an interactive Discord embed studio;
- a server-rendered Flask control plane and confidential Discord OAuth flow;
- a `discord.py` bot built around slash commands, buttons, selects, and modals;
- a Python worker boundary for asynchronous jobs;
- an RLS-enabled Supabase/Postgres schema, audit log, analytics events, outbox, and job queue.

The dashboard never receives a Supabase secret key or Discord client secret. The initial web architecture is server-mediated: browser requests go to Flask, Flask authorizes the actor and guild, and trusted server processes write to Supabase.

## Product experience

The Sites dashboard includes four focused surfaces:

1. **Overview** — launch readiness, truthful empty-state product health, and the next best setup action.
2. **Embed studio** — live editing of message purpose, module, title, and description with a Discord-style preview.
3. **Analytics** — canonical activation, value, retention, and reliability definitions without invented statistics.
4. **Settings** — a safe checklist of required server environment groups.

The bot includes:

- `/panel` — an administrator-only control panel with a persistent module select and action buttons;
- `/status` — an ephemeral operational status embed;
- `/ticket` — a guided modal followed by a success embed;
- consistent success, information, warning, and critical embed themes;
- request IDs, explicit recovery copy, and ephemeral administrative responses.

## Repository map

```text
app/                    Sites/vinext dashboard
bot/                    discord.py runtime, embeds, views, commands
docs/                   analytics and Discord design contracts
public/                 web assets and social preview
python_worker/          asynchronous worker boundary
server/                 Flask app, templates, static assets, OAuth, Supabase gateway
supabase/migrations/    RLS-enabled PostgreSQL migration
tests/                  rendered Sites tests
tests_py/               Flask, bot, and schema tests
worker/                 Cloudflare/Sites worker entry point
```

## Local setup

Requirements:

- Node.js 22.13 or later
- Python 3.11 or later
- `uv`
- a Discord application when testing real bot or OAuth flows
- a dedicated Supabase project when testing persistent data

Copy `.env.example` to `.env`, then fill only the services you intend to run. Never place a Supabase secret key in a `NEXT_PUBLIC_` variable or browser file.

Install and run the Sites dashboard:

```powershell
npm ci
npm run dev
```

Install and run the Python processes:

```powershell
uv sync --all-groups
uv run python -m server.run
uv run python -m bot.main
uv run python -m python_worker.main
```

The default local URLs are:

- Sites dashboard: `http://localhost:3000`
- Flask control plane: `http://localhost:5000`
- Flask health endpoint: `http://localhost:5000/api/health`

## Supabase

The migration was created with the official Supabase CLI and lives in `supabase/migrations/20260810033029_guildpilot_core.sql`.

Security posture:

- RLS is enabled on every `public` table.
- `anon` and `authenticated` receive no table access in the initial server-mediated architecture.
- `service_role` receives explicit table grants for trusted server processes.
- the only trigger helper is `SECURITY INVOKER` in a non-exposed `private` schema.
- no view bypasses RLS and no authorization decision uses user-editable metadata.
- audit, analytics, outbox, and job records have dedicated indexes for their main access paths.

Apply the migration only to a new or explicitly selected project. Do not point it at an unrelated project.

## Discord application

Recommended scopes:

- OAuth dashboard login: `identify guilds`
- bot invite: `bot applications.commands`

Recommended bot intents:

- Guilds only for the included commands. Message Content is not required.

Set `DISCORD_DEV_GUILD_ID` during development for fast guild-scoped command synchronization. Remove it for global command synchronization before production.

## Quality checks

```powershell
npm run build
npm run lint
node --test tests/rendered-html.test.mjs
uv run ruff check .
uv run pytest
```

Current automated coverage verifies:

- Sites server rendering and honest data labels;
- Flask readiness behavior, internal event authentication, and security headers;
- embed branding and persistent Discord component IDs;
- RLS coverage, revoked browser roles, explicit server grants, and absence of `SECURITY DEFINER`.

## Deployment shape

- **Sites:** deploys the public dashboard and embed studio from the validated vinext build.
- **Flask web:** deploy `gunicorn --bind 0.0.0.0:8080 server.run:app` as its own process.
- **Discord bot:** deploy `python -m bot.main` as a continuously running process.
- **Worker:** deploy `python -m python_worker.main` independently once job handlers are enabled.

The included `Dockerfile` defaults to the Flask process. Override the container command for the bot or worker so failures and scaling remain independent.

## Decisions intentionally deferred

- A new Supabase project requires organization and cost confirmation before creation.
- A GitHub repository can be published after a repository target or UI/CLI creation path is available.
- Provider token refresh storage and encryption should be added before long-lived Discord dashboard sessions.
- Production bot links must replace the local dashboard URL before launch.

See `docs/analytics-contract.md` and `docs/discord-interaction-design.md` for the implementation contracts behind the product UI.

