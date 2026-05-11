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

let ws = null;
let audioStream = null;
let audioContext = null;
let processor = null;
let consultationId = null;
let sessionId = null;

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

function cleanupAudio() {
  try { if (processor) processor.disconnect(); } catch {}
  processor = null;
  try { if (audioStream) audioStream.getTracks().forEach(t => t.stop()); } catch {}
  audioStream = null;
  try { if (audioContext && audioContext.state !== 'closed') audioContext.close(); } catch {}
  audioContext = null;
}

if (startBtn) {
  startBtn.onclick = async function () {
    cleanupAudio();
    if (ws) { try { ws.close(); } catch {} ws = null; }

    startBtn.disabled = true;
    stopBtn.disabled = false;
    transcriptionError.textContent = '';
    transcriptionSaved.textContent = '';
    partialText.textContent = '';
    chunksList.innerHTML = '';
    if (transcriptArea) transcriptArea.value = '';
    setStatus('ready', 'Connecting…');

    try {
      // 1. Create a transcription session.
      if (!sessionId) {
        const sResp = await fetch('/transcriptions/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ consultation_id: parseInt(consultationId) }),
        });
        const raw = await sResp.text();
        if (!sResp.ok) throw new Error(`Start session failed (${sResp.status}): ${raw.substring(0, 180)}`);
        const data = JSON.parse(raw);
        if (!data.session_id) throw new Error('Missing session_id');
        sessionId = data.session_id;
      }

      // 2. Open WebSocket.
      const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${wsProto}//${window.location.host}/transcriptions/ws/${sessionId}`);
      ws.binaryType = 'arraybuffer';

      ws.onerror = () => { transcriptionError.textContent = 'WebSocket error'; };

      ws.onmessage = (event) => {
        if (typeof event.data !== 'string') return;
        const trimmed = event.data.trim();
        if (!trimmed.startsWith('{')) return;
        let msg;
        try { msg = JSON.parse(trimmed); } catch { return; }

        // Backend may send either { partial_text } / { chunk_id, text } or
        // a Gabriele-style { type: 'partial' | 'final' | 'final_full', segment }.
        if (msg.partial_text !== undefined) {
          partialText.textContent = msg.partial_text;
          if (transcriptArea) transcriptArea.value = msg.partial_text;
        } else if (msg.chunk_id !== undefined) {
          const li = document.createElement('li');
          li.textContent = `[${msg.timestamp}s] ${msg.text}`;
          chunksList.appendChild(li);
          if (transcriptArea && msg.text) {
            transcriptArea.value += (transcriptArea.value ? '\n' : '') + msg.text;
          }
        } else if (msg.type === 'partial' && msg.segment) {
          if (transcriptArea) transcriptArea.value = msg.segment.text;
        } else if (msg.type === 'final' && msg.segment && msg.segment.text.trim()) {
          if (transcriptArea) transcriptArea.value += (transcriptArea.value ? '\n' : '') + msg.segment.text;
        } else if (msg.type === 'final_full') {
          if (transcriptArea && msg.full_text) transcriptArea.value = msg.full_text;
          saveBtn.disabled = false;
        } else if (msg.error) {
          transcriptionError.textContent = msg.error;
        }
      };

      // 3. Wait for socket open, then start mic capture (PCM16 @ 16kHz).
      await new Promise((resolve, reject) => {
        ws.onopen = resolve;
        setTimeout(() => reject(new Error('WebSocket open timeout')), 5000);
      });
      setStatus('recording', 'Recording');

      audioStream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });

      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContext.state === 'suspended') await audioContext.resume();

      const source = audioContext.createMediaStreamSource(audioStream);
      const gainNode = audioContext.createGain();
      gainNode.gain.value = 4.0;
      processor = audioContext.createScriptProcessor(4096, 1, 1);

      source.connect(gainNode);
      gainNode.connect(processor);
      processor.connect(audioContext.destination);

      const resampleRatio = 16000 / audioContext.sampleRate;
      processor.onaudioprocess = (e) => {
        const audioData = e.inputBuffer.getChannelData(0);
        const targetLength = Math.floor(audioData.length * resampleRatio);
        const resampled = new Float32Array(targetLength);
        for (let i = 0; i < targetLength; i++) {
          const sourceIndex = i / resampleRatio;
          const left = Math.floor(sourceIndex);
          const right = left + 1;
          const frac = sourceIndex - left;
          resampled[i] = right < audioData.length
            ? audioData[left] * (1 - frac) + audioData[right] * frac
            : (audioData[left] || 0);
        }
        const int16 = new Int16Array(resampled.length);
        for (let i = 0; i < resampled.length; i++) {
          int16[i] = Math.max(-1, Math.min(1, resampled[i])) * 0x7FFF;
        }
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(int16.buffer);
        }
      };
    } catch (err) {
      console.error('[Audio]', err);
      transcriptionError.textContent = `Microphone error: ${err.name || ''} ${err.message || err}`;
      startBtn.disabled = false;
      stopBtn.disabled = true;
      setStatus('ready', 'Ready');
    }
  };
}

if (stopBtn) {
  stopBtn.onclick = function () {
    stopBtn.disabled = true;
    startBtn.disabled = false;
    saveBtn.disabled = false;
    cleanupAudio();
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send('FINALIZE'); } catch {}
      }
    }, 300);
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
