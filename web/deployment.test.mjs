import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

test("a raw frontend checkout cannot replace the serving deployment", async () => {
  const config = JSON.parse(await readFile(new URL("./vercel.json", import.meta.url), "utf8"));
  assert.equal(config.buildCommand, "node scripts/require-serving-export.mjs");
  const result = spawnSync(process.execPath, [
    fileURLToPath(new URL("./scripts/require-serving-export.mjs", import.meta.url)),
  ], { encoding: "utf8", cwd: new URL(".", import.meta.url) });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Refusing a static-only deployment/);
  assert.match(result.stderr, /arxiv_search\.serving\.export/);
});

test("missing live API routes are reported as unavailable, never as coming soon", async t => {
  const saved = { location: globalThis.location, fetch: globalThis.fetch };
  t.after(() => Object.assign(globalThis, saved));
  globalThis.location = { hostname: "arxiv.agarwal-labs.com", search: "" };
  globalThis.fetch = async () => ({
    ok: false, status: 404, json: async () => { throw new SyntaxError("Not JSON"); },
  });
  const { getMeta, search, isMock } = await import("./api.js?deployment-test");
  for (const request of [() => getMeta(), () => search("retrieval")]) {
    await assert.rejects(request, error => {
      assert.equal(error.code, "not_deployed");
      assert.match(error.message, /unavailable in this deployment/);
      return true;
    });
  }
  assert.equal(isMock(), false);
  const app = await readFile(new URL("./app.js", import.meta.url), "utf8");
  assert.ok(!app.includes("Search is coming soon"));
  assert.ok(app.includes('title: "Search temporarily unavailable"'));
});
