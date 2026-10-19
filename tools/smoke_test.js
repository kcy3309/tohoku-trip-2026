const { chromium } = require("playwright");
const path = require("path");
const { pathToFileURL } = require("url");

const ROOT = path.resolve(__dirname, "..");
const URL = pathToFileURL(path.join(ROOT, "index.html")).href;
const errors = [];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push("console.error: " + m.text()); });
  await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });

  const checks = {
    "overview rows": "#ovTable tbody tr",
    "decision items": "#decisionList li",
    "day cards": "details.day",
    "timeline items": ".it",
    "cost cards": ".cost-card",
    "hotel cost rows": "#hotelCostTable tbody tr",
    "toll rows": "#tollTable tbody tr",
    "spot rows": "#spotTable tbody tr",
    "alert cards": ".alert",
    "snow rows": "#snowTable tbody tr",
    "hotlines": ".hotline",
    "sos steps": "#sosSteps li",
    "phrases": ".phrase",
    "charging tables": "#charging table",
    "map markers": ".leaf-marker",
    "route polyline": ".leaflet-overlay-pane path",
    "weather cards": ".wx",
    "weather day badges": ".day-meta .tag.p-high, .day-meta .tag.p-mid, .day-meta .tag.p-low",
    "meal budget rows": "#mealTable tbody tr",
    "build stamp": ".build-info b",
  };
  for (const [name, sel] of Object.entries(checks)) {
    const n = await page.locator(sel).count();
    console.log((n ? "OK  " : "FAIL") + ` ${name}: ${n}`);
    if (!n) errors.push(name + " is 0");
  }

  const cards = await page.locator(".cost-card").count();
  console.log((cards === 4 ? "OK  " : "FAIL") + ` cost cards exact: ${cards}`);
  if (cards !== 4) errors.push("cost cards != 4");
  const inc = await page.locator("#mealTable .pill.paid").count();
  console.log((inc === 10 ? "OK  " : "FAIL") + ` meal included pills: ${inc}`);
  if (inc !== 10) errors.push("meal included pills != 10");

  await page.click("#themeBtn");
  let theme = await page.evaluate(() => document.documentElement.dataset.theme);
  console.log((theme === "dark" ? "OK  " : "FAIL") + ` theme toggle -> ${theme}`);
  if (theme !== "dark") errors.push("theme toggle failed");
  await page.click("#themeBtn");

  await page.selectOption("#fCounty", "青森縣");
  const shown = await page.locator("#spotTable tbody tr").count();
  const expected = await page.evaluate(() => DATA.spots.filter((s) => s.county === "青森縣").length);
  console.log((shown === expected && shown > 0 ? "OK  " : "FAIL") + ` filter 青森縣: shown=${shown} expected=${expected}`);
  if (shown !== expected) errors.push("county filter mismatch");

  await page.click("#day-5 summary");
  const opened = await page.evaluate(() => document.getElementById("day-5").open);
  console.log((opened ? "OK  " : "FAIL") + " day-5 expand");
  if (!opened) errors.push("day expand failed");

  await page.selectOption("#fCounty", "");
  await page.evaluate(() => { document.documentElement.dataset.theme = "light"; });
  await page.screenshot({ path: path.join(ROOT, "_data", "shot-light.png") });
  await page.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
  await page.screenshot({ path: path.join(ROOT, "_data", "shot-dark.png") });
  console.log("screenshots saved");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => { document.documentElement.dataset.theme = "light"; });
  await page.screenshot({ path: path.join(ROOT, "_data", "shot-mobile.png") });
  console.log("mobile screenshot saved");

  await browser.close();
  if (errors.length) {
    console.log("\nERRORS:");
    errors.forEach((e) => console.log(" -", e));
    process.exit(1);
  }
  console.log("\nALL CHECKS PASSED");
})();
