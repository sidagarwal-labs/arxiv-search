import test from "node:test";
import assert from "node:assert/strict";
import { notifyPortfolioReady } from "./portfolio.js";

for (const origin of ["https://agarwal-labs.com", "https://www.agarwal-labs.com"]) {
  test(`ready signal targets only the embedding portfolio: ${origin}`, () => {
    const calls = [];
    notifyPortfolioReady({ parent: { postMessage: (...args) => calls.push(args) } }, `${origin}/lab`);
    assert.deepEqual(calls, [[{ type: "arxiv-search:ready" }, origin]]);
  });
}

test("standalone pages do not message themselves", () => {
  const browser = { postMessage: () => assert.fail("Unexpected message") };
  browser.parent = browser;
  notifyPortfolioReady(browser, "https://agarwal-labs.com/");
});

for (const referrer of ["", "invalid", "https://example.com/", "http://agarwal-labs.com/",
  "https://agarwal-labs.com.evil.example/", "https://agarwal-labs.com:444/"]) {
  test(`no ready signal to an unapproved or unknown parent: ${referrer}`, () => {
    notifyPortfolioReady({ parent: { postMessage: () => assert.fail("Unexpected message") } }, referrer);
  });
}
