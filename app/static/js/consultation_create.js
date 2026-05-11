// consultation_create.js
// Patient lookup + consultation creation + live transcription UI.

// ── Patient lookup (two fields: name ↔ ID) ───────────────────────────
const nameInput = document.getElementById('patient-name');
const idInput = document.getElementById('patient-id-input');
const idField = document.getElementById('patient-id-field');
const suggestionsList = document.getElementById('patient-suggestions');
const selectedHint = document.getElementById('patient-selected');
const patientError = document.getElementById('patient-error');
let debounceTimer = null;

function clearPatientState() {
  idField.value = '';
  selectedHint.textContent = '';
  selectedHint.style.display = 'none';
  patientError.textContent = '';
  patientError.style.display = 'none';
  idInput.classList.remove('nc-group__input--err', 'nc-group__input--ok');
  nameInput.classList.remove('nc-group__input--err', 'nc-group__input--ok');
}

function showPatientError(msg) {
  patientError.textContent = msg;
  patientError.style.display = '';
  selectedHint.style.display = 'none';
  idInput.classList.add('nc-group__input--err');
  nameInput.classList.add('nc-group__input--err');
  idInput.classList.remove('nc-group__input--ok');
  nameInput.classList.remove('nc-group__input--ok');
}

function showPatientSuccess(msg) {
  selectedHint.textContent = msg;
  selectedHint.style.display = '';
  patientError.style.display = 'none';
  idInput.classList.add('nc-group__input--ok');
  nameInput.classList.add('nc-group__input--ok');
  idInput.classList.remove('nc-group__input--err');
  nameInput.classList.remove('nc-group__input--err');
}

if (nameInput) {
  nameInput.addEventListener('input', function () {
    clearPatientState();
    idInput.value = '';
    clearTimeout(debounceTimer);
    const q = this.value.trim();
    if (q.length === 0) {
      suggestionsList.innerHTML = '';
      suggestionsList.style.display = 'none';
      return;
    }
    debounceTimer = setTimeout(async () => {
      try {
        const resp = await fetch(`/patients/search?q=${encodeURIComponent(q)}`);
        if (!resp.ok) return;
        const patients = await resp.json();
        suggestionsList.innerHTML = '';
        if (patients.length === 0) {
          const li = document.createElement('li');
          li.className = 'ac-empty';
          li.textContent = 'No patients found — check the spelling';
          suggestionsList.appendChild(li);
          showPatientError('No matching patient. Check the name.');
        } else {
          if (patients.length === 1) {
            const p = patients[0];
            idField.value = p.id;
            idInput.value = p.id;
            showPatientSuccess(`\u2713 ${p.first_name} ${p.last_name} (ID ${p.id})`);
          }
          patients.forEach(p => {
            const li = document.createElement('li');
            li.className = 'ac-item';
            li.innerHTML = `<strong>${p.first_name} ${p.last_name}</strong> <span class="ac-meta">ID ${p.id} \u00b7 ${p.email}</span>`;
            li.addEventListener('click', () => {
              idField.value = p.id;
              nameInput.value = `${p.first_name} ${p.last_name}`;
              idInput.value = p.id;
              showPatientSuccess(`\u2713 ${p.first_name} ${p.last_name} (ID ${p.id})`);
              suggestionsList.innerHTML = '';
              suggestionsList.style.display = 'none';
            });
            suggestionsList.appendChild(li);
          });
        }
        suggestionsList.style.display = '';
      } catch (e) { /* ignore */ }
    }, 250);
  });

  document.addEventListener('click', function (e) {
    if (!nameInput.contains(e.target) && !suggestionsList.contains(e.target)) {
      suggestionsList.style.display = 'none';
    }
  });
}

if (idInput) {
  idInput.addEventListener('input', function () {
    clearPatientState();
    nameInput.value = '';
    suggestionsList.style.display = 'none';
    clearTimeout(debounceTimer);
    const q = this.value.trim();
    if (q.length === 0) return;
    if (!/^\d+$/.test(q)) {
      showPatientError('ID must be a number.');
      return;
    }
    debounceTimer = setTimeout(async () => {
      try {
        const resp = await fetch(`/patients/search?q=${encodeURIComponent(q)}`);
        if (!resp.ok) return;
        const patients = await resp.json();
        const exact = patients.find(p => String(p.id) === q);
        if (exact) {
          idField.value = exact.id;
          nameInput.value = `${exact.first_name} ${exact.last_name}`;
          showPatientSuccess(`\u2713 ${exact.first_name} ${exact.last_name} (ID ${exact.id})`);
        } else {
          showPatientError(`No patient found with ID ${q}.`);
        }
      } catch (e) { /* ignore */ }
    }, 300);
  });
}

// ── Consultation creation + transcription ─────────────────────────────

// Web Speech API — Chrome/Edge only. Falls back gracefully.
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let isRecording = false;
let finalTranscript = '';
let consultationId = null;
let sessionId = null;

console.log('[MedFlow] consultation_create.js loaded, SpeechRecognition available:', !!SpeechRecognition);

const form = document.getElementById('create-consultation-form');
const successDiv = document.getElementById('consultation-success');
const errorDiv = document.getElementById('consultation-error');
const transcriptionUI = document.getElementById('transcription-ui');
const startBtn = document.getElementById('start-transcription');
const stopBtn = document.getElementById('stop-transcription');
const saveBtn = document.getElementById('save-transcription');
const partialText = document.getElementById('partial-text');
const chunksList = document.getElementById('transcription-chunks');
const transcriptionError = document.getElementById('transcription-error');
const transcriptionSaved = document.getElementById('transcription-saved');
const transcriptArea = document.getElementById('transcript-display');
const statusEl = document.getElementById('trx-status');

// Make transcript editable so doctors can correct in-place before save.
if (transcriptArea) transcriptArea.removeAttribute('readonly');

function setStatus(state, text) {
  if (!statusEl) return;
  statusEl.classList.remove('trx-status--recording', 'trx-status--saved');
  if (state === 'recording') statusEl.classList.add('trx-status--recording');
  if (state === 'saved')     statusEl.classList.add('trx-status--saved');
  const txt = statusEl.querySelector('.trx-status__text');
  if (txt) txt.textContent = text;
}

if (form) {
  form.onsubmit = async function (e) {
    e.preventDefault();
    successDiv.textContent = '';
    successDiv.style.display = 'none';
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    transcriptionUI.style.display = 'none';
    if (!idField.value) {
      showPatientError('Please select a patient or enter a valid ID.');
      nameInput.focus();
      return;
    }
    const formData = new FormData(form);
    const payload = {
      patient_id: formData.get('patient_id'),
      chief_complaint: formData.get('chief_complaint'),
    };
    try {
      const resp = await fetch('/consultations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(payload),
        redirect: 'follow',
      });
      if (!resp.ok) throw new Error('Failed to create consultation');
      const match = resp.url.match(/consultations\/(\d+)/);
      if (!match) throw new Error('Could not determine consultation ID');
      consultationId = match[1];
      sessionId = null;
      successDiv.textContent = 'Consultation created. Click Start Recording to begin.';
      successDiv.style.display = '';
      transcriptionUI.style.display = '';
      startBtn.disabled = false;
      saveBtn.disabled = false;
      setStatus('ready', 'Ready');
    } catch (err) {
      errorDiv.textContent = err.message || err;
      errorDiv.style.display = '';
    }
  };
}

function stopRecognition() {
  isRecording = false;
  if (recognition) {
    recognition.onend = null;   // prevent auto-restart
    recognition.onerror = null;
    try { recognition.stop(); } catch {}
    recognition = null;
  }
  finalTranscript = '';
}

// Show browser-support hint once UI is visible.
if (startBtn && !SpeechRecognition) {
  startBtn.title = 'Live transcription requires Chrome or Edge';
}

if (startBtn) {
  startBtn.onclick = function () {
    if (!SpeechRecognition) {
      transcriptionError.textContent =
        '\u26a0\ufe0f Your browser does not support live transcription. '
        + 'Please use Google Chrome or Microsoft Edge. '
        + 'You can also type the transcript manually below and click Save.';
      return;
    }

    stopRecognition();
    isRecording = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    transcriptionError.textContent = '';
    transcriptionSaved.textContent = '';
    if (transcriptArea) transcriptArea.value = '';
    finalTranscript = '';
    setStatus('recording', 'Starting\u2026');

    console.log('[MedFlow] Starting SpeechRecognition, consultationId=', consultationId);

    // Start recording immediately — no server call needed to hear audio.
    // Session is created lazily on Save.
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      console.log('[MedFlow] recognition.onstart fired');
      setStatus('recording', 'Recording');
    };

    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += text + ' ';
        } else {
          interim += text;
        }
      }
      if (transcriptArea) transcriptArea.value = finalTranscript + interim;
    };

    recognition.onerror = (event) => {
      console.error('[MedFlow] recognition.onerror', event.error);
      isRecording = false;
      if (event.error === 'not-allowed' || event.error === 'permission-denied') {
        transcriptionError.textContent =
          '\u26a0\ufe0f Microphone access denied. '
          + 'Click the camera/mic icon in your browser address bar and allow access, then try again.';
      } else if (event.error === 'network') {
        transcriptionError.textContent =
          '\u26a0\ufe0f Speech recognition requires an internet connection to Google\'s speech servers. '
          + 'You can type the transcript manually below instead.';
      } else if (event.error !== 'aborted' && event.error !== 'no-speech') {
        transcriptionError.textContent = `\u26a0\ufe0f Recording error: ${event.error}`;
      }
      startBtn.disabled = false;
      stopBtn.disabled = true;
      setStatus('ready', 'Ready');
    };

    // Auto-restart on natural silence; stop if user pressed Stop.
    recognition.onend = () => {
      console.log('[MedFlow] recognition.onend, isRecording=', isRecording);
      if (isRecording) {
        try { recognition.start(); } catch (e) { console.warn('[MedFlow] restart failed', e); }
      }
    };

    try {
      recognition.start();
      console.log('[MedFlow] recognition.start() called');
    } catch (err) {
      console.error('[MedFlow] recognition.start() threw', err);
      transcriptionError.textContent = `Could not start recording: ${err.message || err}`;
      startBtn.disabled = false;
      stopBtn.disabled = true;
      isRecording = false;
      setStatus('ready', 'Ready');
    }
  };
}

if (stopBtn) {
  stopBtn.onclick = function () {
    console.log('[MedFlow] Stop clicked, transcript so far:', transcriptArea ? transcriptArea.value.substring(0, 80) : '(none)');
    stopRecognition();
    stopBtn.disabled = true;
    startBtn.disabled = false;
    saveBtn.disabled = false;
    setStatus('saved', 'Stopped');
  };
}

if (saveBtn) {
  saveBtn.onclick = async function () {
    saveBtn.disabled = true;
    transcriptionSaved.textContent = 'Saving transcription…';
    transcriptionError.textContent = '';

    // Make sure we have a session even if Start Recording was never pressed
    // (e.g. doctor typed the transcript directly into the textarea).
    try {
      if (!sessionId && consultationId) {
        const sResp = await fetch('/transcriptions/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ consultation_id: parseInt(consultationId) }),
        });
        if (sResp.ok) {
          const sData = await sResp.json();
          sessionId = sData.session_id;
        }
      }
      // If textarea has content but no streaming chunks were saved, persist
      // the typed text so the save flow has something to write.
      if (transcriptArea && transcriptArea.value.trim() && sessionId) {
        await fetch(`/transcriptions/session/${sessionId}/inject-demo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: transcriptArea.value }),
        });
      }
    } catch (e) {
      console.warn('[Save] inject fallback failed', e);
    }

    try {
      const resp = await fetch('/transcriptions/save-transcription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consultation_id: parseInt(consultationId),
          session_id: sessionId,
        }),
      });
      const responseText = await resp.text();
      if (!resp.ok) {
        transcriptionError.textContent = `Server error (${resp.status}): ${responseText.substring(0, 200)}`;
        saveBtn.disabled = false;
        return;
      }
      transcriptionSaved.textContent = 'Transcription saved! Opening review workflow…';
      const reviewId = consultationId;
      startBtn.disabled = true;
      stopBtn.disabled = true;
      setStatus('saved', 'Saved');
      setTimeout(() => { window.location.href = `/review/${reviewId}`; }, 800);
    } catch (err) {
      transcriptionError.textContent = err.message || err;
      saveBtn.disabled = false;
    }
  };
}
