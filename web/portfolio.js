const PORTFOLIO_ORIGINS = [
  "https://agarwal-labs.com",
  "https://www.agarwal-labs.com",
];

export function notifyPortfolioReady(browserWindow = window, referrer = document.referrer) {
  if (browserWindow.parent === browserWindow || !URL.canParse(referrer)) return;
  const origin = new URL(referrer).origin;
  if (PORTFOLIO_ORIGINS.includes(origin)) {
    browserWindow.parent.postMessage({ type: "arxiv-search:ready" }, origin);
  }
}
