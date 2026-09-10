const healthCard = document.querySelector("[data-health-endpoint]");

async function refreshHealth() {
  if (!healthCard) return;
  try {
    const response = await fetch(healthCard.dataset.healthEndpoint, {
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    for (const [name, ready] of Object.entries(payload.checks ?? {})) {
      healthCard.querySelector(`[data-check="${name}"]`)?.classList.toggle("ready", Boolean(ready));
    }
  } catch {
    healthCard.setAttribute("data-health-state", "unavailable");
  }
}

refreshHealth();

