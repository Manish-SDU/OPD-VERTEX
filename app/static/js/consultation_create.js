// consultation_create.js
// Patient lookup + consultation creation + Faster-Whisper transcription UI.

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
          li.textContent = 'No patients found - check the spelling';
          suggestionsList.appendChild(li);
          showPatientError('No matching patient. Check the name.');
        } else {
          if (patients.length === 1) {
            const p = patients[0];
            idField.value = p.id;
            idInput.value = p.id;
            showPatientSuccess(`\u2713 ${p.first_name} ${p.last_name} (ID ${p.id})`);
          }
          patients.forEach((p) => {
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
      } catch (_) {
        // Ignore transient lookup errors while typing
      }
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
        const exact = patients.find((p) => String(p.id) === q);
        if (exact) {
          idField.value = exact.id;
          nameInput.value = `${exact.first_name} ${exact.last_name}`;
          showPatientSuccess(`\u2713 ${exact.first_name} ${exact.last_name} (ID ${exact.id})`);
        } else {
          showPatientError(`No patient found with ID ${q}.`);
        }
      } catch (_) {
        // Ignore transient lookup errors while typing
      }
    }, 300);
  });
}

const TARGET_SAMPLE_RATE = 16000;

let isRecording = false;
let finalizedTranscript = '';
let consultationId = null;
let sessionId = null;
let usedMicrophoneCapture = false;
let audioContext = null;
let mediaStream = null;
let mediaSource = null;
let processorNode = null;
let transcriptionSocket = null;

const form = document.getElementById('create-consultation-form');
const successDiv = document.getElementById('consultation-success');
const errorDiv = document.getElementById('consultation-error');
const transcriptionUI = document.getElementById('transcription-ui');
const startBtn = document.getElementById('start-transcription');
const stopBtn = document.getElementById('stop-transcription');
const saveBtn = document.getElementById('save-transcription');
const transcriptionError = document.getElementById('transcription-error');
const transcriptionSaved = document.getElementById('transcription-saved');
const transcriptArea = document.getElementById('transcript-display');
const statusEl = document.getElementById('trx-status');

if (transcriptArea) transcriptArea.removeAttribute('readonly');

function setStatus(state, text) {
  if (!statusEl) return;
  statusEl.classList.remove('trx-status--recording', 'trx-status--saved');
  if (state === 'recording') statusEl.classList.add('trx-status--recording');
  if (state === 'saved') statusEl.classList.add('trx-status--saved');
  const txt = statusEl.querySelector('.trx-status__text');
  if (txt) txt.textContent = text;
}

function resolveConsultationId() {
  if (consultationId) return consultationId;

  const runtimeContext = window.__CONSULTATION_CONTEXT__;
  if (runtimeContext && runtimeContext.consultationId) {
    consultationId = String(runtimeContext.consultationId);
    return consultationId;
  }

  if (transcriptionUI && transcriptionUI.dataset.consultationId) {
    consultationId = String(transcriptionUI.dataset.consultationId);
    return consultationId;
  }

  const match = window.location.pathname.match(/\/consultations\/(\d+)/);
  if (match) {
    consultationId = match[1];
    return consultationId;
  }

  return null;
}

function initializeExistingConsultation() {
  const resolvedConsultationId = resolveConsultationId();
  if (!resolvedConsultationId) return;
  if (transcriptionUI) transcriptionUI.style.display = '';
  if (startBtn) startBtn.disabled = false;
  if (saveBtn) saveBtn.disabled = false;
  setStatus('ready', 'Ready');
}

async function ensureTranscriptionSession() {
  const resolvedConsultationId = resolveConsultationId();
  if (!resolvedConsultationId) {
    throw new Error('Could not determine the consultation ID for this page.');
  }

  if (sessionId) return sessionId;

  const response = await fetch('/transcriptions/session/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ consultation_id: parseInt(resolvedConsultationId, 10) }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Could not start transcription session (${response.status})`);
  }

  const data = await response.json();
  sessionId = data.session_id;
  return sessionId;
}

function updateTranscriptArea(partialText) {
  if (!transcriptArea) return;
  const finalText = finalizedTranscript.trim();
  const partial = (partialText || '').trim();
  transcriptArea.value = [finalText, partial].filter(Boolean).join(finalText && partial ? ' ' : '');
}

function resetTranscriptionState() {
  isRecording = false;
  finalizedTranscript = '';
  usedMicrophoneCapture = false;
}

function downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
  if (inputSampleRate === outputSampleRate) {
    return buffer;
  }

  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;

    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      accum += buffer[i];
      count += 1;
    }

    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function floatTo16BitPCM(floatBuffer) {
  const output = new Int16Array(floatBuffer.length);
  for (let i = 0; i < floatBuffer.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, floatBuffer[i]));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output;
}

function cleanupAudioPipeline() {
  if (processorNode) {
    processorNode.onaudioprocess = null;
    try { processorNode.disconnect(); } catch (_) {}
    processorNode = null;
  }

  if (mediaSource) {
    try { mediaSource.disconnect(); } catch (_) {}
    mediaSource = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    try { audioContext.close(); } catch (_) {}
    audioContext = null;
  }

  if (transcriptionSocket) {
    try {
      if (transcriptionSocket.readyState === WebSocket.OPEN) {
        transcriptionSocket.send('FINALIZE');
      }
      transcriptionSocket.close();
    } catch (_) {
      // Ignore cleanup errors
    }
    transcriptionSocket = null;
  }
}

async function startAudioCapture() {
  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error('This browser does not support Web Audio capture.');
  }

  audioContext = new AudioContextClass();
  mediaSource = audioContext.createMediaStreamSource(mediaStream);
  processorNode = audioContext.createScriptProcessor(4096, 1, 1);

  processorNode.onaudioprocess = (event) => {
    if (!isRecording || !transcriptionSocket || transcriptionSocket.readyState !== WebSocket.OPEN) {
      return;
    }

    const inputData = event.inputBuffer.getChannelData(0);
    const downsampled = downsampleBuffer(inputData, audioContext.sampleRate, TARGET_SAMPLE_RATE);
    const pcm16 = floatTo16BitPCM(downsampled);
    transcriptionSocket.send(pcm16.buffer);
  };

  mediaSource.connect(processorNode);
  processorNode.connect(audioContext.destination);
}

async function openTranscriptionSocket(activeSessionId) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socketUrl = `${protocol}://${window.location.host}/transcriptions/ws/${activeSessionId}`;

  await new Promise((resolve, reject) => {
    transcriptionSocket = new WebSocket(socketUrl);
    transcriptionSocket.binaryType = 'arraybuffer';

    transcriptionSocket.onopen = () => resolve();
    transcriptionSocket.onerror = () => reject(new Error('Could not connect to the transcription stream.'));
    transcriptionSocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.error) {
          transcriptionError.textContent = payload.error;
          return;
        }

        if (payload.text && payload.text !== '[processing...]') {
          finalizedTranscript = [finalizedTranscript.trim(), payload.text.trim()].filter(Boolean).join(' ');
          updateTranscriptArea('');
        } else if (payload.partial_text) {
          updateTranscriptArea(payload.partial_text);
        }
      } catch (_) {
        // Ignore non-JSON frames
      }
    };
    transcriptionSocket.onclose = () => {
      transcriptionSocket = null;
    };
  });
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
      errorDiv.textContent = err.message || String(err);
      errorDiv.style.display = '';
    }
  };
}

initializeExistingConsultation();

if (startBtn && !(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
  startBtn.title = 'Live transcription requires browser microphone access.';
}

if (startBtn) {
  startBtn.onclick = async function () {
    const resolvedConsultationId = resolveConsultationId();
    if (!resolvedConsultationId) {
      transcriptionError.textContent =
        'Could not determine which consultation to save this transcript to. Please reload the page and try again.';
      return;
    }
    if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
      transcriptionError.textContent =
        '\u26a0\ufe0f This browser cannot capture microphone audio for Faster-Whisper. '
        + 'You can still paste the transcript manually below and click Save.';
      return;
    }

    cleanupAudioPipeline();
    resetTranscriptionState();
    isRecording = true;
    usedMicrophoneCapture = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    saveBtn.disabled = true;
    transcriptionError.textContent = '';
    transcriptionSaved.textContent = '';
    if (transcriptArea) transcriptArea.value = '';
    setStatus('recording', 'Starting…');

    try {
      const activeSessionId = await ensureTranscriptionSession();
      console.log('[MedFlow] Starting Faster-Whisper capture, consultationId=', resolvedConsultationId, 'sessionId=', activeSessionId);
      await openTranscriptionSocket(activeSessionId);
      await startAudioCapture();
      setStatus('recording', 'Recording');
    } catch (err) {
      cleanupAudioPipeline();
      isRecording = false;
      startBtn.disabled = false;
      stopBtn.disabled = true;
      saveBtn.disabled = false;
      transcriptionError.textContent = err.message || String(err);
      setStatus('ready', 'Ready');
    }
  };
}

if (stopBtn) {
  stopBtn.onclick = function () {
    console.log('[MedFlow] Stop clicked, transcript so far:', transcriptArea ? transcriptArea.value.substring(0, 80) : '(none)');
    isRecording = false;
    cleanupAudioPipeline();
    stopBtn.disabled = true;
    startBtn.disabled = false;
    saveBtn.disabled = false;
    setStatus('saved', 'Stopped');
  };
}

if (saveBtn) {
  saveBtn.onclick = async function () {
    const resolvedConsultationId = resolveConsultationId();
    if (!resolvedConsultationId) {
      transcriptionSaved.textContent = '';
      transcriptionError.textContent =
        'Could not determine which consultation to save this transcript to. Please reload the page and try again.';
      return;
    }

    const transcriptText = transcriptArea ? transcriptArea.value.trim() : '';
    if (!transcriptText) {
      transcriptionSaved.textContent = '';
      transcriptionError.textContent = 'Please record, type, or paste a transcript before saving.';
      if (transcriptArea) transcriptArea.focus();
      return;
    }

    saveBtn.disabled = true;
    transcriptionSaved.textContent = 'Saving transcription...';
    transcriptionError.textContent = '';
    const hasManualEditsAfterRecording =
      usedMicrophoneCapture
      && finalizedTranscript.trim()
      && transcriptText !== finalizedTranscript.trim();

    try {
      await ensureTranscriptionSession();
      if (transcriptText && sessionId && (!usedMicrophoneCapture || hasManualEditsAfterRecording)) {
        await fetch(`/transcriptions/session/${sessionId}/inject-demo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: transcriptText }),
        });
      }
    } catch (e) {
      console.warn('[Save] inject fallback failed', e);
    }

    try {
      const saveUrl = usedMicrophoneCapture && sessionId && !hasManualEditsAfterRecording
        ? `/transcriptions/session/${sessionId}/complete`
        : '/transcriptions/save-transcription';
      const saveOptions = usedMicrophoneCapture && sessionId && !hasManualEditsAfterRecording
        ? { method: 'POST' }
        : {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            consultation_id: parseInt(resolvedConsultationId, 10),
            session_id: sessionId,
          }),
        };
      const resp = await fetch(saveUrl, saveOptions);
      const responseText = await resp.text();
      if (!resp.ok) {
        let errorMessage = `Server error (${resp.status})`;
        try {
          const payload = JSON.parse(responseText);
          errorMessage = payload.detail || errorMessage;
        } catch (_) {
          if (responseText) errorMessage = `${errorMessage}: ${responseText.substring(0, 200)}`;
        }
        transcriptionError.textContent = errorMessage;
        saveBtn.disabled = false;
        return;
      }
      transcriptionSaved.textContent = 'Transcription saved! Opening review workflow...';
      const reviewId = resolvedConsultationId;
      startBtn.disabled = true;
      stopBtn.disabled = true;
      setStatus('saved', 'Saved');
      setTimeout(() => { window.location.href = `/review/${reviewId}`; }, 800);
    } catch (err) {
      transcriptionError.textContent = err.message || String(err);
      saveBtn.disabled = false;
    }
  };
}
