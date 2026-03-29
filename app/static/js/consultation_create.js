// consultation_create.js
// Handles AJAX consultation creation and transcription UI logic for the create consultation page

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
        body: new URLSearchParams(payload),
        redirect: 'follow'
      });
      if (!resp.ok) throw new Error('Failed to create consultation');
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
      const resp = await fetch('/transcriptions/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consultation_id: consultationId })
      });
      const data = await resp.json();
      sessionId = data.session_id;
      console.log(`[Session] Started new session: ${sessionId}`);
      ws = new WebSocket(`ws://${window.location.host}/transcriptions/ws/${sessionId}`);
      ws.binaryType = 'arraybuffer';
      ws.onmessage = (event) => {
        try {
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
        }
        
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(int16Array.buffer);
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
      const resp = await fetch(`/transcriptions/session/${sessionId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
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
      consultationId = null;
      sessionId = null;
    } catch (err) {
      console.error('[Save] Fetch error:', err);
      transcriptionError.textContent = err.message || err;
      saveBtn.disabled = false;
    }
  };
}
