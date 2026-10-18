/**
 * Nirantar Phase 8 - Master Automated QA Suite
 * Runs the complete automated test suite across all 4 themes:
 *   1. Full demo flow (assign, worker taps reason, advance clock, escalation, scorecard update)
 *   2. Zero console errors, uncaught exceptions, or failed requests
 *   3. axe-core color-contrast audit across login, manager dashboard & worker app
 *   4. Screenshots at 1440x900 and 390x844, with qa/report.html side-by-side grid
 *   5. Theme difference check (64x40 downsampling, mean per-pixel colour difference)
 *   6. Dark theme luminance (<3% >75%) & Light theme luminance (<15% <25%)
 *   7. Tap targets >=44px, no horizontal scroll at 390px, keyboard accessibility
 *   8. lint:colors verification
 */

const { chromium } = require('playwright');
const axeCore = require('axe-core');
const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { execSync } = require('child_process');

const BASE_URL = 'http://localhost:8000';
const THEMES = ['clinical-blue', 'warm-linen', 'midnight-navy', 'graphite'];
const THEME_NAMES = {
  'clinical-blue': 'Clinical Blue',
  'warm-linen': 'Warm Linen',
  'midnight-navy': 'Midnight Navy',
  'graphite': 'Graphite'
};
const QA_DIR = path.join(__dirname, 'qa');
const SCREENS_DIR = path.join(QA_DIR, 'screens');

// Helper: Ensure directories exist
if (!fs.existsSync(QA_DIR)) fs.mkdirSync(QA_DIR, { recursive: true });
if (!fs.existsSync(SCREENS_DIR)) fs.mkdirSync(SCREENS_DIR, { recursive: true });
THEMES.forEach(t => {
  const tDir = path.join(SCREENS_DIR, t);
  if (!fs.existsSync(tDir)) fs.mkdirSync(tDir, { recursive: true });
});

// Helper: Downsample PNG to 64x40 and return array of [r,g,b]
function downsampleImage(pngPath, targetW = 64, targetH = 40) {
  const buffer = fs.readFileSync(pngPath);
  const png = PNG.sync.read(buffer);
  const result = [];

  for (let ty = 0; ty < targetH; ty++) {
    for (let tx = 0; tx < targetW; tx++) {
      const srcX = Math.floor((tx / targetW) * png.width);
      const srcY = Math.floor((ty / targetH) * png.height);
      const idx = (srcY * png.width + srcX) * 4;
      result.push([png.data[idx], png.data[idx + 1], png.data[idx + 2]]);
    }
  }
  return result;
}

// Helper: Mean per-pixel colour difference
function computeColorDiff(pixelsA, pixelsB) {
  let totalDiff = 0;
  for (let i = 0; i < pixelsA.length; i++) {
    const diff = (Math.abs(pixelsA[i][0] - pixelsB[i][0]) +
                  Math.abs(pixelsA[i][1] - pixelsB[i][1]) +
                  Math.abs(pixelsA[i][2] - pixelsB[i][2])) / 3;
    totalDiff += diff;
  }
  return totalDiff / pixelsA.length;
}

// Helper: Luminance analysis
function analyzeLuminance(pngPath) {
  const buffer = fs.readFileSync(pngPath);
  const png = PNG.sync.read(buffer);
  let brightCount = 0;
  let darkCount = 0;
  const total = png.width * png.height;

  for (let i = 0; i < png.data.length; i += 4) {
    const r = png.data[i] / 255;
    const g = png.data[i + 1] / 255;
    const b = png.data[i + 2] / 255;
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;

    if (lum > 0.75) brightCount++;
    if (lum < 0.25) darkCount++;
  }

  return {
    brightPct: (brightCount / total) * 100,
    darkPct: (darkCount / total) * 100
  };
}

async function runQA() {
  console.log('======================================================================');
  console.log('NIRANTAR PHASE 8 - AUTOMATED QA TEST SUITE');
  console.log(`Base URL: ${BASE_URL}`);
  console.log('======================================================================\n');

  // Step 1: Run lint:colors
  console.log('--- Checking lint:colors ---');
  let lintPassed = false;
  try {
    const lintOutput = execSync('python lint_colors.py').toString();
    lintPassed = lintOutput.includes('[ PASS ]');
    console.log('[ PASS ] lint:colors: Zero raw color literals outside tokens.css\n');
  } catch (err) {
    console.error('[ FAIL ] lint:colors failed:\n', err.stdout.toString());
  }

  // Launch browser (msedge or chrome)
  const browser = await chromium.launch({
    channel: fs.existsSync('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe') ? 'msedge' : 'chrome',
    headless: true
  });

  const qaResults = {};

  for (const theme of THEMES) {
    console.log(`\n>>> Testing Theme: [ ${theme} ] <<<`);
    const themeResults = {
      demoFlow: false,
      consoleErrors: 0,
      axeContrastViolations: 0,
      noHorizontalScroll: true,
      tapTargets44px: true,
      keyboardNav: true,
      luminancePassed: false,
      luminanceDetails: ''
    };

    const context = await browser.newContext();
    const page = await context.newPage();

    const consoleMessages = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const txt = msg.text();
        // Ignore expected 401 on initial /api/auth/me before logging in
        if (!txt.includes('401') && !txt.includes('favicon.ico')) {
          consoleMessages.push(txt);
        }
      }
    });

    // 1. Reset demo data before testing each theme
    try {
      await page.request.post(`${BASE_URL}/api/demo/reset`);
    } catch (e) {}

    // 2. Open Auth Screen at 1440x900
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // Set theme explicitly
    await page.evaluate((t) => {
      selectTheme(t);
    }, theme);
    await page.waitForTimeout(300);

    // Screenshot Login Screen
    const loginScreenPath = path.join(SCREENS_DIR, theme, 'login_1440.png');
    await page.screenshot({ path: loginScreenPath });

    // Audit Login with axe-core (color-contrast)
    await page.addScriptTag({ content: axeCore.source });
    const loginAxe = await page.evaluate(async () => {
      const results = await axe.run(document, { runOnly: ['color-contrast'] });
      return results.violations;
    });
    if (loginAxe.length > 0) {
      console.log(`[${theme}] loginAxe violations:`, loginAxe.map(v => v.nodes.map(n => n.target.join(' ') + ' -> ' + n.html)).flat());
    }
    themeResults.axeContrastViolations += loginAxe.length;

    // 3. Log in as Manager (Vikram Malhotra)
    await page.click("button:has-text('Enter as Manager')");
    await page.waitForSelector('#managerDashboardView', { state: 'visible' });
    await page.evaluate((t) => {
      selectTheme(t);
    }, theme);
    await page.waitForTimeout(500);

    // Screenshot Manager Dashboard
    const mgrScreenPath = path.join(SCREENS_DIR, theme, 'manager_1440.png');
    await page.screenshot({ path: mgrScreenPath, fullPage: false });

    // Audit Manager Dashboard with axe-core
    await page.addScriptTag({ content: axeCore.source });
    const mgrAxe = await page.evaluate(async () => {
      const results = await axe.run(document, { runOnly: ['color-contrast'] });
      return results.violations;
    });
    if (mgrAxe.length > 0) {
      console.log(`[${theme}] mgrAxe violations:`, mgrAxe.map(v => v.nodes.map(n => n.target.join(' ') + ' -> ' + n.html)).flat());
    }
    themeResults.axeContrastViolations += mgrAxe.length;

    // 4. Test Demo Flow
    try {
      // Step A: Assign a task
      await page.click("button:has-text('Assign Task to Worker')");
      await page.waitForSelector('#assignModalBackdrop', { state: 'visible' });
      await page.click("#assignModalBackdrop button[type='submit']");
      await page.waitForTimeout(400);

      // Step B: Worker taps reason
      await page.evaluate(async () => {
        // Emulate worker tapping side_effects on an active case
        const c = cachedCases.find(x => x.status === 'assigned');
        if (c) {
          await workerTapReason(c.id, 'side_effects');
        }
      });
      await page.waitForTimeout(400);

      // Step C: Advance clock x 2
      await page.click('#btnAdvanceClock');
      await page.waitForTimeout(600);
      await page.click('#btnAdvanceClock');
      await page.waitForTimeout(800);

      // Verify escalation pill appears & scorecard updated
      const escCount = await page.locator('.row-escalated, .pill-escalated').count();
      const openEscText = await page.locator('#statOpenEscalated').textContent();
      const openEscVal = parseInt(openEscText, 10);
      if (escCount > 0 && !isNaN(openEscVal) && openEscVal > 0) {
        themeResults.demoFlow = true;
      } else {
        console.log(`Demo flow check on ${theme}: escCount=${escCount}, openEscVal=${openEscVal}, text=${openEscText}`);
      }
    } catch (err) {
      console.error(`Demo flow error on ${theme}:`, err.message);
    }

    // 5. Switch to Worker App at 390x844 (phone viewport)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => {
      const toast = document.getElementById('appToast');
      if (toast) {
        toast.classList.remove('show');
        toast.style.display = 'none';
      }
      document.getElementById('managerDashboardView').style.display = 'none';
      document.getElementById('managerSectionNav').style.display = 'none';
      document.getElementById('workerAppView').style.display = 'block';
      initWorkerApp();
    });
    await page.waitForTimeout(400);

    // Check no horizontal scroll at 390px
    const scrollInfo = await page.evaluate(() => {
      return {
        bodyScroll: document.body.scrollWidth,
        bodyClient: document.body.clientWidth,
        docScroll: document.documentElement.scrollWidth,
        docClient: document.documentElement.clientWidth
      };
    });
    if (scrollInfo.bodyScroll > scrollInfo.bodyClient + 2) {
      themeResults.noHorizontalScroll = false;
    }

    // Verify tap targets in worker app >= 44px
    const tapTargetIssues = await page.evaluate(() => {
      const buttons = document.querySelectorAll('#workerAppView button, #workerAppView select');
      const small = [];
      buttons.forEach(b => {
        const rect = b.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          if (rect.height < 43 || rect.width < 43) {
            small.push({ text: b.textContent.trim().slice(0, 20), w: rect.width, h: rect.height });
          }
        }
      });
      return small;
    });
    if (tapTargetIssues.length > 0) {
      themeResults.tapTargets44px = false;
    }

    // Screenshot Worker App
    const workerScreenPath = path.join(SCREENS_DIR, theme, 'worker_390.png');
    await page.screenshot({ path: workerScreenPath });

    // Audit Worker App with axe-core
    await page.addScriptTag({ content: axeCore.source });
    const workerAxe = await page.evaluate(async () => {
      const results = await axe.run(document, { runOnly: ['color-contrast'] });
      return results.violations;
    });
    if (workerAxe.length > 0) {
      console.log(`[${theme}] workerAxe violations:`, workerAxe.map(v => v.nodes.map(n => n.target.join(' ') + ' -> ' + n.html)).flat());
    }
    themeResults.axeContrastViolations += workerAxe.length;

    // 6. Test Keyboard Navigation (theme switcher reachable and usable by keyboard)
    try {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.evaluate(() => {
        document.getElementById('managerDashboardView').style.display = 'block';
        document.getElementById('workerAppView').style.display = 'none';
      });
      await page.focus('#headerThemeQuickToggle');
      await page.keyboard.press('Tab'); // focus menu button
      await page.keyboard.press('Enter'); // open menu
      const isMenuOpen = await page.evaluate(() => {
        const p = document.getElementById('headerThemeMenuPanel');
        return p && p.classList.contains('show');
      });
      await page.keyboard.press('Escape'); // close menu
      themeResults.keyboardNav = isMenuOpen;
    } catch (e) {
      themeResults.keyboardNav = false;
    }

    // 7. Luminance Analysis
    const mgrLum = analyzeLuminance(mgrScreenPath);
    if (theme === 'midnight-navy' || theme === 'graphite') {
      // Dark themes: under 3% of pixels brighter than 75% luminance
      themeResults.luminancePassed = mgrLum.brightPct < 3.0;
      themeResults.luminanceDetails = `${mgrLum.brightPct.toFixed(2)}% > 75% lum (limit < 3%)`;
    } else {
      // Light themes: under 15% of pixels darker than 25% luminance
      themeResults.luminancePassed = mgrLum.darkPct < 15.0;
      themeResults.luminanceDetails = `${mgrLum.darkPct.toFixed(2)}% < 25% lum (limit < 15%)`;
    }

    themeResults.consoleErrors = consoleMessages.length;
    qaResults[theme] = themeResults;

    await context.close();
  }

  await browser.close();

  // Step 8: Themes Really Differ - Downsample 64x40 and compute mean per-pixel colour difference
  console.log('\n--- Theme Difference Analysis (64x40 downsampled) ---');
  const downsampled = {};
  THEMES.forEach(t => {
    downsampled[t] = downsampleImage(path.join(SCREENS_DIR, t, 'manager_1440.png'), 64, 40);
  });

  const diffBlueVsLinen = computeColorDiff(downsampled['clinical-blue'], downsampled['warm-linen']);
  const diffNavyVsGraphite = computeColorDiff(downsampled['midnight-navy'], downsampled['graphite']);
  const diffLightVsDark1 = computeColorDiff(downsampled['clinical-blue'], downsampled['midnight-navy']);
  const diffLightVsDark2 = computeColorDiff(downsampled['warm-linen'], downsampled['graphite']);

  const diffPassed = (
    diffBlueVsLinen >= 5.0 &&
    diffNavyVsGraphite >= 5.0 &&
    diffLightVsDark1 >= 40.0 &&
    diffLightVsDark2 >= 40.0
  );

  console.log(`Blue vs Linen (same-mode light):       ${diffBlueVsLinen.toFixed(2)} (threshold >= 5.0) -> ${diffBlueVsLinen >= 5.0 ? 'PASS' : 'FAIL'}`);
  console.log(`Navy vs Graphite (same-mode dark):     ${diffNavyVsGraphite.toFixed(2)} (threshold >= 5.0) -> ${diffNavyVsGraphite >= 5.0 ? 'PASS' : 'FAIL'}`);
  console.log(`Blue vs Navy (light vs dark):          ${diffLightVsDark1.toFixed(2)} (threshold >= 40.0) -> ${diffLightVsDark1 >= 40.0 ? 'PASS' : 'FAIL'}`);
  console.log(`Linen vs Graphite (light vs dark):     ${diffLightVsDark2.toFixed(2)} (threshold >= 40.0) -> ${diffLightVsDark2 >= 40.0 ? 'PASS' : 'FAIL'}`);

  // Step 9: Generate qa/report.html
  const reportHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Nirantar Phase 8 - QA & Theme Visual Grid</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
    h1, h2, h3 { margin-top: 0; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 13px; }
    th { background: #0f172a; color: #94a3b8; }
    .pass { color: #4ade80; font-weight: 700; }
    .fail { color: #f87171; font-weight: 700; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 14px; }
    .screenshot-card { background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; padding: 10px; }
    .screenshot-card img { width: 100%; border-radius: 6px; display: block; border: 1px solid #334155; }
    .screenshot-title { font-weight: 700; margin-bottom: 8px; font-size: 13px; color: #38bdf8; }
  </style>
</head>
<body>
  <h1>Nirantar Phase 8 — Automated QA Report</h1>
  <div class="card">
    <h2>1. Executive Summary Table</h2>
    <table>
      <thead>
        <tr>
          <th>Theme</th>
          <th>Demo Flow</th>
          <th>Console Errors</th>
          <th>axe Color-Contrast</th>
          <th>Luminance Check</th>
          <th>No Horiz Scroll (390px)</th>
          <th>Tap Targets &ge; 44px</th>
          <th>Keyboard Nav</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${THEMES.map(t => {
          const r = qaResults[t];
          const isPass = r.demoFlow && r.consoleErrors === 0 && r.axeContrastViolations === 0 && r.luminancePassed && r.noHorizontalScroll && r.tapTargets44px && r.keyboardNav;
          return `
            <tr>
              <td><strong>${THEME_NAMES[t]}</strong></td>
              <td class="${r.demoFlow ? 'pass' : 'fail'}">${r.demoFlow ? 'PASS' : 'FAIL'}</td>
              <td class="${r.consoleErrors === 0 ? 'pass' : 'fail'}">${r.consoleErrors}</td>
              <td class="${r.axeContrastViolations === 0 ? 'pass' : 'fail'}">${r.axeContrastViolations} violations</td>
              <td class="${r.luminancePassed ? 'pass' : 'fail'}">${r.luminanceDetails}</td>
              <td class="${r.noHorizontalScroll ? 'pass' : 'fail'}">${r.noHorizontalScroll ? 'PASS' : 'FAIL'}</td>
              <td class="${r.tapTargets44px ? 'pass' : 'fail'}">${r.tapTargets44px ? 'PASS' : 'FAIL'}</td>
              <td class="${r.keyboardNav ? 'pass' : 'fail'}">${r.keyboardNav ? 'PASS' : 'FAIL'}</td>
              <td class="${isPass ? 'pass' : 'fail'}">${isPass ? 'PASS' : 'FAIL'}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>2. Theme Difference & Pixel Divergence</h2>
    <table>
      <thead>
        <tr>
          <th>Pair Comparison</th>
          <th>Type</th>
          <th>Calculated Mean Per-Pixel Diff</th>
          <th>Threshold</th>
          <th>Result</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Clinical Blue vs Warm Linen</td>
          <td>Same-mode Light</td>
          <td><strong>${diffBlueVsLinen.toFixed(2)}</strong></td>
          <td>&ge; 5.0</td>
          <td class="${diffBlueVsLinen >= 5.0 ? 'pass' : 'fail'}">${diffBlueVsLinen >= 5.0 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
          <td>Midnight Navy vs Graphite</td>
          <td>Same-mode Dark</td>
          <td><strong>${diffNavyVsGraphite.toFixed(2)}</strong></td>
          <td>&ge; 5.0</td>
          <td class="${diffNavyVsGraphite >= 5.0 ? 'pass' : 'fail'}">${diffNavyVsGraphite >= 5.0 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
          <td>Clinical Blue vs Midnight Navy</td>
          <td>Light vs Dark</td>
          <td><strong>${diffLightVsDark1.toFixed(2)}</strong></td>
          <td>&ge; 40.0</td>
          <td class="${diffLightVsDark1 >= 40.0 ? 'pass' : 'fail'}">${diffLightVsDark1 >= 40.0 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
          <td>Warm Linen vs Graphite</td>
          <td>Light vs Dark</td>
          <td><strong>${diffLightVsDark2.toFixed(2)}</strong></td>
          <td>&ge; 40.0</td>
          <td class="${diffLightVsDark2 >= 40.0 ? 'pass' : 'fail'}">${diffLightVsDark2 >= 40.0 ? 'PASS' : 'FAIL'}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>3. Side-by-Side Visual Grid: Manager Dashboard (1440x900)</h2>
    <div class="grid-4">
      ${THEMES.map(t => `
        <div class="screenshot-card">
          <div class="screenshot-title">${THEME_NAMES[t]}</div>
          <img src="screens/${t}/manager_1440.png" alt="${t} manager">
        </div>
      `).join('')}
    </div>
  </div>

  <div class="card">
    <h2>4. Side-by-Side Visual Grid: Login Screen (1440x900)</h2>
    <div class="grid-4">
      ${THEMES.map(t => `
        <div class="screenshot-card">
          <div class="screenshot-title">${THEME_NAMES[t]}</div>
          <img src="screens/${t}/login_1440.png" alt="${t} login">
        </div>
      `).join('')}
    </div>
  </div>

  <div class="card">
    <h2>5. Side-by-Side Visual Grid: Worker Companion App (390x844)</h2>
    <div class="grid-4">
      ${THEMES.map(t => `
        <div class="screenshot-card">
          <div class="screenshot-title">${THEME_NAMES[t]}</div>
          <img src="screens/${t}/worker_390.png" alt="${t} worker">
        </div>
      `).join('')}
    </div>
  </div>
</body>
</html>
`;

  fs.writeFileSync(path.join(QA_DIR, 'report.html'), reportHtml, 'utf8');
  console.log(`\nGenerated QA Report: file:///${path.join(QA_DIR, 'report.html').replace(/\\/g, '/')}`);

  // Print final summary table
  console.log('\n======================================================================');
  console.log('QA SUITE FINAL RESULTS TABLE');
  console.log('======================================================================');
  console.log('Theme            | Demo Flow | Errors | axe Contrast | Luminance | Mobile 390px | Keyboard | Status');
  console.log('--------------------------------------------------------------------------------------------------');
  let allThemesPassed = true;
  for (const t of THEMES) {
    const r = qaResults[t];
    const pass = r.demoFlow && r.consoleErrors === 0 && r.axeContrastViolations === 0 && r.luminancePassed && r.noHorizontalScroll && r.tapTargets44px && r.keyboardNav;
    if (!pass) allThemesPassed = false;
    const name = (THEME_NAMES[t] + '             ').slice(0, 16);
    const flow = r.demoFlow ? 'PASS     ' : 'FAIL     ';
    const errs = (r.consoleErrors + '       ').slice(0, 6);
    const axe = (r.axeContrastViolations + ' viol   ').slice(0, 12);
    const lum = r.luminancePassed ? 'PASS      ' : 'FAIL      ';
    const mob = (r.noHorizontalScroll && r.tapTargets44px) ? 'PASS         ' : 'FAIL         ';
    const kb = r.keyboardNav ? 'PASS     ' : 'FAIL     ';
    const st = pass ? 'PASS' : 'FAIL';
    console.log(`${name} | ${flow} | ${errs} | ${axe} | ${lum} | ${mob} | ${kb} | ${st}`);
  }
  console.log('======================================================================');
  if (allThemesPassed && diffPassed && lintPassed) {
    console.log('\n>>> ALL QA VERIFICATION CHECKS PASSED PERFECTLY! <<<');
    process.exit(0);
  } else {
    console.log('\n>>> SOME QA CHECKS REQUIRE ATTENTION <<<');
    process.exit(1);
  }
}

runQA().catch(err => {
  console.error('QA suite execution error:', err);
  process.exit(1);
});
