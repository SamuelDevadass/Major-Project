const API_BASE = "http://localhost:8000";

// ── YEAR RANGES ─────────────────────────────────────────────────────────────
const YEAR_RANGES = [
  { label: '2022 – 2024', years: [2022, 2023, 2024] },
];

// ── STATE ───────────────────────────────────────────────────────────────────
let selectedCompanies = [];   // [{ ticker, name }]
let selectedYearRange = null;
let analysisComplete  = false;
let currentJobId      = null;
let pollInterval      = null;

// ── INIT DROPDOWNS ──────────────────────────────────────────────────────────
async function initDropdowns() {
  // ── COMPANIES (from API) ──────────────────────────────────────────────────
  const opts = document.getElementById('company-options');
  try {
    const res       = await fetch(`${API_BASE}/companies`);
    const companies = await res.json();

    companies.forEach(c => {
      const div       = document.createElement('div');
      div.className   = 'dropdown-option';
      div.dataset.ticker = c.ticker;
      div.dataset.name   = c.company_name.toLowerCase();
      div.innerHTML   = `<span>${c.company_name}</span><span class="opt-ticker">${c.sector || ''}</span>`;
      div.onclick     = () => toggleCompany(c.ticker, c.company_name, div);
      opts.appendChild(div);
    });
  } catch (err) {
    opts.innerHTML = `<div style="padding:12px;color:var(--red)">Failed to load companies — is the backend running?</div>`;
  }

  // ── YEAR RANGES ───────────────────────────────────────────────────────────
  const yopts = document.getElementById('year-options');
  YEAR_RANGES.forEach((r, i) => {
    const div       = document.createElement('div');
    div.className   = 'dropdown-option';
    div.dataset.idx = i;
    div.innerHTML   = `<span>${r.label}</span><span class="opt-ticker">${r.years.join(', ')}</span>`;
    div.onclick     = () => selectYearRange(i, div);
    yopts.appendChild(div);
  });
}

// ── DROPDOWN TOGGLE ─────────────────────────────────────────────────────────
function toggleDropdown(type) {
  const dd      = document.getElementById(`${type}-dropdown`);
  const trigger = document.getElementById(`${type}-trigger`);
  const isOpen  = dd.classList.contains('open');
  document.querySelectorAll('.multiselect-dropdown').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.multiselect-trigger').forEach(t => t.classList.remove('open'));
  if (!isOpen) {
    dd.classList.add('open');
    trigger.classList.add('open');
    if (type === 'company') document.getElementById('company-search').focus();
  }
}

document.addEventListener('click', e => {
  if (!e.target.closest('.multiselect-wrapper')) {
    document.querySelectorAll('.multiselect-dropdown').forEach(d => d.classList.remove('open'));
    document.querySelectorAll('.multiselect-trigger').forEach(t => t.classList.remove('open'));
  }
});

// ── COMPANY SELECTION ───────────────────────────────────────────────────────
function toggleCompany(ticker, name, el) {
  const idx = selectedCompanies.findIndex(c => c.ticker === ticker);
  if (idx > -1) {
    selectedCompanies.splice(idx, 1);
    el.classList.remove('selected');
  } else {
    if (selectedCompanies.length >= 5) return;
    selectedCompanies.push({ ticker, name });
    el.classList.add('selected');
  }
  document.querySelectorAll('#company-options .dropdown-option').forEach(opt => {
    if (!opt.classList.contains('selected')) {
      opt.classList.toggle('disabled', selectedCompanies.length >= 5);
    }
  });
  renderCompanyTags();
  updateSummary();
  updateRunButton();
}

function renderCompanyTags() {
  const container   = document.getElementById('company-tags');
  const placeholder = document.getElementById('company-placeholder');
  container.innerHTML = '';
  if (selectedCompanies.length === 0) {
    container.appendChild(placeholder);
    placeholder.style.display = '';
    return;
  }
  placeholder.style.display = 'none';
  selectedCompanies.forEach(c => {
    const tag       = document.createElement('div');
    tag.className   = 'tag';
    tag.innerHTML   = `${c.name} <span class="tag-remove" onclick="removeCompany('${c.ticker}', event)">×</span>`;
    container.appendChild(tag);
  });
}

function removeCompany(ticker, event) {
  event.stopPropagation();
  const el  = document.querySelector(`#company-options .dropdown-option[data-ticker="${ticker}"]`);
  const idx = selectedCompanies.findIndex(c => c.ticker === ticker);
  if (idx > -1) selectedCompanies.splice(idx, 1);
  if (el) el.classList.remove('selected');
  document.querySelectorAll('#company-options .dropdown-option').forEach(opt => {
    if (!opt.classList.contains('selected')) opt.classList.remove('disabled');
  });
  renderCompanyTags();
  updateSummary();
  updateRunButton();
}

// ── YEAR SELECTION ──────────────────────────────────────────────────────────
function selectYearRange(idx, el) {
  selectedYearRange = YEAR_RANGES[idx];
  document.querySelectorAll('#year-options .dropdown-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');

  const container   = document.getElementById('year-tags');
  const placeholder = document.getElementById('year-placeholder');
  container.innerHTML     = '';
  placeholder.style.display = 'none';
  const tag     = document.createElement('div');
  tag.className = 'tag';
  tag.innerHTML = `${selectedYearRange.label} <span class="tag-remove" onclick="clearYear(event)">×</span>`;
  container.appendChild(tag);

  document.getElementById('year-dropdown').classList.remove('open');
  document.getElementById('year-trigger').classList.remove('open');

  updateSummary();
  updateRunButton();
}

function clearYear(event) {
  event.stopPropagation();
  selectedYearRange = null;
  document.querySelectorAll('#year-options .dropdown-option').forEach(o => o.classList.remove('selected'));
  const container   = document.getElementById('year-tags');
  const placeholder = document.getElementById('year-placeholder');
  container.innerHTML = '';
  container.appendChild(placeholder);
  placeholder.style.display = '';
  updateSummary();
  updateRunButton();
}

// ── FILTER SEARCH ───────────────────────────────────────────────────────────
function filterOptions(type) {
  const q = document.getElementById(`${type}-search`).value.toLowerCase();
  document.querySelectorAll(`#${type}-options .dropdown-option`).forEach(opt => {
    const match = (opt.dataset.name   && opt.dataset.name.includes(q)) ||
                  (opt.dataset.ticker && opt.dataset.ticker.toLowerCase().includes(q));
    opt.style.display = match ? '' : 'none';
  });
}

// ── SUMMARY ─────────────────────────────────────────────────────────────────
function updateSummary() {
  const el = document.getElementById('selection-summary');
  if (selectedCompanies.length === 0 && !selectedYearRange) {
    el.innerHTML = `<span class="summary-prefix">awaiting selection —</span> <span style="color:var(--text-dim);font-size:0.75rem;font-family:var(--mono)">choose companies and year range to begin</span>`;
    return;
  }
  let html = `<span class="summary-prefix">Analyzing</span> `;
  html += selectedCompanies.length > 0
    ? selectedCompanies.map(c => `<span class="summary-item">${c.name}</span>`).join(' ')
    : `<span style="color:var(--text-dim)">no companies</span>`;
  html += ` <span class="summary-sep">|</span> `;
  html += selectedYearRange
    ? selectedYearRange.years.map(y => `<span class="summary-item">${y}</span>`).join(' ')
    : `<span style="color:var(--text-dim)">no range</span>`;
  el.innerHTML = html;
}

function updateRunButton() {
  document.getElementById('btn-run').disabled = !(selectedCompanies.length >= 1 && selectedYearRange);
}

// ── STEP UI HELPERS ──────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, badge: 'RUNNING',    doneBadge: 'DONE', detail: () => `Orchestrator initialized — session started` },
  { id: 2, badge: 'FETCHING',   doneBadge: 'DONE', detail: () => `Loading CRISIL ESG data for <span>${selectedCompanies.length}</span> companies` },
  { id: 3, badge: 'INDEXING',   doneBadge: 'DONE', detail: () => `Fetching live news + building FAISS index` },
  { id: 4, badge: 'COMPUTING',  doneBadge: 'DONE', detail: () => `LOWESS smoothing + adaptive forward validation` },
  { id: 5, badge: 'GENERATING', doneBadge: 'DONE', detail: () => `Groq LLaMA3-70B — <span>${selectedCompanies.length * 3 + 1}</span> calls` },
  { id: 6, badge: 'BUILDING',   doneBadge: 'DONE', detail: () => `Generating Excel workbooks + charts` },
];

function log(msg, type = 'info') {
  const terminal = document.getElementById('terminal-log');
  const now      = new Date();
  const time     = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
  const line     = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `<span class="log-time">${time}</span><span class="log-msg ${type}">${msg}</span>`;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function activateStep(stepNum, progress) {
  const el       = document.getElementById(`step-${stepNum}`);
  const badge    = document.getElementById(`step-${stepNum}-badge`);
  const detail   = document.getElementById(`step-${stepNum}-detail`);
  const stepData = STEPS[stepNum - 1];
  if (!el) return;
  el.classList.add('active');
  badge.textContent        = stepData.badge;
  badge.style.borderColor  = 'var(--amber)';
  badge.style.color        = 'var(--amber)';
  detail.innerHTML         = stepData.detail();
  document.getElementById('progress-fill').style.width = progress + '%';
}

function completeStep(stepNum) {
  const el       = document.getElementById(`step-${stepNum}`);
  const badge    = document.getElementById(`step-${stepNum}-badge`);
  const stepData = STEPS[stepNum - 1];
  if (!el) return;
  el.classList.remove('active');
  el.classList.add('done');
  badge.textContent       = stepData.doneBadge;
  badge.style.borderColor = 'var(--green-dim)';
  badge.style.color       = 'var(--green)';
  badge.style.background  = 'var(--green-glow)';
}

// ── ANALYSIS PIPELINE ────────────────────────────────────────────────────────
async function startAnalysis() {
  // Switch views
  document.getElementById('input-panel').style.display = 'none';
  const section = document.getElementById('analysis-section');
  section.style.display = 'block';
  document.getElementById('terminal-log').innerHTML = '';
  log('Analysis pipeline starting...', 'info');
  setTimeout(() => section.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);

  // ── POST /analyze ─────────────────────────────────────────────────────────
  let job_id;
  try {
    const res  = await fetch(`${API_BASE}/analyze`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        companies:  selectedCompanies.map(c => c.ticker),
        year_range: selectedYearRange.years,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      log(`[ERROR] ${JSON.stringify(err.detail)}`, 'error');
      showError('Failed to start analysis. Check backend logs.');
      return;
    }

    const data = await res.json();
    job_id     = data.job_id;
    currentJobId = job_id;
    log(`[MCP] Job started — ID: ${job_id}`, 'ok');
  } catch (err) {
    log(`[ERROR] Cannot reach backend: ${err.message}`, 'error');
    showError('Backend unreachable. Is uvicorn running on port 8000?');
    return;
  }

  // ── POLL /status/{job_id} every 2 seconds ─────────────────────────────────
  let lastStep = 0;

  pollInterval = setInterval(async () => {
    try {
      const res    = await fetch(`${API_BASE}/status/${job_id}`);
      const status = await res.json();

      // Update step UI when step advances
      if (status.step !== lastStep) {
        if (lastStep > 0) completeStep(lastStep);
        const progressMap = { 1: 10, 2: 25, 3: 45, 4: 62, 5: 80, 6: 93 };
        activateStep(status.step, progressMap[status.step] || 0);
        lastStep = status.step;
      }

      // Append log message
      if (status.log) log(status.log, 'info');

      // ── DONE ────────────────────────────────────────────────────────────
      if (status.status === 'done') {
        clearInterval(pollInterval);
        completeStep(lastStep);
        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('status-dot').className      = 'status-dot done';
        document.getElementById('status-text').textContent   = 'Analysis Complete';
        document.getElementById('status-text').style.color   = 'var(--green)';
        document.getElementById('btn-results').disabled      = false;
        analysisComplete = true;
        log('[DONE] Analysis complete — results ready', 'ok');

        // Save to sessionStorage for results page
        sessionStorage.setItem('job_id',        job_id);
        sessionStorage.setItem('esg_companies', JSON.stringify(selectedCompanies));
        sessionStorage.setItem('esg_years',     JSON.stringify(selectedYearRange));
      }

      // ── ERROR ────────────────────────────────────────────────────────────
      if (status.status === 'error') {
        clearInterval(pollInterval);
        log(`[ERROR] ${status.error_msg || 'Pipeline failed'}`, 'error');
        showError(status.error_msg || 'Pipeline failed. Check backend logs.');
      }

    } catch (err) {
      log(`[ERROR] Polling failed: ${err.message}`, 'error');
    }
  }, 2000);
}

function showError(msg) {
  document.getElementById('status-dot').className    = 'status-dot error';
  document.getElementById('status-text').textContent = 'Error';
  document.getElementById('status-text').style.color = 'var(--red)';
  log(`[ERROR] ${msg}`, 'error');
}

function goToResults() {
  window.location.href = 'results.html';
}

// ── BOOT ─────────────────────────────────────────────────────────────────────
initDropdowns();