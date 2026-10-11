const { chromium } = require("playwright");
const path = require("path");
const { pathToFileURL } = require("url");

const ROOT = path.resolve(__dirname, "..");
const URL = pathToFileURL(path.join(ROOT, "index.html")).href;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });

  // hero + overview
  await page.evaluate(() => document.documentElement.dataset.theme = "light");
  await page.locator(".hero").screenshot({ path: path.join(ROOT, "_data", "sec-hero.png") });
  await page.locator("#mapsec").scrollIntoViewIfNeeded();
  await page.waitForTimeout(1200);
  await page.locator("#mapsec").screenshot({ path: path.join(ROOT, "_data", "sec-map.png") });
  await page.locator("#cost").screenshot({ path: path.join(ROOT, "_data", "sec-cost.png") });
  await page.locator("#spots").screenshot({ path: path.join(ROOT, "_data", "sec-spots.png") });
  await page.locator("#alerts").screenshot({ path: path.join(ROOT, "_data", "sec-alerts.png") });
  await page.locator("#sos").screenshot({ path: path.join(ROOT, "_data", "sec-sos.png") });

  // dark day card (verify heading contrast fix)
  await page.evaluate(() => { document.documentElement.dataset.theme = "dark"; localStorage.setItem("tohoku-theme", "dark"); });
  await page.locator("#day-3").scrollIntoViewIfNeeded();
  await page.locator("#day-3").screenshot({ path: path.join(ROOT, "_data", "sec-day-dark.png") });

  await browser.close();
  console.log("section screenshots saved");
})();
