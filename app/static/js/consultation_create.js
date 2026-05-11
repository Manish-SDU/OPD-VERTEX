// consultation_create.js
// Handles AJAX consultation creation and transcription UI logic for the create consultation page

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

// ── Name field: type name → dropdown → auto-fill ID ──────────────────
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

// ── ID field: type ID → auto-fill name ───────────────────────────────
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
let mediaRecorder = null;
let audioStream = null;
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

if (form) {
  form.onsubmit = async function(e) {
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
      chief_complaint: formData.get('chief_complaint')
    };
    try {
      const resp = await fetch('/consultations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(payload),
        redirect: 'follow'
      });
      if (!resp.ok) throw new Error('Failed to create consultation');
      const url = resp.url;
      const match = url.match(/consultations\/(\d+)/);
      if (!match) throw new Error('Could not determine consultation ID');
      consultationId = match[1];
      sessionId = null;
      successDiv.textContent = 'Consultation created! Starting transcription...';
      successDiv.style.display = '';
      transcriptionUI.style.display = '';
      startBtn.disabled = false;
      setTimeout(() => startBtn.click(), 500);
    } catch (err) {
      errorDiv.textContent = err.message || err;
      errorDiv.style.display = '';
    }
  };
}

if (startBtn) {
  startBtn.onclick = async function() {
    // Clean up any previous recording
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    if (audioStream) {
      audioStream.getTracks().forEach(t => t.stop());
    }
    if (ws) {
      try { ws.close(); } catch {}
      ws = null;
    }

    startBtn.disabled = true;
    stopBtn.disabled = false;
    transcriptionError.textContent = '';
    partialText.textContent = '';
    chunksList.innerHTML = '';
    transcriptionSaved.textContent = '';

    try {
      // Create a new transcription session for each recording
      const resp = await fetch('/transcriptions/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consultation_id: parseInt(consultationId) })
      });
      const raw = await resp.text();
      if (!resp.ok) throw new Error(`Start session failed (${resp.status}): ${raw.substring(0, 180)}`);
      const data = JSON.parse(raw);
      if (!data.session_id) throw new Error('Start session response is missing session_id');
      sessionId = data.session_id;
      console.log('[Session] Created:', sessionId);

      // Open WebSocket to the app proxy
      const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${wsProto}//${window.location.host}/transcriptions/ws/${sessionId}`);

      ws.onerror = () => { transcriptionError.textContent = 'WebSocket error'; };
      ws.onmessage = (evt) => {
        if (typeof evt.data !== 'string') return;
        let msg;
        try { msg = JSON.parse(evt.data); } catch { return; }

        if (msg.type === 'partial' && msg.segment) {
          partialText.textContent = msg.segment.text;
        } else if (msg.type === 'final' && msg.segment && msg.segment.text.trim()) {
          partialText.textContent = '';
          const li = document.createElement('li');
          li.textContent = `[${msg.segment.start.toFixed(1)}s] ${msg.segment.text}`;
          chunksList.appendChild(li);
        } else if (msg.type === 'final_full') {
          partialText.textContent = '';
          if (msg.full_text) {
            chunksList.innerHTML = '';
            const li = document.createElement('li');
            li.textContent = msg.full_text;
            chunksList.appendChild(li);
          }
          saveBtn.disabled = false;
        } else if (msg.type === 'error') {
          transcriptionError.textContent = msg.message || 'Transcription error';
        }
      };

      // Start mic and MediaRecorder only after WS is open — same approach as TC
      ws.onopen = async () => {
        console.log('[WS] Connected');
        try {
          audioStream = await navigator.mediaDevices.getUserMedia({
            audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false },
          });
          // WebM/Opus — ffmpeg in the whisper pipeline can decode this container
          mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm;codecs=opus' });
          console.log('[Audio] MediaRecorder mimeType:', mediaRecorder.mimeType);

          mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
              // Convert Blob → ArrayBuffer before sending — required for binary WS frames
              e.data.arrayBuffer().then((buf) => ws.send(buf));
              console.log('[Audio] Sent chunk:', e.data.size, 'bytes');
            }
          };

          mediaRecorder.start(2000);
          console.log('[Audio] Recording started');
        } catch (err) {
          console.error('[Audio Error]', err);
          transcriptionError.textContent = `Microphone error: ${err.name} - ${err.message}`;
          startBtn.disabled = false;
          stopBtn.disabled = true;
        }
      };

    } catch (err) {
      console.error('[Session Error]', err);
      transcriptionError.textContent = `Session error: ${err.name} - ${err.message}`;
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }
  };
}

if (stopBtn) {
  stopBtn.onclick = function() {
    stopBtn.disabled = true;
    startBtn.disabled = false;

    // Stop the mic tracks — let the last ondataavailable flush naturally
    try { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); } catch {}
    try { if (audioStream) audioStream.getTracks().forEach(t => t.stop()); } catch {}

    // Wait 400 ms for the final ondataavailable chunk to arrive at whisper, then finalize
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('FINALIZE');
        console.log('[Session] Sent FINALIZE');
      }
    }, 400);
  };
}

if (saveBtn) {
  saveBtn.onclick = async function() {
    saveBtn.disabled = true;
    transcriptionSaved.textContent = 'Saving transcription...';
    transcriptionError.textContent = '';
    try {
      const resp = await fetch('/transcriptions/save-transcription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consultation_id: parseInt(consultationId),
          session_id: sessionId
        })
      });
      const responseText = await resp.text();
      if (!resp.ok) {
        transcriptionError.textContent = `Server error (${resp.status}): ${responseText}`;
        saveBtn.disabled = false;
        return;
      }
      transcriptionSaved.textContent = 'Transcription saved successfully!';
      startBtn.disabled = true;
      stopBtn.disabled = true;
      saveBtn.disabled = true;
      consultationId = null;
      sessionId = null;
    } catch (err) {
      transcriptionError.textContent = err.message || err;
      saveBtn.disabled = false;
    }
  };
}
