/**
 * Nirantar Phase 8 Application Controller
 * Handles pure token themes, Sun/Moon quick toggle, 4-theme picker,
 * error/empty/loading states on all sections, full keyboard accessibility,
 * worker app with >=44px tap targets, and real-time synchronisation.
 */

// Global State
let currentUser = null;
let currentDemoDate = '2026-10-18';

// Theme system: 4 contrast-tested themes
const THEME_NAMES = {
  'clinical-blue': 'Clinical Blue',
  'warm-linen': 'Warm Linen',
  'midnight-navy': 'Midnight Navy',
  'graphite': 'Graphite'
};

const LIGHT_THEMES = ['clinical-blue', 'warm-linen'];
const DARK_THEMES = ['midnight-navy', 'graphite'];

let lastUsedLightTheme = 'clinical-blue';
let lastUsedDarkTheme = 'midnight-navy';

let currentTheme = (function() {
  let saved = localStorage.getItem('nirantar_theme');
  if (saved === 'clinical_teal' || saved === 'ocean_blue') saved = 'clinical-blue';
  if (saved === 'midnight_care') saved = 'midnight-navy';
  if (saved === 'aurora') saved = 'graphite';
  if (!THEME_NAMES[saved]) {
    const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    saved = isDark ? 'midnight-navy' : 'clinical-blue';
  }
  return saved;
})();

let currentCaseFilter = 'all';
let currentSortColumn = 'default';
let currentSortDirection = 'asc';
let showAllRows = false;
let selectedVillageId = 'VIL-2'; // Default: Kalyanpur Basti
let guidedDemoStep = 0;

let cachedCases = [];
let cachedVillages = [];
let cachedFacilities = [];
let cachedPatients = [];
let cachedOutcomes = [];

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  checkAuth();
  setupKeyboardAccessibility();
});

// =========================================================================
// 1. THEME SWITCHER & ACCESSIBILITY
// =========================================================================
function initTheme() {
  selectTheme(currentTheme, false);
}

function selectTheme(themeName, persist = true) {
  if (!THEME_NAMES[themeName]) themeName = 'clinical-blue';
  currentTheme = themeName;

  if (LIGHT_THEMES.includes(themeName)) {
    lastUsedLightTheme = themeName;
  } else {
    lastUsedDarkTheme = themeName;
  }

  // Set data-theme on <html> directly
  document.documentElement.setAttribute('data-theme', themeName);
  
  if (persist) {
    localStorage.setItem('nirantar_theme', themeName);
    if (currentUser) {
      fetch('/api/user/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: themeName })
      }).catch(() => {});
    }
  }

  updateThemeUI();
  closeAllThemeMenus();
}

function toggleLightDarkTheme() {
  if (LIGHT_THEMES.includes(currentTheme)) {
    selectTheme(lastUsedDarkTheme);
  } else {
    selectTheme(lastUsedLightTheme);
  }
}

function updateThemeUI() {
  const isDark = DARK_THEMES.includes(currentTheme);
  const quickIcon = isDark ? '☀' : '🌙';
  const quickTitle = isDark ? 'Switch to Light theme' : 'Switch to Dark theme';

  // Update quick toggle buttons and icons
  ['headerQuickToggleIcon', 'authQuickToggleIcon', 'workerQuickToggleIcon'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = quickIcon;
  });

  ['headerThemeQuickToggle', 'authThemeQuickToggle'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.title = quickTitle;
  });

  // Update label display
  document.querySelectorAll('.theme-name-display').forEach(el => {
    el.textContent = THEME_NAMES[currentTheme];
  });

  // Update active state on menu options
  document.querySelectorAll('.theme-option-card').forEach(card => {
    card.classList.remove('active');
  });

  ['opt-', 'authOpt-'].forEach(prefix => {
    const activeCard = document.getElementById(prefix + currentTheme);
    if (activeCard) activeCard.classList.add('active');
  });

  // Re-render map so SVG theme enhancements apply
  renderDistrictMapSvg();
}

function toggleThemeMenu(panelId = 'headerThemeMenuPanel') {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  const isShowing = panel.classList.contains('show');
  closeAllThemeMenus();
  if (!isShowing) {
    panel.classList.add('show');
  }
}

function closeAllThemeMenus() {
  document.querySelectorAll('.theme-menu-panel').forEach(p => p.classList.remove('show'));
}

// Global click outside theme dropdowns
window.addEventListener('click', (e) => {
  if (!e.target.closest('.theme-switcher-group') && !e.target.closest('.theme-toggle-btn')) {
    closeAllThemeMenus();
  }
});

function setupKeyboardAccessibility() {
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllThemeMenus();
      closeAssignModal();
    }
  });
}

// =========================================================================
// 2. AUTHENTICATION & PERSONA MANAGEMENT
// =========================================================================
let authPersona = 'manager'; // 'manager' | 'worker'
let authMode = 'login';       // 'login' | 'signup'

function setAuthPersona(persona) {
  authPersona = persona;
  const btnMgr = document.getElementById('authPersonaMgr');
  const btnWrk = document.getElementById('authPersonaWorker');
  if (btnMgr && btnWrk) {
    if (persona === 'manager') {
      btnMgr.style.background = 'var(--surface)';
      btnMgr.style.color = 'var(--primary)';
      btnWrk.style.background = 'transparent';
      btnWrk.style.color = 'var(--muted)';
    } else {
      btnWrk.style.background = 'var(--surface)';
      btnWrk.style.color = 'var(--primary)';
      btnMgr.style.background = 'transparent';
      btnMgr.style.color = 'var(--muted)';
    }
  }
  updateRoleCards();
  const inviteInput = document.getElementById('authInviteInput');
  if (inviteInput) {
    inviteInput.placeholder = persona === 'manager' 
      ? 'e.g. NIRANTAR_MGR_2026' 
      : 'e.g. NIRANTAR_FIELD_2026';
  }
}

function updateRoleCards() {
  const container = document.getElementById('roleCardsGrid');
  if (!container) return;
  
  if (authPersona === 'manager') {
    container.innerHTML = `
      <label class="card" style="padding:10px; cursor:pointer; display:flex; align-items:center; gap:8px;">
        <input type="radio" name="signupRole" value="program_manager" checked style="accent-color:var(--primary);">
        <div>
          <div style="font-weight:700; font-size:12px;">Program Manager</div>
          <div style="font-size:10px; color:var(--muted);">District Lead</div>
        </div>
      </label>
      <label class="card" style="padding:10px; cursor:pointer; display:flex; align-items:center; gap:8px;">
        <input type="radio" name="signupRole" value="coordinator" style="accent-color:var(--primary);">
        <div>
          <div style="font-weight:700; font-size:12px;">Coordinator</div>
          <div style="font-size:10px; color:var(--muted);">Operations & Caseload</div>
        </div>
      </label>
    `;
  } else {
    container.innerHTML = `
      <label class="card" style="padding:10px; cursor:pointer; display:flex; align-items:center; gap:8px;">
        <input type="radio" name="signupRole" value="care_worker" checked style="accent-color:var(--primary);">
        <div>
          <div style="font-weight:700; font-size:12px;">Care Worker</div>
          <div style="font-size:10px; color:var(--muted);">Field Tasks</div>
        </div>
      </label>
      <label class="card" style="padding:10px; cursor:pointer; display:flex; align-items:center; gap:8px;">
        <input type="radio" name="signupRole" value="supervisor" style="accent-color:var(--primary);">
        <div>
          <div style="font-weight:700; font-size:12px;">Supervisor</div>
          <div style="font-size:10px; color:var(--muted);">Level 1 Escalations</div>
        </div>
      </label>
      <label class="card" style="padding:10px; cursor:pointer; display:flex; align-items:center; gap:8px;">
        <input type="radio" name="signupRole" value="doctor" style="accent-color:var(--primary);">
        <div>
          <div style="font-weight:700; font-size:12px;">Doctor</div>
          <div style="font-size:10px; color:var(--muted);">Clinical Escalations</div>
        </div>
      </label>
    `;
  }
}

function toggleAuthMode(e) {
  if (e) e.preventDefault();
  authMode = authMode === 'login' ? 'signup' : 'login';
  const title = document.getElementById('authFormTitle');
  const prompt = document.getElementById('authTogglePrompt');
  const link = document.getElementById('authToggleLink');
  const submitBtn = document.getElementById('authSubmitBtn');
  const signupFields = document.getElementById('signupOnlyFields');
  const strengthBox = document.getElementById('passwordStrengthBox');

  if (authMode === 'signup') {
    title.textContent = 'Create Nirantar Account';
    prompt.textContent = 'Already registered?';
    link.textContent = 'Sign In';
    submitBtn.textContent = 'Create Account';
    signupFields.style.display = 'block';
    strengthBox.style.display = 'block';
    updateRoleCards();
  } else {
    title.textContent = 'Sign In to Nirantar';
    prompt.textContent = 'Need an account?';
    link.textContent = 'Sign Up';
    submitBtn.textContent = 'Sign In';
    signupFields.style.display = 'none';
    strengthBox.style.display = 'none';
  }
}

function togglePasswordVisibility() {
  const input = document.getElementById('authPasswordInput');
  input.type = input.type === 'password' ? 'text' : 'password';
}

function updatePasswordStrength(val) {
  const bar = document.getElementById('passwordStrengthBar');
  const txt = document.getElementById('passwordStrengthText');
  if (!bar || !txt) return;

  if (val.length < 8) {
    bar.style.width = '25%';
    bar.style.backgroundColor = 'var(--urgent)';
    txt.textContent = 'Min 8 characters required';
  } else if (!/[A-Z]/.test(val) || !/[0-9]/.test(val)) {
    bar.style.width = '60%';
    bar.style.backgroundColor = 'var(--watch)';
    txt.textContent = 'Medium (Add numbers & uppercase)';
  } else {
    bar.style.width = '100%';
    bar.style.backgroundColor = 'var(--safe)';
    txt.textContent = 'Strong password';
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const errorBox = document.getElementById('authErrorAlert');
  errorBox.style.display = 'none';

  const email = document.getElementById('authEmailInput').value;
  const password = document.getElementById('authPasswordInput').value;

  try {
    let res;
    if (authMode === 'signup') {
      const name = document.getElementById('authNameInput').value;
      const roleEl = document.querySelector('input[name="signupRole"]:checked');
      const role = roleEl ? roleEl.value : (authPersona === 'manager' ? 'program_manager' : 'care_worker');
      const inviteCode = document.getElementById('authInviteInput').value;

      res = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, role, invite_code: inviteCode })
      });
    } else {
      res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
    }

    const data = await res.json();
    if (!res.ok) {
      errorBox.textContent = data.error || 'Authentication failed';
      errorBox.style.display = 'block';
      return;
    }

    currentUser = data.user;
    const localTheme = localStorage.getItem('nirantar_theme');
    if (localTheme && THEME_NAMES[localTheme]) {
      selectTheme(localTheme, true);
    } else if (currentUser.theme) {
      selectTheme(currentUser.theme, true);
    }
    showToast(`Welcome, ${currentUser.name}!`);
    routeByRole();
  } catch (err) {
    errorBox.textContent = 'Network error connecting to server';
    errorBox.style.display = 'block';
  }
}

async function demoLogin(email) {
  const errorBox = document.getElementById('authErrorAlert');
  if (errorBox) errorBox.style.display = 'none';
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: 'NirantarDemo2026!' })
    });
    const data = await res.json();
    if (!res.ok) {
      if (errorBox) {
        errorBox.textContent = data.error || 'Demo login failed';
        errorBox.style.display = 'block';
      }
      return;
    }
    currentUser = data.user;
    const localTheme = localStorage.getItem('nirantar_theme');
    if (localTheme && THEME_NAMES[localTheme]) {
      selectTheme(localTheme, true);
    } else if (currentUser.theme) {
      selectTheme(currentUser.theme, true);
    }
    showToast(`Logged in as ${currentUser.name}`);
    routeByRole();
  } catch (err) {
    if (errorBox) {
      errorBox.textContent = 'Server connection failed';
      errorBox.style.display = 'block';
    }
  }
}

async function checkAuth() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      const data = await res.json();
      currentUser = data.user;
      const localTheme = localStorage.getItem('nirantar_theme');
      if (localTheme && THEME_NAMES[localTheme]) {
        selectTheme(localTheme, false);
      } else if (currentUser.theme) {
        selectTheme(currentUser.theme, false);
      }
      routeByRole();
    } else {
      showAuthScreen();
    }
  } catch (e) {
    showAuthScreen();
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  currentUser = null;
  showToast('Logged out successfully');
  showAuthScreen();
}

function showAuthScreen() {
  document.getElementById('authScreen').style.display = 'flex';
  document.getElementById('appScreen').style.display = 'none';
  setAuthPersona('manager');
}

function routeByRole() {
  if (!currentUser) {
    showAuthScreen();
    return;
  }
  document.getElementById('authScreen').style.display = 'none';
  document.getElementById('appScreen').style.display = 'block';

  // Set user chip
  const initials = currentUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  document.getElementById('userAvatarInitials').textContent = initials || 'U';
  document.getElementById('userProfileName').textContent = currentUser.name;
  document.getElementById('userProfileRole').textContent = currentUser.role;

  const isManagerRole = ['program_manager', 'coordinator'].includes(currentUser.role);
  if (isManagerRole) {
    document.getElementById('managerDashboardView').style.display = 'block';
    document.getElementById('managerSectionNav').style.display = 'flex';
    document.getElementById('workerAppView').style.display = 'none';
    document.getElementById('managerGreeting').textContent = `Welcome, ${currentUser.name.split(' ')[0]}`;
    initManagerDashboard();
  } else {
    document.getElementById('managerDashboardView').style.display = 'none';
    document.getElementById('managerSectionNav').style.display = 'none';
    document.getElementById('workerAppView').style.display = 'block';
    initWorkerApp();
  }
}

// =========================================================================
// 3. CLOCK & ESCALATION CONTROLS
// =========================================================================
async function fetchClockDate() {
  try {
    const res = await fetch('/api/clock');
    if (res.ok) {
      const data = await res.json();
      currentDemoDate = data.current_date;
      formatClockDisplay(currentDemoDate);
    }
  } catch (e) {}
}

function formatClockDisplay(dateStr) {
  const d = new Date(dateStr);
  const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  document.getElementById('appDemoClockDisplay').textContent = formatted;
}

async function advanceDemoClock(days = 1) {
  const btn = document.getElementById('btnAdvanceClock');
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/clock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'advance_day', days: days })
    });
    const data = await res.json();
    if (res.ok) {
      currentDemoDate = data.current_date;
      formatClockDisplay(currentDemoDate);
      const newEsc = data.escalation_result ? data.escalation_result.escalated_count : 0;
      showToast(`Clock advanced to ${currentDemoDate} (+${newEsc} escalated)`);
      await refreshAllData();
      if (newEsc > 0) {
        highlightEscalatedRows();
      }
    }
  } catch (e) {
    showToast('Failed to advance clock', '⚠');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function triggerEscalationEngine() {
  const btn = document.getElementById('btnRunEsc');
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/escalation/run', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(`Escalation run complete: ${data.escalated_count} new escalations`);
      await refreshAllData();
      if (data.escalated_count > 0) {
        highlightEscalatedRows();
      }
    }
  } catch (e) {
    showToast('Escalation run failed', '⚠');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function highlightEscalatedRows() {
  document.querySelectorAll('.row-escalated').forEach(row => {
    row.classList.remove('escalation-flash');
    void row.offsetWidth; // trigger reflow
    row.classList.add('escalation-flash');
  });
}

async function confirmResetDemo() {
  if (!confirm('Restore all synthetic demo cases, facilities and stock to their seeded state?\n\n(Signed-up user accounts will be preserved).')) {
    return;
  }
  try {
    const res = await fetch('/api/reset', { method: 'POST' });
    if (res.ok) {
      showToast('Demo data restored to initial seed state');
      await refreshAllData();
    }
  } catch (e) {
    showToast('Failed to reset demo data', '⚠');
  }
}

async function refreshAllData() {
  await Promise.all([
    fetchClockDate(),
    fetchScorecard(),
    fetchCases(),
    fetchGaps(),
    fetchWhatWorks()
  ]);
}

// =========================================================================
// 4. SCORECARD SECTION
// =========================================================================
async function fetchScorecard() {
  const errorBox = document.getElementById('scorecardErrorBox');
  const grid = document.getElementById('scorecardCardsGrid');
  try {
    const sliderVal = document.getElementById('assumptionRange').value;
    const res = await fetch(`/api/scorecard?assumption=${sliderVal}`);
    if (!res.ok) throw new Error('Failed to fetch scorecard');
    const data = await res.json();

    if (errorBox) errorBox.style.display = 'none';
    if (grid) grid.style.display = 'grid';

    document.getElementById('statActivePatients').textContent = data.active_patients ?? 0;
    document.getElementById('statPatientsAtRisk').textContent = data.patients_at_risk ?? 0;
    const compRate = data.follow_up_completion_rate ?? data.completion_rate_percent ?? (data.completion_rate != null ? Math.round(data.completion_rate * 1000) / 10 : 0);
    document.getElementById('statCompletionRate').textContent = `${compRate}%`;
    document.getElementById('statCompletionRatio').textContent = `${data.resolved_cases ?? 0} resolved / ${data.total_cases ?? 0} total`;
    document.getElementById('statMedianDays').innerHTML = `${data.median_days_to_resolve ?? 0} <span style="font-size:13px; font-weight:500; color:var(--muted);">days</span>`;
    document.getElementById('statOpenEscalated').textContent = data.open_and_escalated ?? data.open_and_escalated_cases ?? 0;
    document.getElementById('statPastDue').textContent = data.cases_past_due ?? 0;
    const hoursVal = data.hours_saved ?? data.coordinator_hours_saved ?? 0;
    document.getElementById('statHoursSaved').innerHTML = `${hoursVal} <span style="font-size:13px; font-weight:500; color:var(--muted);">hrs</span>`;

    // Workers breakdown
    const listCont = document.getElementById('statWorkersList');
    if (listCont && data.cases_per_worker) {
      if (Array.isArray(data.cases_per_worker)) {
        listCont.innerHTML = data.cases_per_worker.map(item => `
          <div style="display:flex; justify-content:space-between; padding:2px 0; border-bottom:1px solid var(--border);">
            <span style="color:var(--text);">${item.worker_name || item.worker_id}</span>
            <span class="pill pill-safe" style="font-size:10px; padding:1px 6px;">${item.case_count} cases</span>
          </div>
        `).join('');
      } else {
        listCont.innerHTML = Object.entries(data.cases_per_worker).map(([w, c]) => `
          <div style="display:flex; justify-content:space-between; padding:2px 0; border-bottom:1px solid var(--border);">
            <span style="color:var(--text);">${w}</span>
            <span class="pill pill-safe" style="font-size:10px; padding:1px 6px;">${c} cases</span>
          </div>
        `).join('');
      }
    }
  } catch (err) {
    if (errorBox) errorBox.style.display = 'flex';
    if (grid) grid.style.display = 'none';
  }
}

function handleAssumptionSlider(val) {
  document.getElementById('statAssumptionLabel').textContent = `${val}m / call`;
  fetchScorecard();
}

function animateNumber(elementId, targetValue) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const target = parseInt(targetValue, 10);
  if (isNaN(target)) {
    el.textContent = targetValue;
    return;
  }
  const current = parseInt(el.textContent, 10) || 0;
  const step = target > current ? 1 : -1;
  if (current === target) {
    el.textContent = target;
    return;
  }
  let c = current;
  const interval = setInterval(() => {
    c += step;
    el.textContent = c;
    if (c === target) clearInterval(interval);
  }, 40);
}

// =========================================================================
// 5. CASE QUEUE (SORTING, FILTERING & BUG FIXES)
// =========================================================================
async function fetchCases() {
  const errorBox = document.getElementById('caseQueueErrorBox');
  const table = document.getElementById('caseMasterTable');
  try {
    const res = await fetch('/api/cases');
    if (!res.ok) throw new Error('Failed to fetch cases');
    const data = await res.json();
    cachedCases = data.cases || [];

    if (errorBox) errorBox.style.display = 'none';
    if (table) table.style.display = 'table';

    renderCasesTableUI();
    if (['care_worker', 'supervisor', 'doctor'].includes(currentUser.role)) {
      renderWorkerCardsUI();
    }
  } catch (err) {
    if (errorBox) errorBox.style.display = 'flex';
    if (table) table.style.display = 'none';
  }
}

function setCaseChipFilter(filter) {
  currentCaseFilter = filter;
  ['All', 'Esc', 'Past', 'Assigned', 'Resolved'].forEach(name => {
    const btn = document.getElementById(`chipFilter${name}`);
    if (btn) {
      btn.style.background = 'transparent';
      btn.style.color = 'var(--text)';
      btn.style.fontWeight = 'normal';
    }
  });
  const map = { all: 'All', escalated: 'Esc', past_due: 'Past', assigned: 'Assigned', resolved: 'Resolved' };
  const activeBtn = document.getElementById(`chipFilter${map[filter]}`);
  if (activeBtn) {
    activeBtn.style.background = 'var(--soft)';
    activeBtn.style.color = 'var(--primary-strong)';
    activeBtn.style.fontWeight = '700';
  }
  renderCasesTableUI();
}

function toggleTableSort(col) {
  if (currentSortColumn === col) {
    if (currentSortDirection === 'asc') {
      currentSortDirection = 'desc';
    } else {
      currentSortColumn = 'default';
      currentSortDirection = 'asc';
    }
  } else {
    currentSortColumn = col;
    currentSortDirection = 'asc';
  }

  // Update indicators
  ['patient', 'risk', 'village', 'worker', 'status', 'due_date'].forEach(c => {
    const ind = document.getElementById(`sortIndicator-${c}`);
    if (ind) {
      if (currentSortColumn === c) {
        ind.textContent = currentSortDirection === 'asc' ? '▲' : '▼';
        ind.style.color = 'var(--primary)';
      } else {
        ind.textContent = '⇅';
        ind.style.color = 'var(--muted)';
      }
    }
  });

  renderCasesTableUI();
}

function renderCasesTableUI() {
  const tbody = document.getElementById('caseQueueTbody');
  const counterEl = document.getElementById('caseCounterDisplay');
  const showMoreBox = document.getElementById('showMoreContainer');
  const showMoreBtn = document.getElementById('btnShowMore');
  if (!tbody) return;

  const workerFilter = document.getElementById('filterWorkerSelect').value;
  const villageFilter = document.getElementById('filterVillageSelect').value;
  const search = document.getElementById('caseSearchInput').value.toLowerCase().trim();

  // 1. Filtering
  let list = cachedCases.filter(c => {
    if (currentCaseFilter === 'escalated' && c.status !== 'escalated') return false;
    if (currentCaseFilter === 'past_due' && !c.is_past_due) return false;
    if (currentCaseFilter === 'assigned' && c.status !== 'assigned') return false;
    if (currentCaseFilter === 'resolved' && c.status !== 'resolved') return false;

    if (workerFilter && c.owner_id !== workerFilter) return false;
    if (villageFilter && c.village_name !== villageFilter && !c.village_name.includes(villageFilter)) return false;

    if (search) {
      const pName = (c.patient_name || '').toLowerCase();
      const pId = (c.patient_id || '').toLowerCase();
      const vName = (c.village_name || '').toLowerCase();
      const wName = (c.owner_name || '').toLowerCase();
      if (!pName.includes(search) && !pId.includes(search) && !vName.includes(search) && !wName.includes(search)) {
        return false;
      }
    }
    return true;
  });

  // 2. Sorting
  if (currentSortColumn !== 'default') {
    list.sort((a, b) => {
      let va, vb;
      if (currentSortColumn === 'patient') {
        va = a.patient_name; vb = b.patient_name;
      } else if (currentSortColumn === 'risk') {
        va = a.risk_score; vb = b.risk_score;
      } else if (currentSortColumn === 'village') {
        va = a.village_name; vb = b.village_name;
      } else if (currentSortColumn === 'worker') {
        va = a.owner_name; vb = b.owner_name;
      } else if (currentSortColumn === 'status') {
        va = a.status; vb = b.status;
      } else if (currentSortColumn === 'due_date') {
        va = a.due_date; vb = b.due_date;
      }
      if (va < vb) return currentSortDirection === 'asc' ? -1 : 1;
      if (va > vb) return currentSortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }

  // Counter
  counterEl.textContent = `Showing ${Math.min(showAllRows ? list.length : 10, list.length)} of ${list.length}`;
  if (list.length > 10) {
    showMoreBox.style.display = 'block';
    showMoreBtn.textContent = showAllRows ? 'Show Less Cases' : `Show More (${list.length - 10} remaining)`;
  } else {
    showMoreBox.style.display = 'none';
  }

  const displayedList = showAllRows ? list : list.slice(0, 10);

  if (displayedList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--muted);">No cases match the selected filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = displayedList.map(c => {
    const isResolved = c.status === 'resolved';
    const isEscalated = c.status === 'escalated';
    const isPastDue = c.is_past_due;

    let rowStyle = 'border-bottom:1px solid var(--border);';
    if (isResolved) rowStyle += ' background:var(--surface-2);';

    // Risk Pill
    const riskPillClass = c.risk_category === 'Urgent' ? 'pill-urgent' : (c.risk_category === 'Watch' ? 'pill-watch' : 'pill-safe');

    // Status & Escalation Badge (Single arrow)
    let statusBadge = '';
    if (isEscalated) {
      const tgt = c.escalated_to === 'supervisor' ? 'Supervisor' : (c.escalated_to === 'doctor' ? 'Doctor' : 'Program Manager');
      statusBadge = `<span class="pill pill-escalated">↑ Escalated to ${tgt}</span>`;
    } else if (isResolved) {
      statusBadge = `<span class="pill pill-safe">Resolved (${c.resolved_at || 'Done'})</span>`;
    } else if (c.status === 'in_progress') {
      statusBadge = `<span class="pill pill-watch">In Progress</span>`;
    } else if (c.status === 'closed_lost') {
      statusBadge = `<span class="pill" style="background:var(--border); color:var(--muted);">Closed Lost</span>`;
    } else {
      statusBadge = `<span class="pill pill-assigned">Assigned</span>`;
    }

    // Due Date
    let dueHtml = c.due_date;
    if (isPastDue) {
      dueHtml = `<span style="color:var(--urgent); font-weight:700; display:inline-flex; align-items:center; gap:4px;">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        ${c.due_date} (Past due)
      </span>`;
    } else if (c.is_due_today) {
      dueHtml = `<span style="color:var(--watch); font-weight:700;">${c.due_date} (Today)</span>`;
    }

    // Reason & Rescue text
    const reasonText = (c.reason || 'unspecified').replace(/_/g, ' ');
    const actionText = (c.action || 'counselling').replace(/_/g, ' ');

    let actionCell = '';
    if (isResolved) {
      actionCell = `<span style="font-size:12px; color:var(--muted); font-weight:500;">Completed</span>`;
    } else {
      actionCell = `
        <div style="display:flex; gap:6px;">
          <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="resolveCaseInQueue('${c.id}')">Resolve</button>
          ${!isEscalated ? `<button class="btn btn-purple" style="padding:4px 8px; font-size:11px;" onclick="escalateCaseInQueue('${c.id}')">Escalate</button>` : ''}
        </div>
      `;
    }

    return `
      <tr style="${rowStyle}" class="${isEscalated ? 'row-escalated' : ''}" id="caseRow-${c.id}">
        <td style="padding:12px 14px;">
          <div style="font-weight:700; color:var(--text); font-size:14px;">${c.patient_name}</div>
          <div style="font-size:11px; color:var(--muted);">${c.patient_id} · ${c.gender}, ${c.age}y</div>
        </td>
        <td style="padding:12px 14px;">
          <div style="font-weight:700;">${c.condition}</div>
          <div style="margin-top:2px;">
            <span class="pill ${riskPillClass}" style="font-size:10px; padding:2px 7px;">${c.risk_category} (${c.risk_score})</span>
          </div>
        </td>
        <td style="padding:12px 14px; font-weight:500;">${c.village_name}</td>
        <td style="padding:12px 14px;">
          <div style="font-weight:600;">${c.owner_name}</div>
          <div style="font-size:10px; color:var(--muted);">${c.owner_id}</div>
        </td>
        <td style="padding:12px 14px;">${statusBadge}</td>
        <td style="padding:12px 14px;">${dueHtml}</td>
        <td style="padding:12px 14px;">
          <div style="font-weight:700; color:var(--text); font-size:12px; text-transform:capitalize;">${reasonText}</div>
          <div style="font-size:11px; color:var(--muted); text-transform:capitalize;">${actionText}</div>
        </td>
        <td style="padding:12px 14px;">${actionCell}</td>
      </tr>
    `;
  }).join('');
}

function toggleShowMoreRows() {
  showAllRows = !showAllRows;
  renderCasesTableUI();
}

async function resolveCaseInQueue(caseId) {
  try {
    const res = await fetch(`/api/cases/${caseId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'resolved' })
    });
    if (res.ok) {
      showToast(`Case ${caseId} marked as resolved!`);
      await Promise.all([fetchCases(), fetchScorecard()]);
    }
  } catch (e) {
    showToast('Failed to resolve case', '⚠');
  }
}

async function escalateCaseInQueue(caseId) {
  try {
    const res = await fetch(`/api/cases/${caseId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'escalated' })
    });
    if (res.ok) {
      showToast(`Case ${caseId} escalated to supervisor!`);
      await Promise.all([fetchCases(), fetchScorecard()]);
    }
  } catch (e) {
    showToast('Failed to escalate case', '⚠');
  }
}

// =========================================================================
// 6. ASSIGN TASK MODAL
// =========================================================================
async function openAssignTaskModal() {
  const modal = document.getElementById('assignModalBackdrop');
  const patientSelect = document.getElementById('modalAssignPatient');
  const dueInput = document.getElementById('modalAssignDueDate');
  if (!modal || !patientSelect) return;

  // Set default due date to demo_date + 2 days
  const d = new Date(currentDemoDate);
  d.setDate(d.getDate() + 2);
  dueInput.value = d.toISOString().split('T')[0];

  // Populate patients if not done
  if (cachedPatients.length === 0) {
    try {
      const res = await fetch('/api/patients');
      if (res.ok) {
        const data = await res.json();
        cachedPatients = data.patients || [];
      }
    } catch (e) {}
  }

  patientSelect.innerHTML = cachedPatients.map(p => `
    <option value="${p.id}">
      ${p.name} (${p.condition} · ${p.village_name} · Risk: ${p.risk_score})
    </option>
  `).join('');

  modal.style.display = 'flex';
}

function closeAssignModal() {
  const modal = document.getElementById('assignModalBackdrop');
  if (modal) modal.style.display = 'none';
}

async function handleAssignFormSubmit(e) {
  e.preventDefault();
  const patientId = document.getElementById('modalAssignPatient').value;
  const ownerId = document.getElementById('modalAssignWorker').value;
  const dueDate = document.getElementById('modalAssignDueDate').value;
  const reason = document.getElementById('modalAssignReason').value;
  const action = document.getElementById('modalAssignAction').value;

  try {
    const res = await fetch('/api/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: patientId,
        owner_id: ownerId,
        due_date: dueDate,
        reason: reason,
        action: action
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Task assigned successfully (${data.case_id})`);
      closeAssignModal();
      await Promise.all([fetchCases(), fetchScorecard()]);
    } else {
      alert(data.error || 'Failed to assign task');
    }
  } catch (err) {
    showToast('Network error assigning task', '⚠');
  }
}

// =========================================================================
// 7. GAP RANKING & INTERACTIVE SVG MAP
// =========================================================================
async function fetchGaps() {
  const errorBox = document.getElementById('gapsErrorBox');
  const grid = document.getElementById('gapsGridContainer');
  try {
    const res = await fetch('/api/gaps');
    if (!res.ok) throw new Error('Failed to fetch gaps');
    const data = await res.json();
    cachedVillages = (data.villages || []).map((v, i) => ({
      ...v,
      rank: v.rank != null ? v.rank : (i + 1)
    }));

    if (errorBox) errorBox.style.display = 'none';
    if (grid) grid.style.display = 'grid';

    renderGapsRankingTable();
    renderDistrictMapSvg();
    updateSelectedVillageDetail(selectedVillageId);
  } catch (err) {
    if (errorBox) errorBox.style.display = 'flex';
    if (grid) grid.style.display = 'none';
  }
}

function renderGapsRankingTable() {
  const tbody = document.getElementById('gapsRankingTbody');
  if (!tbody) return;

  tbody.innerHTML = cachedVillages.map((v, idx) => {
    const f = v.factors;
    const rank = v.rank != null ? v.rank : (idx + 1);
    const isSelected = v.village_id === selectedVillageId;
    return `
      <tr style="border-bottom:1px solid var(--border); cursor:pointer; ${isSelected ? 'background:var(--soft);' : ''}"
          onclick="selectVillageOnMap('${v.village_id}')"
          onmouseenter="hoverVillageHighlight('${v.village_id}', true)"
          onmouseleave="hoverVillageHighlight('${v.village_id}', false)"
          id="gapRow-${v.village_id}">
        <td style="padding:10px 8px;">
          <div style="font-weight:700; color:var(--text); font-size:13px; display:flex; align-items:center; gap:6px;">
            <span class="pill ${rank <= 2 ? 'pill-urgent' : (rank <= 4 ? 'pill-watch' : 'pill-safe')}" style="font-size:10px; padding:1px 6px;">#${rank}</span>
            <span>${v.village_name}</span>
          </div>
          <div style="font-size:10px; color:var(--muted); margin-top:2px;">${v.population} residents · ${v.high_risk_patients} high risk</div>
        </td>
        <td style="padding:10px 8px; color:var(--muted);">${v.facility_name}</td>
        <td style="padding:10px 8px; font-weight:600;">${v.distance_km} km</td>
        <td style="padding:10px 8px;">
          <span style="font-size:14px; font-weight:800; color:var(--primary-strong); font-family:var(--font-numeric);">${v.gap_score}</span>
        </td>
        <td style="padding:10px 8px;">
          <div class="stacked-bar">
            <div class="stacked-risk" style="width:${f.risk_factor}%;"></div>
            <div class="stacked-dist" style="width:${f.distance_factor}%;"></div>
            <div class="stacked-stock" style="width:${f.stock_factor}%;"></div>
          </div>
          <div style="font-size:9px; color:var(--muted); margin-top:2px;">
            R:${f.risk_factor} D:${f.distance_factor} S:${f.stock_factor}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function selectVillageOnMap(villageId) {
  selectedVillageId = villageId;
  renderDistrictMapSvg();
  renderGapsRankingTable();
  updateSelectedVillageDetail(villageId);
}

function hoverVillageHighlight(villageId, isHovering) {
  const node = document.getElementById(`mapNode-${villageId}`);
  if (node) {
    node.style.transform = isHovering ? 'scale(1.15)' : 'scale(1)';
    node.style.transition = 'transform 150ms ease';
  }
}

function updateSelectedVillageDetail(villageId) {
  const v = cachedVillages.find(vil => vil.village_id === villageId);
  if (!v) return;

  const rank = v.rank != null ? v.rank : (cachedVillages.findIndex(vil => vil.village_id === villageId) + 1);
  document.getElementById('selVilName').textContent = `#${rank} ${v.village_name}`;
  document.getElementById('selVilPop').textContent = `Pop: ${v.population}`;
  document.getElementById('selVilScore').textContent = v.gap_score;
  document.getElementById('selVilRisk').textContent = `${v.high_risk_patients} patients (${v.share_high_risk_percent}%)`;
  document.getElementById('selVilDist').textContent = `${v.distance_km} km to ${v.facility_name}`;
  document.getElementById('selVilStock').textContent = `${v.stockout_count} medicines`;

  const f = v.factors;
  document.getElementById('selVilBarR').style.width = `${f.risk_factor}%`;
  document.getElementById('selVilBarD').style.width = `${f.distance_factor}%`;
  document.getElementById('selVilBarS').style.width = `${f.stock_factor}%`;

  document.getElementById('selVilFactorsText').innerHTML = `
    <span><strong>R: ${f.risk_factor}</strong> (High-risk %)</span>
    <span><strong>D: ${f.distance_factor}</strong> (Distance)</span>
    <span><strong>S: ${f.stock_factor}</strong> (Stockout)</span>
  `;
}

function renderDistrictMapSvg() {
  const mapContainer = document.getElementById('mapSvgBox');
  if (!mapContainer || cachedVillages.length === 0) return;

  const facLocations = {
    'FAC-1': { x: 230, y: 155, name: 'Rampur PHC' },
    'FAC-2': { x: 375, y: 105, name: 'Bilaspur Sub-centre' },
    'FAC-3': { x: 135, y: 260, name: 'Chandpur CHC' },
    'FAC-4': { x: 80, y: 75, name: 'Kalyanpur HWC' }
  };

  const vilLocations = {
    'VIL-2': { x: 65, y: 145, fac: 'FAC-4' },   // Kalyanpur Basti
    'VIL-1': { x: 420, y: 65, fac: 'FAC-2' },   // Bilaspur Kalan
    'VIL-4': { x: 395, y: 180, fac: 'FAC-2' },  // Shivpur Khurd
    'VIL-3': { x: 295, y: 240, fac: 'FAC-1' },  // Rampur Dehat
    'VIL-5': { x: 195, y: 80, fac: 'FAC-1' },   // Haripur Mandi
    'VIL-6': { x: 195, y: 285, fac: 'FAC-3' }   // Chandpur Gaon
  };

  let linesSvg = '';
  cachedVillages.forEach(v => {
    const vPos = vilLocations[v.village_id];
    if (vPos) {
      const fPos = facLocations[vPos.fac];
      if (fPos) {
        const mx = (vPos.x + fPos.x) / 2;
        const my = (vPos.y + fPos.y) / 2 - 8;
        linesSvg += `
          <line x1="${vPos.x}" y1="${vPos.y}" x2="${fPos.x}" y2="${fPos.y}" 
                stroke="var(--border)" stroke-width="1.8" stroke-dasharray="4,4" />
          <rect x="${mx - 15}" y="${my - 8}" width="30" height="15" rx="4" fill="var(--surface)" stroke="var(--border)" stroke-width="1"/>
          <text x="${mx}" y="${my + 3}" font-size="9" fill="var(--muted)" font-weight="700" text-anchor="middle">${v.distance_km}km</text>
        `;
      }
    }
  });

  // Facilities
  let facSvg = Object.entries(facLocations).map(([fId, f]) => {
    const hasStockouts = ['FAC-1', 'FAC-2', 'FAC-4'].includes(fId);
    const badge = hasStockouts ? `
      <circle cx="${f.x + 11}" cy="${f.y - 11}" r="5" fill="var(--urgent)" stroke="var(--surface)" stroke-width="1.5" />
      <text x="${f.x + 11}" y="${f.y - 9}" font-size="7" fill="var(--on-primary)" font-weight="800" text-anchor="middle">!</text>
    ` : '';

    return `
      <g>
        <rect x="${f.x - 13}" y="${f.y - 13}" width="26" height="26" rx="6" fill="var(--primary)" stroke="var(--surface)" stroke-width="2"/>
        <path d="M${f.x} ${f.y - 6} V${f.y + 6} M${f.x - 6} ${f.y} H${f.x + 6}" stroke="var(--on-primary)" stroke-width="2.2" stroke-linecap="round"/>
        ${badge}
        <text x="${f.x}" y="${f.y + 22}" font-size="10" font-weight="800" fill="var(--text)" text-anchor="middle">${f.name}</text>
      </g>
    `;
  }).join('');

  // Villages
  let vilSvg = cachedVillages.map(v => {
    const pos = vilLocations[v.village_id];
    if (!pos) return '';
    const isSelected = v.village_id === selectedVillageId;
    const r = Math.max(14, Math.min(22, v.population / 100));

    let ringColor = 'var(--primary)';
    if (v.gap_score >= 60) ringColor = 'var(--urgent)';
    else if (v.gap_score >= 30) ringColor = 'var(--watch)';

    return `
      <g id="mapNode-${v.village_id}" style="cursor:pointer;" onclick="selectVillageOnMap('${v.village_id}')">
        ${isSelected ? `<circle cx="${pos.x}" cy="${pos.y}" r="${r + 5}" fill="none" stroke="var(--escalated)" stroke-width="2.5" stroke-dasharray="3,3"/>` : ''}
        <circle cx="${pos.x}" cy="${pos.y}" r="${r}" fill="var(--surface)" stroke="${ringColor}" stroke-width="2.5"/>
        <circle cx="${pos.x}" cy="${pos.y}" r="${r - 4}" fill="${ringColor}" opacity="0.15"/>
        <text x="${pos.x}" y="${pos.y + 4}" font-size="10" font-weight="800" fill="${ringColor}" text-anchor="middle">${v.gap_score}</text>
        <text x="${pos.x}" y="${pos.y + r + 13}" font-size="10" font-weight="700" fill="var(--text)" text-anchor="middle">${v.village_name}</text>
      </g>
    `;
  }).join('');

  mapContainer.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 490 320">
      ${linesSvg}
      ${facSvg}
      ${vilSvg}
    </svg>
  `;
}



// =========================================================================
// 9. WHAT WORKS
// =========================================================================
async function fetchWhatWorks() {
  const errorBox = document.getElementById('whatWorksErrorBox');
  const tbody = document.getElementById('whatWorksTbody');
  try {
    const res = await fetch('/api/what-works');
    if (!res.ok) throw new Error('Failed to fetch what-works');
    const data = await res.json();
    cachedOutcomes = data.what_works || [];

    if (errorBox) errorBox.style.display = 'none';

    tbody.innerHTML = cachedOutcomes.map(item => {
      const ratePct = Math.round(item.return_rate * 100);
      return `
        <tr style="border-bottom:1px solid var(--border);">
          <td style="padding:12px 16px; font-weight:700; color:var(--text);">${item.condition}</td>
          <td style="padding:12px 16px;">${item.reason}</td>
          <td style="padding:12px 16px;">
            <span class="pill pill-assigned" style="font-size:11px;">${item.action}</span>
          </td>
          <td style="padding:12px 16px; font-weight:600;">${item.cases_count} cases</td>
          <td style="padding:12px 16px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <div style="flex:1; height:8px; background:var(--border); border-radius:4px; overflow:hidden;">
                <div style="width:${ratePct}%; height:100%; background:var(--safe);"></div>
              </div>
              <span style="font-weight:700; font-size:12px; color:var(--safe); font-family:var(--font-numeric);">${ratePct}%</span>
            </div>
          </td>
          <td style="padding:12px 16px;">
            <span style="background:var(--soft); color:var(--text); padding:4px 8px; border-radius:6px; font-weight:700; font-size:11px; display:inline-flex; align-items:center; gap:4px;">
              ⏱ ${item.avg_days_to_return} days
            </span>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    if (errorBox) errorBox.style.display = 'flex';
  }
}

// =========================================================================
// 10. WORKER APP UI (PHONE VIEW: 390PX WITH TAP TARGETS >= 44PX)
// =========================================================================
function switchWorkerAppView(workerId) {
  renderWorkerCardsUI(workerId);
}

function renderWorkerCardsUI(customId) {
  const listCont = document.getElementById('workerCardsList');
  const titleEl = document.getElementById('workerQueueTitle');
  const countBadge = document.getElementById('workerTasksCountBadge');
  if (!listCont) return;

  const currentId = customId || (currentUser ? currentUser.id : 'W-101');
  const isSupervisor = currentId === 'SUP-201';
  const isDoctor = currentId === 'DOC-301';

  let tasks = [];
  if (isSupervisor) {
    titleEl.textContent = 'Supervisor Escalation Queue';
    tasks = cachedCases.filter(c => c.escalated_to === 'supervisor' && !['resolved', 'closed_lost'].includes(c.status));
  } else if (isDoctor) {
    titleEl.textContent = 'Doctor Clinical Review Queue';
    tasks = cachedCases.filter(c => c.escalated_to === 'doctor' && !['resolved', 'closed_lost'].includes(c.status));
  } else {
    titleEl.textContent = 'My Assigned Follow-ups';
    tasks = cachedCases.filter(c => c.owner_id === currentId && !['resolved', 'closed_lost'].includes(c.status));
  }

  countBadge.textContent = `${tasks.length} active`;

  if (tasks.length === 0) {
    listCont.innerHTML = `
      <div style="text-align:center; padding:48px 16px; color:var(--muted);">
        <div style="font-size:36px; margin-bottom:8px;">🎉</div>
        <div style="font-weight:800; font-size:16px; color:var(--text);">All caught up!</div>
        <div style="font-size:12px; margin-top:4px;">No pending follow-ups in queue for ${currentId}.</div>
      </div>
    `;
    return;
  }

  listCont.innerHTML = tasks.map(t => {
    let escBadge = '';
    if (t.status === 'escalated') {
      escBadge = `<div class="pill pill-escalated" style="margin-bottom:10px;">↑ Escalated to ${t.escalated_to}</div>`;
    }

    let dueHtml = `<span style="font-weight:600;">Due: ${t.due_date}</span>`;
    if (t.is_past_due) {
      dueHtml = `<span style="color:var(--urgent); font-weight:700;">⚠ Past Due (${t.due_date})</span>`;
    }

    return `
      <div class="card" style="padding:16px; margin-bottom:12px;">
        ${escBadge}
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="font-size:15px; font-weight:800; color:var(--text);">${t.patient_name}</div>
            <div style="font-size:12px; color:var(--muted);">${t.condition} · ${t.village_name}</div>
          </div>
          <div>${dueHtml}</div>
        </div>

        <div style="margin-top:12px;">
          <div style="font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:6px;">
            Tap Patient-Reported Reason:
          </div>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <button class="btn btn-secondary worker-tap-target" style="padding:8px 12px; font-size:12px; ${t.reason === 'feels_fine' ? 'background:var(--primary); color:var(--on-primary);' : ''}" onclick="workerTapReason('${t.id}', 'feels_fine')">Feels Fine</button>
            <button class="btn btn-secondary worker-tap-target" style="padding:8px 12px; font-size:12px; ${t.reason === 'no_stock' ? 'background:var(--primary); color:var(--on-primary);' : ''}" onclick="workerTapReason('${t.id}', 'no_stock')">No Stock</button>
            <button class="btn btn-secondary worker-tap-target" style="padding:8px 12px; font-size:12px; ${t.reason === 'cant_travel' ? 'background:var(--primary); color:var(--on-primary);' : ''}" onclick="workerTapReason('${t.id}', 'cant_travel')">Can't Travel</button>
            <button class="btn btn-secondary worker-tap-target" style="padding:8px 12px; font-size:12px; ${t.reason === 'lost_wages' ? 'background:var(--primary); color:var(--on-primary);' : ''}" onclick="workerTapReason('${t.id}', 'lost_wages')">Lost Wages</button>
            <button class="btn btn-secondary worker-tap-target" style="padding:8px 12px; font-size:12px; border-color:var(--urgent); ${t.reason === 'side_effects' ? 'background:var(--urgent); color:var(--on-primary);' : 'color:var(--urgent);'}" onclick="workerTapReason('${t.id}', 'side_effects')">⚡ Side Effects</button>
          </div>
        </div>

        <div style="display:flex; gap:8px; margin-top:14px;">
          <button class="btn btn-secondary worker-tap-target" style="flex:1;" onclick="workerUpdateStatus('${t.id}', 'in_progress')">In Progress</button>
          <button class="btn btn-primary worker-tap-target" style="flex:1;" onclick="workerUpdateStatus('${t.id}', 'resolved')">Mark Resolved</button>
        </div>
      </div>
    `;
  }).join('');
}

async function workerTapReason(caseId, reason) {
  try {
    const res = await fetch(`/api/cases/${caseId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to update reason', '⚠');
      return;
    }
    if (reason === 'side_effects') {
      showToast('Urgent side effects reported! Escalated straight to Doctor', '⚡');
    } else {
      showToast(`Recorded: ${reason.replace(/_/g, ' ')}`);
    }
    await Promise.all([fetchCases(), fetchScorecard()]);
    renderWorkerCardsUI();
  } catch (err) {
    showToast('Failed to record reason', '⚠');
  }
}

async function workerUpdateStatus(caseId, status) {
  try {
    const res = await fetch(`/api/cases/${caseId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: status })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Permission denied', '⚠');
      return;
    }
    showToast(`Task ${caseId} updated to ${status}`);
    await Promise.all([fetchCases(), fetchScorecard()]);
    renderWorkerCardsUI();
  } catch (err) {
    showToast('Failed to update task', '⚠');
  }
}

// =========================================================================
// 11. GUIDED DEMO STEPPER
// =========================================================================
const demoSteps = [
  {
    title: '1. Review Flagged Patients',
    desc: 'The Scorecard flags patients at risk across 6 villages in the district.',
    highlight: 'secScorecard'
  },
  {
    title: '2. Proactive Assignment',
    desc: 'Coordinator assigns an intervention to a care worker with a 2-day due date.',
    highlight: 'secCaseQueue'
  },
  {
    title: '3. Field Reason Capture',
    desc: 'Care worker visits the household and taps the root cause (e.g. Side Effects or No Stock).',
    highlight: 'workerAppView'
  },
  {
    title: '4. Demo Clock Advance',
    desc: 'Click "Advance 1 Day" in top bar. Overdue tasks automatically escalate.',
    highlight: 'btnAdvanceClock'
  },
  {
    title: '5. Escalation & Evidence',
    desc: 'Case queue shows purple escalation badges; What Works records outcome evidence.',
    highlight: 'tileEscalated'
  }
];

function toggleGuidedDemo() {
  const card = document.getElementById('guidedDemoCard');
  if (!card) return;
  const isHidden = card.style.display === 'none';
  if (isHidden) {
    card.style.display = 'block';
    guidedDemoStep = 0;
    renderDemoStep();
  } else {
    card.style.display = 'none';
    clearHighlights();
  }
}

function navigateDemoStep(direction) {
  guidedDemoStep += direction;
  if (guidedDemoStep < 0) guidedDemoStep = 0;
  if (guidedDemoStep >= demoSteps.length) {
    toggleGuidedDemo();
    return;
  }
  renderDemoStep();
}

function renderDemoStep() {
  clearHighlights();
  const step = demoSteps[guidedDemoStep];
  document.getElementById('demoStepBadge').textContent = `Step ${guidedDemoStep + 1} of ${demoSteps.length}`;
  document.getElementById('demoStepTitle').textContent = step.title;
  document.getElementById('demoStepDesc').textContent = step.desc;

  const prevBtn = document.getElementById('demoStepPrev');
  const nextBtn = document.getElementById('demoStepNext');
  prevBtn.style.visibility = guidedDemoStep === 0 ? 'hidden' : 'visible';
  nextBtn.textContent = guidedDemoStep === demoSteps.length - 1 ? 'Finish Demo' : 'Next Step →';

  if (step.highlight) {
    const el = document.getElementById(step.highlight);
    if (el) {
      el.classList.add('demo-highlight');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function clearHighlights() {
  document.querySelectorAll('.demo-highlight').forEach(el => el.classList.remove('demo-highlight'));
}

function scrollToSection(sectionId) {
  const sec = document.getElementById(sectionId);
  if (sec) {
    sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.querySelectorAll('.section-nav-link').forEach(link => link.classList.remove('active'));
    const clickedLink = document.querySelector(`[onclick="scrollToSection('${sectionId}')"]`);
    if (clickedLink) clickedLink.classList.add('active');
  }
}

function showToast(msg, icon = '✔') {
  const b = document.getElementById('appToast');
  if (!b) return;
  document.getElementById('toastMsg').textContent = msg;
  document.getElementById('toastIcon').textContent = icon;
  b.classList.add('show');
  setTimeout(() => b.classList.remove('show'), 2800);
}

function initManagerDashboard() {
  refreshAllData();
}

function initWorkerApp() {
  const switcher = document.getElementById('workerAppRoleSwitcher');
  if (switcher && currentUser) {
    switcher.value = currentUser.id;
  }
  refreshAllData();
}
