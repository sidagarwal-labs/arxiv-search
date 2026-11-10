import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("viewer CSP allows arXiv frames and only portfolio frame ancestors", async () => {
  const config = JSON.parse(await readFile(new URL("./vercel.json", import.meta.url), "utf8"));
  const policy = config.headers[0].headers.find(header => header.key === "Content-Security-Policy").value;
  for (const directive of ["frame-src https://arxiv.org", "script-src 'self'", "connect-src 'self'",
    "object-src 'none'", "frame-ancestors 'self' https://agarwal-labs.com https://www.agarwal-labs.com"]) {
    assert.ok(policy.split(";").map(value => value.trim()).includes(directive), directive);
  }
  assert.ok(!config.headers.flatMap(rule => rule.headers)
    .some(header => header.key.toLowerCase() === "x-frame-options"));
});

test("public showcase ignores API overrides and only fetches static sample data", async t => {
  const saved = { location: globalThis.location, fetch: globalThis.fetch };
  t.after(() => Object.assign(globalThis, saved));
  globalThis.location = {hostname:"arxiv.agarwal-labs.com",search:"?api=https://never.invalid&mock=1"};
  const { CONFIG } = await import("./config.js");
  CONFIG.SHOWCASE_ONLY = true;
  CONFIG.MODE = "live";
  t.after(() => { CONFIG.SHOWCASE_ONLY = false; });
  const calls = [];
  globalThis.fetch = async url => {
    calls.push(url);
    assert.equal(url, "./mock/papers.json");
    return {ok:true,json:async()=>({meta:{papers:1},papers:[{
      arxiv_id:"2510.12345",title:"Retrieval methods",abstract:"Retrieval evidence",authors:[],
    }]})};
  };
  const {getMeta,search,summarize,isMock} = await import("./api.js?showcase-test");
  await getMeta();
  const result = await search("retrieval");
  await summarize("retrieval",result.results.map(p=>p.arxiv_id));
  assert.equal(isMock(),true);
  assert.deepEqual(calls,["./mock/papers.json"]);
});
