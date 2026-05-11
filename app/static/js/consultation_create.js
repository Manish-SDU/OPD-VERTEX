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
const transcriptArea    = document.getElementById('transcript-display');
const demoBtn           = document.getElementById('demo-transcript');

if (form) {
  form.onsubmit = async function(e) {
    e.preventDefault();
    successDiv.textContent = '';
    successDiv.style.display = 'none';
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    transcriptionUI.style.display = 'none';
    // Validate patient selection
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
      // Try to extract consultation ID from redirect URL or response
      let url = resp.url;
      let match = url.match(/consultations\/(\d+)/);
      if (!match) throw new Error('Could not determine consultation ID');
      consultationId = match[1];
      sessionId = null;  // Reset session for new consultation
      successDiv.textContent = 'Consultation created! Starting transcription...';
      successDiv.style.display = '';
      transcriptionUI.style.display = '';
      startBtn.disabled = false;
      // Auto-start transcription
      setTimeout(() => startBtn.click(), 500);
    } catch (err) {
      errorDiv.textContent = err.message || err;
      errorDiv.style.display = '';
    }
  };
}

if (startBtn) {
  startBtn.onclick = async function() {
    // Clean up any previous audio context and stream
    if (audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      console.log("[Audio] Cleaned up previous audio stream");
    }
    if (processor) {
      processor.disconnect();
      console.log("[Audio] Disconnected previous processor");
    }
    if (audioContext && audioContext.state !== 'closed') {
      await audioContext.close();
      console.log("[Audio] Closed previous audio context");
    }
    
    startBtn.disabled = true;
    stopBtn.disabled = false;
    transcriptionError.textContent = '';
    partialText.textContent = '';
    chunksList.innerHTML = '';
    transcriptionSaved.textContent = '';
    try {
      // Only create new session if one doesn't exist (allows reuse across stop/start)
      if (!sessionId) {
        const resp = await fetch('/transcriptions/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ consultation_id: consultationId })
        });
        const raw = await resp.text();
        if (!resp.ok) {
          throw new Error(`Start session failed (${resp.status}): ${raw.substring(0, 180)}`);
        }

        let data;
        try {
          data = JSON.parse(raw);
        } catch (parseErr) {
          throw new Error(`Start session returned non-JSON response: ${raw.substring(0, 180)}`);
        }

        if (!data || !data.session_id) {
          throw new Error('Start session response is missing session_id');
        }

        sessionId = data.session_id;
        console.log(`[Session] Created new session: ${sessionId}`);
      } else {
        console.log(`[Session] Reusing existing session: ${sessionId}`);
      }
      ws = new WebSocket(`ws://${window.location.host}/transcriptions/ws/${sessionId}`);
      ws.binaryType = 'arraybuffer';
      ws.onmessage = (event) => {
        try {
          if (typeof event.data !== 'string') {
            // Ignore non-text websocket frames.
            return;
          }

          const trimmed = event.data.trim();
          if (!trimmed.startsWith('{')) {
            // Ignore heartbeat or unexpected plain-text frames.
            return;
          }

          const data = JSON.parse(trimmed);
          if (data.chunk_id !== undefined) {
            const li = document.createElement('li');
            li.textContent = `[${data.timestamp}s] ${data.text}`;
            chunksList.appendChild(li);
          } else if (data.partial_text !== undefined) {
            partialText.textContent = data.partial_text;
            if (transcriptArea) transcriptArea.value = data.partial_text;
          } else if (data.error) {
            transcriptionError.textContent = data.error;
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', event.data, e);
          transcriptionError.textContent = 'Invalid message from server: ' + e.message;
        }
      };
      ws.onerror = (event) => {
        transcriptionError.textContent = 'WebSocket error';
      };
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("[Audio] Microphone access granted", audioStream);
      
      // Use Web Audio API for raw PCM audio instead of MediaRecorder/WebM
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      console.log(`[Audio] Context state: ${audioContext.state}, Sample rate: ${audioContext.sampleRate}`);
      
      // Resume audio context if suspended (browsers require user gesture)
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
        console.log(`[Audio] Context resumed, state now: ${audioContext.state}`);
      }
      
      const source = audioContext.createMediaStreamSource(audioStream);
      console.log("[Audio] Media stream source created");
      
      // Add a gain node to boost low microphone input
      const gainNode = audioContext.createGain();
      gainNode.gain.value = 6.0; // Boost audio level by 6x
      console.log("[Audio] Gain node created with gain: 6.0x");
      
      processor = audioContext.createScriptProcessor(4096, 1, 1);
      console.log("[Audio] Script processor created");
      
      source.connect(gainNode);
      gainNode.connect(processor);
      processor.connect(audioContext.destination);
      console.log("[Audio] Connections established");
      
      // Calculate resampling ratio: from audioContext.sampleRate to 16000 Hz
      const resampleRatio = 16000 / audioContext.sampleRate;
      console.log(`[Audio] Resampling ratio: ${audioContext.sampleRate}Hz -> 16000Hz (${resampleRatio.toFixed(4)})`);
      
      let frameCount = 0;
      let maxPeak = 0;
      let resampleBuffer = [];
      
      processor.onaudioprocess = (e) => {
        const audioData = e.inputBuffer.getChannelData(0);
        frameCount++;
        
        // Calculate RMS (root mean square) to check audio level
        let sum = 0;
        let peak = 0;
        for (let i = 0; i < audioData.length; i++) {
          sum += audioData[i] * audioData[i];
          peak = Math.max(peak, Math.abs(audioData[i]));
        }
        maxPeak = Math.max(maxPeak, peak);
        const rms = Math.sqrt(sum / audioData.length);
        
        // Simple linear interpolation resampling
        const targetLength = Math.floor(audioData.length * resampleRatio);
        const resampledData = new Float32Array(targetLength);
        
        for (let i = 0; i < targetLength; i++) {
          const sourceIndex = i / resampleRatio;
          const leftIndex = Math.floor(sourceIndex);
          const rightIndex = leftIndex + 1;
          const fraction = sourceIndex - leftIndex;
          
          if (rightIndex < audioData.length) {
            resampledData[i] = audioData[leftIndex] * (1 - fraction) + audioData[rightIndex] * fraction;
          } else {
            resampledData[i] = audioData[leftIndex] || 0;
          }
        }
        
        // Convert resampled audio to Int16
        const int16Array = new Int16Array(resampledData.length);
        for (let i = 0; i < resampledData.length; i++) {
          int16Array[i] = Math.max(-1, Math.min(1, resampledData[i])) * 0x7FFF;
        }
        
        // Log audio level every 10 frames (~225ms)
        if (frameCount % 10 === 0) {
          console.log(`[Audio Level] Frame ${frameCount}: RMS: ${rms.toFixed(4)}, Peak: ${peak.toFixed(4)}, Max Peak So Far: ${maxPeak.toFixed(4)}`);
          console.log(`[WS Debug] Frame ${frameCount}: ws=${ws}, readyState=${ws ? ws.readyState : 'N/A'}, OPEN=${WebSocket.OPEN}`);
        }
        
        if (ws && ws.readyState === WebSocket.OPEN) {
          console.log(`[WS Send] Sending ${int16Array.length} int16 samples, buffer size: ${int16Array.buffer.byteLength} bytes`);
          ws.send(int16Array.buffer);
        } else {
          console.warn(`[WS Send] WebSocket not ready: readyState=${ws ? ws.readyState : 'undefined'}, ws=${ws}`);
        }
      };
    } catch (err) {
      console.error("[Audio Error]", err);
      transcriptionError.textContent = `Audio error: ${err.name} - ${err.message}`;
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }
  };
}
if (stopBtn) {
  stopBtn.onclick = async function() {
    stopBtn.disabled = true;
    startBtn.disabled = false;
    saveBtn.disabled = false;
    
    // Stop audio capture
    if (processor) {
      processor.disconnect();
      console.log("[Audio] Processor disconnected");
    }
    if (audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      console.log("[Audio] Audio stream stopped");
    }
    
    // Close WebSocket
    if (ws) ws.close();
    
    // Poll for results every 500ms
    let lastResultsCount = 0;
    let lastPartialText = '';
    const pollInterval = setInterval(async () => {
      try {
        const resp = await fetch(`/transcriptions/session/${sessionId}/results`);
        const data = await resp.json();
        
        // Display results - only update if count changed (new chunk arrived)
        if (data.results && data.results.length > lastResultsCount) {
          lastResultsCount = data.results.length;
          chunksList.innerHTML = '';
          data.results.forEach(result => {
            // Skip empty chunks
            if (result.text && result.text.trim()) {
              const li = document.createElement('li');
              li.textContent = `[${result.timestamp}s] ${result.text}`;
              chunksList.appendChild(li);
            }
          });
        }
        
        // Only update partial text if it actually changed
        if (data.partial_text && data.partial_text !== lastPartialText) {
          lastPartialText = data.partial_text;
          partialText.textContent = data.partial_text;
          if (transcriptArea) transcriptArea.value = data.partial_text;
        }
      } catch (err) {
        console.error('Error polling results:', err);
      }
    }, 500);
    
    // Stop polling after 30 seconds
    setTimeout(() => clearInterval(pollInterval), 30000);
  };
}

if (saveBtn) {
  saveBtn.onclick = async function() {
    saveBtn.disabled = true;
    transcriptionSaved.textContent = 'Saving transcription...';
    transcriptionError.textContent = '';
    try {
      const resp = await fetch(`/transcriptions/save-transcription`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consultation_id: parseInt(consultationId),
          session_id: sessionId
        })
      });
      
      // Get the response text first to see what we actually received
      const responseText = await resp.text();
      console.log(`[Save] Response status: ${resp.status}, Content-Type: ${resp.headers.get('content-type')}`);
      console.log(`[Save] Response text: ${responseText.substring(0, 500)}`);
      
      if (!resp.ok) {
        transcriptionError.textContent = `Server error (${resp.status}): ${responseText}`;
        saveBtn.disabled = false;
        return;
      }
      
      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseErr) {
        console.error('[Save] JSON parse failed:', parseErr);
        transcriptionError.textContent = `JSON parse error: ${parseErr.message}. Response: ${responseText.substring(0, 200)}`;
        saveBtn.disabled = false;
        return;
      }
      
      transcriptionSaved.textContent = 'Transcription saved successfully!';
      form.reset();
      startBtn.disabled = true;
      stopBtn.disabled = true;
      saveBtn.disabled = true;
      if (transcriptArea) transcriptArea.value = '';
      consultationId = null;
      sessionId = null;
    } catch (err) {
      console.error('[Save] Fetch error:', err);
      transcriptionError.textContent = err.message || err;
      saveBtn.disabled = false;
    }
  };
}

// ── Demo transcript (no microphone) ──────────────────────────────────
const DEMO_TEXT =
`Receptionist: Good morning. What brings you in today?

Patient: I've been having stomach pain since last night.

Receptionist: Please have a seat. The doctor will see you shortly.

Doctor: Hello, I'm Dr. Smith. What seems to be the problem?

Patient: I have pain in my stomach, mostly on the lower right side.

Doctor: When did it start?

Patient: Yesterday evening after dinner.

Doctor: Do you have nausea, vomiting, or fever?

Patient: I feel a little nauseous, but no fever.

Doctor: How strong is the pain from 1 to 10?

Patient: About a 6.

Doctor: I'm going to examine your abdomen now.

Patient: Okay.

Doctor: It may be a stomach infection or irritation, but I'd like you to get a scan and some blood tests to be safe.

Patient: Alright.

Doctor: Until then, drink plenty of water, avoid heavy food, and take the medicine I prescribe.

Patient: Thank you, doctor.

Doctor: You're welcome. Please come back if the pain gets worse.`;

if (demoBtn) {
  demoBtn.onclick = async function () {
    demoBtn.disabled = true;
    transcriptionError.textContent = '';
    transcriptionSaved.textContent = '';
    try {
      // Start session if needed
      if (!sessionId) {
        const resp = await fetch('/transcriptions/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ consultation_id: parseInt(consultationId) }),
        });
        const raw = await resp.text();
        if (!resp.ok) throw new Error(`Start session failed (${resp.status}): ${raw.substring(0, 200)}`);
        const data = JSON.parse(raw);
        if (!data.session_id) throw new Error('Missing session_id in response');
        sessionId = data.session_id;
      }

      // Inject demo text
      const injectResp = await fetch(`/transcriptions/session/${sessionId}/inject-demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: DEMO_TEXT }),
      });
      if (!injectResp.ok) {
        const err = await injectResp.text();
        throw new Error(`Inject failed (${injectResp.status}): ${err.substring(0, 200)}`);
      }

      // Show text and enable save
      if (transcriptArea) transcriptArea.value = DEMO_TEXT;
      startBtn.disabled = true;
      stopBtn.disabled = true;
      saveBtn.disabled = false;
      transcriptionSaved.textContent = 'Demo transcript loaded — click Save Transcription to continue.';
    } catch (err) {
      console.error('[Demo] Error:', err);
      transcriptionError.textContent = err.message || err;
      demoBtn.disabled = false;
    }
  };
}
