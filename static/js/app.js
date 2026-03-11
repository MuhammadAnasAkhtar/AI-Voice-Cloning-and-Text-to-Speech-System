/* ══════════════════════════════════════════════════════════
   VOICE STUDIO — Frontend JavaScript
   ══════════════════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────
let langData = {};      // {language: [accents]}
let styles = [];
let profiles = [];

// ══════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
  await loadLanguages();
  await refreshProfiles();
  buildLibrary();
  setupDropzone();
  setupSliders();
  setupTextCounters();
});

// ── Load language data from API ──────────────────────────
async function loadLanguages() {
  try {
    const r = await fetch('/api/languages');
    const d = await r.json();
    langData = d.languages;
    styles = d.styles;

    const langKeys = Object.keys(langData);

    // Populate all language dropdowns
    populateSelect('clone-lang', langKeys);
    populateSelect('normal-lang', langKeys);

    // Populate styles
    populateSelect('clone-style', styles);
    populateSelect('normal-style', styles);

    // Set up accent linking
    updateAccents('clone');
    updateAccents('normal');

    // Listen for language changes
    document.getElementById('clone-lang').addEventListener('change', () => updateAccents('clone'));
    document.getElementById('normal-lang').addEventListener('change', () => updateAccents('normal'));
  } catch (e) {
    showToast('Failed to load language data: ' + e.message, 'error');
  }
}

function populateSelect(id, options) {
  const sel = document.getElementById(id);
  sel.innerHTML = '';
  options.forEach(opt => {
    const o = document.createElement('option');
    o.value = opt;
    o.textContent = opt;
    sel.appendChild(o);
  });
}

function updateAccents(prefix) {
  const lang = document.getElementById(prefix + '-lang').value;
  const accents = langData[lang] || [];
  populateSelect(prefix + '-accent', accents);
}

// ── Profiles ─────────────────────────────────────────────
async function refreshProfiles() {
  try {
    const r = await fetch('/api/profiles');
    const d = await r.json();
    profiles = d.profiles;

    // Update profile dropdown
    const sel = document.getElementById('clone-profile');
    sel.innerHTML = '';
    if (profiles.length === 0) {
      const o = document.createElement('option');
      o.value = '';
      o.textContent = '(none — upload in Custom Voice tab)';
      sel.appendChild(o);
    } else {
      profiles.forEach(p => {
        const o = document.createElement('option');
        o.value = p.name;
        o.textContent = p.name + ' (' + p.f0_median + 'Hz · ' + p.duration + 's)';
        sel.appendChild(o);
      });
    }

    // Update stat
    document.getElementById('stat-profiles').textContent = profiles.length;

    // Update profiles list in Custom Voice tab
    renderProfilesList();
  } catch (e) {
    console.warn('Profile refresh error:', e);
  }
}

function renderProfilesList() {
  const list = document.getElementById('profiles-list');
  if (profiles.length === 0) {
    list.innerHTML = '<div class="profiles-empty">No profiles yet. Upload your first voice sample above.</div>';
    return;
  }
  list.innerHTML = profiles.map(p => `
    <div class="profile-item">
      <div class="profile-avatar">👤</div>
      <div class="profile-info">
        <div class="profile-name">${escHtml(p.name)}</div>
        <div class="profile-meta">
          <span>🎵 ${p.f0_median}Hz</span>
          <span>⏱️ ${p.duration}s</span>
          <span>📅 ${escHtml(p.created)}</span>
        </div>
      </div>
      <div class="profile-actions">
        <button class="btn-profile-del" onclick="deleteProfile('${escHtml(p.name)}')">🗑️ Delete</button>
      </div>
    </div>
  `).join('');
}

async function deleteProfile(name) {
  if (!confirm('Delete profile "' + name + '"?')) return;
  try {
    const r = await fetch('/api/delete-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const d = await r.json();
    if (d.ok) {
      showToast('Profile "' + name + '" deleted', 'success');
      await refreshProfiles();
    } else {
      showToast(d.error || 'Delete failed', 'error');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════
// TAB NAVIGATION
// ══════════════════════════════════════════════════════════

function switchTab(tab) {
  // Update nav buttons
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  // Update panels
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === 'tab-' + tab);
  });
  // Close mobile sidebar
  document.getElementById('sidebar').classList.remove('open');
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ══════════════════════════════════════════════════════════
// TEXT EDITOR HELPERS
// ══════════════════════════════════════════════════════════

function setupTextCounters() {
  ['clone', 'normal'].forEach(prefix => {
    const textarea = document.getElementById(prefix + '-text');
    textarea.addEventListener('input', () => updateWordCount(prefix));
  });
}

function updateWordCount(prefix) {
  const text = document.getElementById(prefix + '-text').value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  const chars = document.getElementById(prefix + '-text').value.length;
  const est = (words / 150).toFixed(1);
  const maxW = 100000;
  const pct = Math.min(words / maxW * 100, 100);
  const color = words === 0 ? '#8b949e' : words > maxW ? '#f85149' : words > 80000 ? '#ffd700' : '#3fb950';

  document.getElementById(prefix + '-wc').textContent = 'Words: ' + words.toLocaleString();
  document.getElementById(prefix + '-wc').style.color = color;
  document.getElementById(prefix + '-cc').textContent = 'Chars: ' + chars.toLocaleString();
  document.getElementById(prefix + '-est').textContent = 'Est. ~' + est + ' min';
  const bar = document.getElementById(prefix + '-bar');
  bar.style.width = pct + '%';
  bar.style.background = color;
}

function clearText(prefix) {
  document.getElementById(prefix + '-text').value = '';
  updateWordCount(prefix);
}

async function pasteClipboard(prefix) {
  try {
    const text = await navigator.clipboard.readText();
    document.getElementById(prefix + '-text').value += text;
    updateWordCount(prefix);
    showToast('Text pasted from clipboard', 'success');
  } catch {
    showToast('Clipboard access denied. Please paste manually (Ctrl+V)', 'info');
  }
}

function insertSample(prefix) {
  const sample = `Welcome to the Advanced Voice Studio. This is a demonstration of high-quality text-to-speech with voice identity transfer technology.

This system can convert any written text into natural-sounding speech using your own voice characteristics. Whether you need to create audiobooks, podcasts, video narrations, or educational content, this tool delivers professional results.

The voice identity transfer feature analyses your uploaded voice sample and applies your unique vocal characteristics — pitch, tone, and rhythm — to the generated speech. This means the output sounds like you, speaking in any language or accent available.

You can process documents of up to one hundred thousand words. The system automatically splits your text into manageable chunks, processes each one, and seamlessly merges them into a single high-quality audio file.

Try it now: replace this sample text with your own script and click the Generate button below.`;

  document.getElementById(prefix + '-text').value = sample;
  updateWordCount(prefix);
  showToast('Sample text inserted', 'success');
}

// ══════════════════════════════════════════════════════════
// FINE-TUNE TOGGLE
// ══════════════════════════════════════════════════════════

function toggleFinetune(prefix) {
  const body = document.getElementById(prefix + '-ft-body');
  const arrow = document.getElementById(prefix + '-ft-arrow');
  body.classList.toggle('open');
  arrow.classList.toggle('open');
}

function setupSliders() {
  // Clone sliders
  setupSlider('clone-timbre', 'clone-timbre-val', 2);
  setupSlider('clone-tempo', 'clone-tempo-val', 2);
  setupSlider('clone-pitch', 'clone-pitch-val', 2);
  // Custom voice sliders
  setupSlider('custom-noise', 'custom-noise-val', 1);
  setupSlider('custom-reverb', 'custom-reverb-val', 2);
}

function setupSlider(sliderId, valId, decimals) {
  const slider = document.getElementById(sliderId);
  const val = document.getElementById(valId);
  if (slider && val) {
    slider.addEventListener('input', () => {
      val.textContent = parseFloat(slider.value).toFixed(decimals);
    });
  }
}

// ══════════════════════════════════════════════════════════
// VOICE CLONING GENERATION
// ══════════════════════════════════════════════════════════

async function generateClone() {
  const btn = document.getElementById('clone-gen-btn');
  const progress = document.getElementById('clone-progress');
  const progressText = document.getElementById('clone-progress-text');
  const result = document.getElementById('clone-result');

  const text = document.getElementById('clone-text').value.trim();
  if (!text) {
    showToast('Please enter text in the editor', 'error');
    return;
  }

  const profVal = document.getElementById('clone-profile').value;
  if (!profVal) {
    showToast('No voice profile found. Go to Custom Voice tab and upload one.', 'error');
    return;
  }

  btn.disabled = true;
  btn.querySelector('.btn-gen-text').textContent = 'Generating...';
  progress.style.display = 'flex';
  result.style.display = 'none';
  progressText.textContent = 'Sending to server...';

  const payload = {
    text: text,
    lang: document.getElementById('clone-lang').value,
    accent: document.getElementById('clone-accent').value,
    style: document.getElementById('clone-style').value,
    profile: profVal,
    timbre: parseFloat(document.getElementById('clone-timbre').value),
    tempo: parseFloat(document.getElementById('clone-tempo').value),
    pitch: parseFloat(document.getElementById('clone-pitch').value),
    mode: 'clone'
  };

  try {
    progressText.textContent = 'Generating audio — this may take 15-60 seconds...';
    const r = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await r.json();

    progress.style.display = 'none';

    if (d.ok) {
      showResult('clone', d);
      showToast('Voice generated successfully!', 'success');
    } else {
      showError('clone', d.error, d.traceback);
      showToast('Generation failed', 'error');
    }
  } catch (e) {
    progress.style.display = 'none';
    showError('clone', 'Request failed: ' + e.message);
    showToast('Connection error', 'error');
  }

  btn.disabled = false;
  btn.querySelector('.btn-gen-text').textContent = 'Generate Voice Output';
}

// ══════════════════════════════════════════════════════════
// NORMAL VOICE GENERATION
// ══════════════════════════════════════════════════════════

async function generateNormal() {
  const btn = document.getElementById('normal-gen-btn');
  const progress = document.getElementById('normal-progress');
  const progressText = document.getElementById('normal-progress-text');
  const result = document.getElementById('normal-result');

  const text = document.getElementById('normal-text').value.trim();
  if (!text) {
    showToast('Please enter text in the editor', 'error');
    return;
  }

  btn.disabled = true;
  btn.querySelector('.btn-gen-text').textContent = 'Generating...';
  progress.style.display = 'flex';
  result.style.display = 'none';
  progressText.textContent = 'Generating with built-in voice...';

  const payload = {
    text: text,
    lang: document.getElementById('normal-lang').value,
    accent: document.getElementById('normal-accent').value,
    style: document.getElementById('normal-style').value,
    profile: '',
    timbre: 0,
    tempo: 0,
    pitch: 1.0,
    mode: 'normal'
  };

  try {
    progressText.textContent = 'Generating audio — please wait...';
    const r = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await r.json();

    progress.style.display = 'none';

    if (d.ok) {
      showResult('normal', d);
      showToast('Voice generated successfully!', 'success');
    } else {
      showError('normal', d.error, d.traceback);
      showToast('Generation failed', 'error');
    }
  } catch (e) {
    progress.style.display = 'none';
    showError('normal', 'Request failed: ' + e.message);
    showToast('Connection error', 'error');
  }

  btn.disabled = false;
  btn.querySelector('.btn-gen-text').textContent = 'Generate Voice';
}

// ══════════════════════════════════════════════════════════
// RESULTS DISPLAY
// ══════════════════════════════════════════════════════════

function showResult(prefix, data) {
  const el = document.getElementById(prefix + '-result');
  el.className = 'result-card';
  el.style.display = 'block';
  el.innerHTML = `
    <div class="result-header">
      <span style="font-size:24px">✅</span>
      <h3>Generation Complete!</h3>
    </div>
    <div class="result-meta">
      <div class="meta-item">👤 <strong>${escHtml(data.profile)}</strong></div>
      <div class="meta-item">🌍 <strong>${escHtml(data.lang)}</strong></div>
      <div class="meta-item">🗣️ <strong>${escHtml(data.accent)}</strong></div>
      <div class="meta-item">🎭 <strong>${escHtml(data.style)}</strong></div>
      <div class="meta-item">📝 <strong>${data.words.toLocaleString()} words</strong></div>
      <div class="meta-item">🧩 <strong>${data.chunks} chunks</strong></div>
      <div class="meta-item">🕐 <strong>${data.duration}</strong></div>
      <div class="meta-item">📦 <strong>${data.size_kb} KB</strong></div>
    </div>
    <p style="color: var(--accent-green); font-size: 13px; margin-bottom: 14px;">
      ${escHtml(data.identity)}
    </p>
    <div class="result-audio">
      <audio controls src="${data.url}" style="width:100%; border-radius:8px"></audio>
    </div>
    <div class="result-download">
      <a href="${data.url}" download="${escHtml(data.filename)}" class="btn-download">
        📥 Download Audio File
      </a>
    </div>`;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showError(prefix, error, tb) {
  const el = document.getElementById(prefix + '-result');
  el.className = 'result-card result-error';
  el.style.display = 'block';
  el.innerHTML = `
    <div class="result-header">
      <span style="font-size:24px">❌</span>
      <h3>Generation Failed</h3>
    </div>
    <p style="color: var(--accent-red); font-size: 14px;">${escHtml(error)}</p>
    ${tb ? '<pre>' + escHtml(tb) + '</pre>' : ''}`;
}

// ══════════════════════════════════════════════════════════
// VOICE UPLOAD (Custom Voice Tab)
// ══════════════════════════════════════════════════════════

function setupDropzone() {
  const zone = document.getElementById('custom-dropzone');
  const input = document.getElementById('custom-file');

  zone.addEventListener('click', () => input.click());

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => {
    zone.classList.remove('drag-over');
  });
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      input.files = e.dataTransfer.files;
      showSelectedFile(e.dataTransfer.files[0]);
    }
  });

  input.addEventListener('change', () => {
    if (input.files.length > 0) {
      showSelectedFile(input.files[0]);
    }
  });
}

function showSelectedFile(file) {
  document.querySelector('.dropzone-content').style.display = 'none';
  const info = document.getElementById('custom-file-info');
  info.style.display = 'flex';
  document.getElementById('custom-file-name').textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
}

function removeFile() {
  document.getElementById('custom-file').value = '';
  document.querySelector('.dropzone-content').style.display = 'block';
  document.getElementById('custom-file-info').style.display = 'none';
}

async function uploadVoice() {
  const fileInput = document.getElementById('custom-file');
  const name = document.getElementById('custom-name').value.trim();
  const btn = document.getElementById('custom-upload-btn');
  const status = document.getElementById('custom-status');

  if (!name) {
    showToast('Please enter a profile name', 'error');
    return;
  }
  if (!fileInput.files || fileInput.files.length === 0) {
    showToast('Please select an audio file', 'error');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span>⏳</span> Analyzing voice...';
  status.innerHTML = '<div class="status-msg status-loading">🔄 Uploading and analyzing voice... This may take 10-30 seconds.</div>';

  const formData = new FormData();
  formData.append('audio', fileInput.files[0]);
  formData.append('name', name);
  formData.append('noise', document.getElementById('custom-noise').value);
  formData.append('reverb', document.getElementById('custom-reverb').value);

  try {
    const r = await fetch('/api/upload-voice', {
      method: 'POST',
      body: formData
    });
    const d = await r.json();

    if (d.ok) {
      status.innerHTML = `
        <div class="status-msg status-success">
          ✅ <strong>${escHtml(d.message)}</strong><br>
          Pitch: ${d.profile.f0_median}Hz · Duration: ${d.profile.duration}s
        </div>`;
      showToast('Voice profile saved!', 'success');
      removeFile();
      await refreshProfiles();
    } else {
      status.innerHTML = `<div class="status-msg status-error">❌ ${escHtml(d.error)}</div>`;
      showToast('Upload failed', 'error');
    }
  } catch (e) {
    status.innerHTML = `<div class="status-msg status-error">❌ Connection error: ${escHtml(e.message)}</div>`;
    showToast('Upload error', 'error');
  }

  btn.disabled = false;
  btn.innerHTML = '<span>💾</span> Analyze & Save Voice Profile';
}

// ══════════════════════════════════════════════════════════
// VOICE LIBRARY
// ══════════════════════════════════════════════════════════

function buildLibrary() {
  const grid = document.getElementById('library-grid');
  const search = document.getElementById('library-search');

  function render(filter) {
    grid.innerHTML = '';
    const fl = (filter || '').toLowerCase();

    for (const [lang, accents] of Object.entries(langData)) {
      const filtered = accents.filter(a => {
        if (!fl) return true;
        return lang.toLowerCase().includes(fl) || a.toLowerCase().includes(fl);
      });
      if (filtered.length === 0) continue;

      const section = document.createElement('div');
      section.className = 'lib-lang-section';
      section.innerHTML = `
        <div class="lib-lang-header">
          <h4>${escHtml(lang)}</h4>
          <span class="lib-lang-count">${filtered.length} voices</span>
        </div>
        <div class="lib-voices">
          ${filtered.map(a => `
            <div class="lib-voice-item">
              <span style="font-size:16px">🎤</span>
              <span class="lib-voice-name">${escHtml(a)}</span>
              <span class="lib-voice-badge ${a.includes('Identity') ? 'badge-identity' : 'badge-standard'}">
                Voice
              </span>
            </div>
          `).join('')}
        </div>`;
      grid.appendChild(section);
    }

    if (grid.children.length === 0) {
      grid.innerHTML = '<div class="profiles-empty">No voices match your search.</div>';
    }
  }

  render('');
  search.addEventListener('input', () => render(search.value));
}

// ══════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════

function escHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function showToast(message, type) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + (type || 'info');
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = '<span>' + (icons[type] || 'ℹ️') + '</span> ' + escHtml(message);
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity .3s';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
