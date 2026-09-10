# GuildPilot Discord interaction design

## Visual contract

Every embed uses `BrandEmbeds` and one semantic accent:

| Purpose | Accent | Required behavior |
| --- | --- | --- |
| Success | `#57F287` | Confirm what completed and what the user can do next |
| Information | `#5865F2` | Explain state without implying success |
| Warning | `#FEE75C` | State the required recovery action in plain language |
| Critical | `#ED4245` | Reserve for failed or dangerous states; never for routine validation |

Each embed has a short author label, one outcome-focused title, compact description, optional fields, and a footer containing a request ID. Decorative imagery is optional; operational clarity is required.

## Component selection

- Use a **button** for one immediate action.
- Use a **select** for a bounded set of related choices.
- Use a **modal** when the user must provide structured text.
- Use an **ephemeral response** for administrator controls, permission errors, and setup secrets.
- Use a **public response** only when the result is intentionally member-visible.
- Ask for confirmation before destructive, irreversible, or broad-impact actions.

## Included flows

### `/panel`

1. Re-check `Manage Guild` on invocation.
2. Return an ephemeral control-panel embed.
3. Offer module selection for welcome, tickets, safety, and insights.
4. Offer quick status and ticket buttons with stable custom IDs.
5. Record a bounded interaction event when Supabase is configured.

### `/ticket`

1. Open a modal with subject and details.
2. Validate Discord's configured maximum lengths.
3. Record `ticket_submitted` without copying the raw details into analytics properties.
4. Return a success embed and a clear delivery expectation.

### Permission failure

1. Do not reveal hidden controls or partial configuration.
2. State which permission is required.
3. Explain who can complete the action.
4. Include a request ID for support and audit correlation.

## Persistent component rules

Persistent controls use `timeout=None` and versioned stable custom IDs. Changes that break callback meaning require a new custom-ID version; old versions remain routable until deployed messages are retired.

