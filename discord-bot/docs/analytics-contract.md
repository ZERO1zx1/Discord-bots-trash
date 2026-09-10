# GuildPilot analytics contract

This contract separates reach, value, retention, and reliability so raw command volume cannot be reported as product success.

## Primary KPIs

| KPI | Definition | Calculation | Source | Decision cadence |
| --- | --- | --- | --- | --- |
| Weekly Value-Active Guilds | Eligible guilds with at least one successful production value event in the latest complete seven-day window | Distinct `guild_id` where an allowed value event succeeded | `analytics_events` joined to valid guild configuration state | Weekly product review |
| 14-Day Guild Activation Rate | Eligible installs that reach valid configuration and their first successful production value event within 14 days | Activated eligible installs / eligible installs with a complete observation window | `guilds`, `module_configs`, `analytics_events` | Weekly funnel review |
| Four-Week Retained Activated Guild Rate | Activated guilds that record at least one value event during their fourth complete week after activation | Retained activated guilds / activated guilds with a complete four-week window | Activation cohort derived from `analytics_events` | Monthly retention review |

No production target is assigned until enough baseline data exists. A missing baseline renders as an em dash and an explicit explanation, never zero-percent success or failure.

## Value events

The first release may treat only completed member or operator outcomes as value events:

- `welcome_flow_completed`
- `ticket_submitted`
- `ticket_resolved`
- `moderation_case_completed`
- `configuration_published`

Opening the dashboard, invoking `/status`, viewing a page, or clicking a navigation control is not a value event.

## Drivers

- time from eligible install to valid configuration;
- time from valid configuration to first value event;
- setup recovery completion after a permission error;
- configured guilds with at least one enabled production module.

## Guardrails

- Discord interaction success rate and error rate;
- P95 command response latency;
- permission-denied rate with successful recovery;
- audit-log coverage for every high-risk action;
- duplicate event and duplicate job rejection rate;
- deleted or paused guild data continuing to receive writes.

## Required event fields

Every analytics event includes:

- globally unique `event_id`;
- versioned snake-case `event_name`;
- optional `guild_id` and `actor_id` according to privacy policy;
- bounded JSON `properties` with no secrets or raw message bodies;
- authoritative `occurred_at` and ingestion `received_at` timestamps.

The schema is the source of calculation inputs. Dashboard labels are product copy, not independent metric definitions.

