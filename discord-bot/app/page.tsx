"use client";

import { useMemo, useState } from "react";

type WorkspaceView = "overview" | "embed" | "analytics" | "settings";
type EmbedTone = "success" | "info" | "warning" | "danger";

const toneConfig: Record<
  EmbedTone,
  { label: string; color: string; eyebrow: string; defaultTitle: string }
> = {
  success: {
    label: "Success",
    color: "#57f287",
    eyebrow: "SETUP COMPLETE",
    defaultTitle: "Your community is ready",
  },
  info: {
    label: "Information",
    color: "#5865f2",
    eyebrow: "GUILDPILOT UPDATE",
    defaultTitle: "A new workflow is available",
  },
  warning: {
    label: "Warning",
    color: "#fee75c",
    eyebrow: "ACTION RECOMMENDED",
    defaultTitle: "Review missing permissions",
  },
  danger: {
    label: "Critical",
    color: "#ed4245",
    eyebrow: "ATTENTION REQUIRED",
    defaultTitle: "A safety rule needs attention",
  },
};

const navigation: Array<{
  id: WorkspaceView;
  label: string;
  glyph: string;
}> = [
  { id: "overview", label: "Overview", glyph: "01" },
  { id: "embed", label: "Embed studio", glyph: "02" },
  { id: "analytics", label: "Analytics", glyph: "03" },
  { id: "settings", label: "Settings", glyph: "04" },
];

const metrics = [
  {
    label: "Value-active guilds",
    value: "—",
    note: "No production events yet",
    accent: "violet",
  },
  {
    label: "14-day activation",
    value: "—",
    note: "Baseline starts after launch",
    accent: "cyan",
  },
  {
    label: "4-week retention",
    value: "—",
    note: "Needs four complete weeks",
    accent: "mint",
  },
];

function GuildPilotMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      GP
    </span>
  );
}

export default function Home() {
  const [view, setView] = useState<WorkspaceView>("overview");
  const [tone, setTone] = useState<EmbedTone>("success");
  const [title, setTitle] = useState(toneConfig.success.defaultTitle);
  const [description, setDescription] = useState(
    "Welcome is enabled, ticket routing is configured, and every high-risk action will be recorded in the audit log.",
  );
  const [module, setModule] = useState("Welcome & onboarding");
  const [toast, setToast] = useState<string | null>(null);

  const embed = useMemo(() => toneConfig[tone], [tone]);

  function chooseTone(nextTone: EmbedTone) {
    setTone(nextTone);
    setTitle(toneConfig[nextTone].defaultTitle);
  }

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2800);
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to dashboard
      </a>

      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-lockup">
          <GuildPilotMark />
          <div>
            <strong>GuildPilot</strong>
            <span>Community operations</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navigation.map((item) => (
            <button
              className={view === item.id ? "nav-item is-active" : "nav-item"}
              key={item.id}
              onClick={() => setView(item.id)}
              type="button"
            >
              <span className="nav-glyph" aria-hidden="true">
                {item.glyph}
              </span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-card">
          <span className="eyebrow">BOT CONNECTION</span>
          <div className="status-row">
            <span className="status-dot is-muted" aria-hidden="true" />
            Awaiting credentials
          </div>
          <p>Add the Discord token to run the bot process.</p>
          <button type="button" onClick={() => setView("settings")}>
            Open setup
          </button>
        </div>

        <div className="profile-mini">
          <span className="profile-avatar" aria-hidden="true">
            GP
          </span>
          <div>
            <strong>Preview workspace</strong>
            <span>Local environment</span>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="mobile-brand">
            <GuildPilotMark />
            <strong>GuildPilot</strong>
          </div>
          <label className="guild-picker">
            <span>Guild</span>
            <select defaultValue="none" aria-label="Choose a Discord guild">
              <option value="none">No guild connected</option>
              <option value="demo">Northstar Community — preview only</option>
            </select>
          </label>
          <div className="topbar-actions">
            <span className="environment-pill">Development</span>
            <button
              className="quiet-button"
              type="button"
              onClick={() => notify("Notifications will appear here after setup.")}
            >
              Updates
            </button>
          </div>
        </header>

        <main id="main-content" className="main-content">
          {view === "overview" && (
            <>
              <section className="hero-panel">
                <div className="hero-copy">
                  <span className="eyebrow">COMMUNITY CONTROL PLANE</span>
                  <h1>Run your Discord community with confidence.</h1>
                  <p>
                    Configure safer workflows, ship polished bot interactions,
                    and understand whether members are receiving real value.
                  </p>
                  <div className="hero-actions">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => notify("Discord OAuth opens when the Flask API is configured.")}
                    >
                      Connect Discord
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => setView("embed")}
                    >
                      Open embed studio
                    </button>
                  </div>
                </div>

                <div className="readiness-card" aria-label="Launch readiness">
                  <div className="readiness-score">
                    <span>1 / 4</span>
                    <small>launch steps</small>
                  </div>
                  <div>
                    <span className="eyebrow">LAUNCH READINESS</span>
                    <h2>Foundation ready</h2>
                    <p>Connect credentials, invite the bot, and complete one module.</p>
                  </div>
                  <ol>
                    <li className="is-done">Project structure</li>
                    <li>Supabase connection</li>
                    <li>Discord authorization</li>
                    <li>First value workflow</li>
                  </ol>
                </div>
              </section>

              <section className="section-block" aria-labelledby="health-title">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">PRODUCT HEALTH</span>
                    <h2 id="health-title">The metrics that guide decisions</h2>
                  </div>
                  <span className="data-state">Live data · not connected</span>
                </div>
                <div className="metric-grid">
                  {metrics.map((metric) => (
                    <article className={`metric-card accent-${metric.accent}`} key={metric.label}>
                      <span>{metric.label}</span>
                      <strong>{metric.value}</strong>
                      <small>{metric.note}</small>
                    </article>
                  ))}
                </div>
              </section>

              <section className="two-column-grid">
                <article className="panel activity-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">ACTIVITY</span>
                      <h2>Value events</h2>
                    </div>
                    <select aria-label="Activity date range" defaultValue="28d">
                      <option value="28d">Last 28 days</option>
                      <option value="7d">Last 7 days</option>
                    </select>
                  </div>
                  <div className="empty-chart" role="img" aria-label="No value event data yet">
                    <div className="chart-grid" aria-hidden="true" />
                    <span className="empty-icon" aria-hidden="true">
                      ↗
                    </span>
                    <h3>No production events yet</h3>
                    <p>
                      The chart begins after a configured guild completes a
                      welcome, ticket, or moderation value event.
                    </p>
                  </div>
                </article>

                <article className="panel next-action-panel">
                  <span className="eyebrow">NEXT BEST ACTION</span>
                  <h2>Connect the foundation</h2>
                  <p>
                    Three environment groups unlock the complete local flow.
                    Secrets stay in server processes and never reach the browser.
                  </p>
                  <ul className="check-list">
                    <li>
                      <span>1</span>
                      Supabase URL and server secret
                    </li>
                    <li>
                      <span>2</span>
                      Discord application credentials
                    </li>
                    <li>
                      <span>3</span>
                      Flask session secret and public URL
                    </li>
                  </ul>
                  <button
                    className="primary-button full-width"
                    type="button"
                    onClick={() => setView("settings")}
                  >
                    Review configuration
                  </button>
                </article>
              </section>
            </>
          )}

          {view === "embed" && (
            <section className="studio-page">
              <div className="page-title">
                <span className="eyebrow">DISCORD EXPERIENCE</span>
                <h1>Embed studio</h1>
                <p>
                  Compose a consistent interaction, then use the same design
                  contract from slash commands, buttons, selects, and modals.
                </p>
              </div>

              <div className="studio-grid">
                <form className="panel editor-panel" onSubmit={(event) => event.preventDefault()}>
                  <div className="field-group">
                    <label htmlFor="embed-tone">Message purpose</label>
                    <select
                      id="embed-tone"
                      value={tone}
                      onChange={(event) => chooseTone(event.target.value as EmbedTone)}
                    >
                      {Object.entries(toneConfig).map(([value, config]) => (
                        <option value={value} key={value}>
                          {config.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="embed-module">Module</label>
                    <select
                      id="embed-module"
                      value={module}
                      onChange={(event) => setModule(event.target.value)}
                    >
                      <option>Welcome & onboarding</option>
                      <option>Tickets & support</option>
                      <option>Moderation & safety</option>
                      <option>Community insights</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="embed-title">Embed title</label>
                    <input
                      id="embed-title"
                      value={title}
                      maxLength={80}
                      onChange={(event) => setTitle(event.target.value)}
                    />
                    <small>{title.length} / 80</small>
                  </div>

                  <div className="field-group">
                    <label htmlFor="embed-description">Description</label>
                    <textarea
                      id="embed-description"
                      value={description}
                      maxLength={320}
                      rows={6}
                      onChange={(event) => setDescription(event.target.value)}
                    />
                    <small>{description.length} / 320</small>
                  </div>

                  <div className="editor-note">
                    <strong>Interaction contract</strong>
                    <p>
                      Destructive actions require confirmation. Long choices use
                      selects; structured input uses a modal; every response has
                      an explicit recovery path.
                    </p>
                  </div>

                  <button
                    className="primary-button full-width"
                    type="button"
                    onClick={() => notify("Preview saved locally. Supabase sync starts after connection.")}
                  >
                    Save interaction preset
                  </button>
                </form>

                <div className="preview-column">
                  <div className="preview-toolbar">
                    <span>Discord preview</span>
                    <span className="preview-label">PREVIEW · NOT SENT</span>
                  </div>
                  <div className="discord-canvas">
                    <div className="discord-message">
                      <div className="bot-avatar" aria-hidden="true">
                        GP
                      </div>
                      <div className="message-body">
                        <div className="message-author">
                          <strong>GuildPilot</strong>
                          <span className="bot-tag">APP</span>
                          <time>Today at 12:40</time>
                        </div>
                        <div className="discord-embed" style={{ borderColor: embed.color }}>
                          <span className="embed-eyebrow" style={{ color: embed.color }}>
                            {embed.eyebrow}
                          </span>
                          <h2>{title || "Untitled interaction"}</h2>
                          <p>{description || "Add a clear description for the member."}</p>
                          <div className="embed-field-grid">
                            <div>
                              <span>Module</span>
                              <strong>{module}</strong>
                            </div>
                            <div>
                              <span>Audit state</span>
                              <strong>Recorded</strong>
                            </div>
                          </div>
                          <div className="embed-footer">
                            <span className="mini-mark">GP</span>
                            GuildPilot · Request ID GP-PREVIEW
                          </div>
                        </div>
                        <div className="discord-components" aria-label="Interactive component preview">
                          <button type="button" onClick={() => notify("Primary action selected.")}>Continue setup</button>
                          <button type="button" className="discord-secondary" onClick={() => notify("Details opened.")}>View details</button>
                          <select aria-label="Choose a workflow" defaultValue="choose">
                            <option value="choose" disabled>Choose a workflow…</option>
                            <option>Configure welcome</option>
                            <option>Create a support ticket</option>
                            <option>Review safety settings</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {view === "analytics" && (
            <section className="simple-page">
              <div className="page-title">
                <span className="eyebrow">DECISION METRICS</span>
                <h1>Analytics foundation</h1>
                <p>
                  Reach, value, retention, and reliability stay separate so
                  command volume cannot masquerade as product success.
                </p>
              </div>
              <div className="metric-definition-grid">
                <article className="panel">
                  <span className="metric-number">01</span>
                  <h2>Weekly Value-Active Guilds</h2>
                  <p>Distinct eligible guilds with at least one successful production value event in seven days.</p>
                  <span className="definition-chip">Primary outcome</span>
                </article>
                <article className="panel">
                  <span className="metric-number">02</span>
                  <h2>14-Day Guild Activation</h2>
                  <p>Eligible installs reaching valid configuration and a first successful value event within fourteen days.</p>
                  <span className="definition-chip">Activation driver</span>
                </article>
                <article className="panel">
                  <span className="metric-number">03</span>
                  <h2>Four-Week Retention</h2>
                  <p>Activated guilds that record value again during the fourth complete week after activation.</p>
                  <span className="definition-chip">Retention outcome</span>
                </article>
              </div>
              <article className="panel guardrail-panel">
                <div>
                  <span className="eyebrow">GUARDRAILS</span>
                  <h2>Success cannot hide harm</h2>
                </div>
                <ul>
                  <li>Interaction success and error rates</li>
                  <li>P95 command response latency</li>
                  <li>Permission-denied and recovery completion</li>
                  <li>Audit-log coverage for high-risk actions</li>
                </ul>
              </article>
            </section>
          )}

          {view === "settings" && (
            <section className="simple-page">
              <div className="page-title">
                <span className="eyebrow">ENVIRONMENT</span>
                <h1>Connection checklist</h1>
                <p>
                  Values are read only by the Flask and bot processes. Nothing
                  sensitive is bundled into this browser application.
                </p>
              </div>
              <div className="settings-list">
                {[
                  ["Supabase", "SUPABASE_URL · SUPABASE_SECRET_KEY", "Required for guild state and events"],
                  ["Discord bot", "DISCORD_TOKEN · DISCORD_APPLICATION_ID", "Required for slash commands and components"],
                  ["Discord OAuth", "DISCORD_CLIENT_ID · DISCORD_CLIENT_SECRET", "Required for dashboard sign-in"],
                  ["Flask", "FLASK_SECRET_KEY · PUBLIC_BASE_URL", "Required for protected sessions and redirects"],
                ].map(([name, keys, description]) => (
                  <article className="setting-row" key={name}>
                    <span className="status-dot is-muted" aria-hidden="true" />
                    <div>
                      <h2>{name}</h2>
                      <code>{keys}</code>
                      <p>{description}</p>
                    </div>
                    <span className="not-configured">Not configured</span>
                  </article>
                ))}
              </div>
            </section>
          )}
        </main>
      </div>

      {toast && (
        <div className="toast" role="status" aria-live="polite">
          <span aria-hidden="true">✓</span>
          {toast}
        </div>
      )}
    </div>
  );
}
