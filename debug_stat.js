const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:8000', { waitUntil: 'networkidle' });
  await page.click("button:has-text('Enter as Manager')");
  await page.waitForSelector('#managerDashboardView', { state: 'visible' });
  await page.waitForTimeout(1000);
  const text = await page.evaluate(() => {
    return {
      activePatients: document.getElementById('statActivePatients').textContent,
      openEscalated: document.getElementById('statOpenEscalated').textContent,
      scorecardHtml: document.getElementById('tileEscalated').innerHTML
    };
  });
  console.log('Result:', text);
  await browser.close();
})();
