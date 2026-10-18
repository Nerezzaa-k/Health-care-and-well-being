const { chromium } = require('playwright');
const axeCore = require('axe-core');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:8000', { waitUntil: 'networkidle' });

  // Log in as worker
  await page.click("button:has-text('Enter as Field Worker')");
  await page.waitForSelector('#workerAppView', { state: 'visible' });
  await page.waitForTimeout(500);

  // Check worker contrast
  await page.addScriptTag({ content: axeCore.source });
  const workerAxe = await page.evaluate(async () => {
    return (await axe.run(document, { runOnly: ['color-contrast'] })).violations;
  });
  console.log('Worker contrast violations:', JSON.stringify(workerAxe.map(v => v.nodes.map(n => ({ html: n.html, failureSummary: n.failureSummary }))), null, 2));

  // Check statOpenEscalated
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => {
    document.getElementById('managerDashboardView').style.display = 'block';
    document.getElementById('workerAppView').style.display = 'none';
  });
  await page.waitForTimeout(1000);
  const elText = await page.locator('#statOpenEscalated').innerText();
  console.log('statOpenEscalated innerText:', elText);

  await browser.close();
})();
