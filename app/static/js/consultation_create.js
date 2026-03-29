// consultation_create.js
// Handles AJAX consultation creation and transcription UI logic for the create consultation page

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
    errorDiv.textContent = '';
    transcriptionUI.style.display = 'none';
    const formData = new FormData(form);
    const payload = {
      patient_id: formData.get('patient_id'),
      chief_complaint: formData.get('chief_complaint')
    };
    try {
      const resp = await fetch('/consultations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(payload)
      });
      if (!resp.redirected && !resp.ok) throw new Error('Failed to create consultation');
      // Try to extract consultation ID from redirect URL or response
      let url = resp.url;
      let match = url.match(/consultations\/(\d+)/);
      if (!match) throw new Error('Could not determine consultation ID');
      consultationId = match[1];
      successDiv.textContent = 'Consultation created! Starting transcription...';
      transcriptionUI.style.display = '';
      startBtn.disabled = false;
      // Auto-start transcription
      setTimeout(() => startBtn.click(), 500);
    } catch (err) {
      errorDiv.textContent = err.message || err;
    }
  };
}

if (startBtn) {
  startBtn.onclick = async function() {
    startBtn.disabled = true;
    stopBtn.disabled = false;
    transcriptionError.textContent = '';
    partialText.textContent = '';
    chunksList.innerHTML = '';
    transcriptionSaved.textContent = '';
    try {
      const resp = await fetch('/transcriptions/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consultation_id: consultationId })
      });
      const data = await resp.json();
      sessionId = data.session_id;
      ws = new WebSocket(`ws://${window.location.host}/transcriptions/ws/${sessionId}`);
      ws.binaryType = 'arraybuffer';
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.chunk_id !== undefined) {
          const li = document.createElement('li');
          li.textContent = `[${data.timestamp}s] ${data.text}`;
          chunksList.appendChild(li);
        } else if (data.partial_text !== undefined) {
          partialText.textContent = data.partial_text;
        } else if (data.error) {
          transcriptionError.textContent = data.error;
        }
      };
      ws.onerror = (event) => {
        transcriptionError.textContent = 'WebSocket error';
      };
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
      mediaRecorder.ondataavailable = function(e) {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data);
        }
      };
      mediaRecorder.start(500); // send every 500ms
    } catch (err) {
      transcriptionError.textContent = err.message || err;
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }
  };
}
if (stopBtn) {
  stopBtn.onclick = function() {
    stopBtn.disabled = true;
    startBtn.disabled = false;
    saveBtn.disabled = false;
    if (mediaRecorder) mediaRecorder.stop();
    if (audioStream) audioStream.getTracks().forEach(track => track.stop());
    if (ws) ws.close();
  };
}

if (saveBtn) {
  saveBtn.onclick = async function() {
    saveBtn.disabled = true;
    transcriptionSaved.textContent = 'Saving transcription...';
    transcriptionError.textContent = '';
    try {
      const resp = await fetch(`/transcriptions/session/${sessionId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await resp.json();
      if (resp.ok) {
        transcriptionSaved.textContent = 'Transcription saved successfully!';
        form.reset();
        startBtn.disabled = true;
        stopBtn.disabled = true;
        saveBtn.disabled = true;
        consultationId = null;
        sessionId = null;
      } else {
        transcriptionError.textContent = data.detail || 'Failed to save transcription';
        saveBtn.disabled = false;
      }
    } catch (err) {
      transcriptionError.textContent = err.message || err;
      saveBtn.disabled = false;
    }
  };
}
