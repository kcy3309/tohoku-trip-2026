const { chromium } = require("playwright");
const path = require("path");
const { pathToFileURL } = require("url");
const ROOT = path.resolve(__dirname, "..");

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await p.goto(pathToFileURL(path.join(ROOT, "index.html")).href, { waitUntil: "networkidle" });
  await p.evaluate(() => { document.documentElement.dataset.theme = "light"; });

  const mapLinks = await p.locator('a[href*="goo.gl"]').count();
  const paid = await p.locator(".pill.paid").count();
  const rentalTotal = await p.locator("#cost .cost-card:nth-child(3) .big").innerText();
  const note = await p.locator("#costNote").innerText();
  console.log("goo.gl links:", mapLinks, "| paid pills:", paid, "| rental total:", rentalTotal);
  console.log("cost note:", note.replace(/\n/g, " / "));

  await p.locator("#day-4").scrollIntoViewIfNeeded();
  const isOpen = await p.evaluate(() => document.getElementById("day-4").open);
  if (!isOpen) await p.click("#day-4 summary");
  await p.waitForTimeout(300);
  await p.locator("#day-4").screenshot({ path: path.join(ROOT, "_data", "sec-day4-paid.png") });
  await p.locator("#cost").screenshot({ path: path.join(ROOT, "_data", "sec-cost.png") });
  await b.close();
  console.log("screenshots saved");
})();
