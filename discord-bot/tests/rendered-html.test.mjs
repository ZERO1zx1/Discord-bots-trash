import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html", host: "localhost" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the GuildPilot control plane", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>GuildPilot — Discord Community Operations<\/title>/i);
  assert.match(html, /Run your Discord community with confidence/i);
  assert.match(html, /Embed studio/i);
  assert.match(html, /No production events yet/i);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("includes accessible navigation and honest data states", async () => {
  const html = await (await render()).text();
  assert.match(html, /Skip to dashboard/i);
  assert.match(html, /Primary navigation/i);
  assert.match(html, /Live data · not connected/i);
  assert.match(html, /Northstar Community — preview only/i);
});
