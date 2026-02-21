"""
JavaScript bridge for NiceGUI frontend.

This module provides the JavaScript code that runs in the browser to handle:
- WebSocket connection to the backend Gemini proxy
- Audio capture (microphone via AudioWorklet)
- Video capture (camera frames)
- Audio playback (AudioWorklet)
- Real-time chat display updates (direct DOM manipulation)

Architecture note: Browser media APIs (getUserMedia, AudioWorklet, WebSocket)
cannot be run in Python — they require browser execution. NiceGUI allows injecting
JavaScript via ui.add_head_html() and calling it via ui.run_javascript().
"""

GEMINI_BRIDGE_JS = r"""
<script>
// ─── Gemini Live API WebSocket Client ──────────────────────────────────────

class GeminiClient {
  constructor() {
    this.ws = null;
    this.connected = false;
    this.projectId = '';
    this.modelUri = '';
    this.serviceUrl = '';
  }

  connect(wsUrl, config) {
    this.serviceUrl = 'wss://us-central1-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent';
    this.projectId = config.projectId;
    this.modelUri = `projects/${config.projectId}/locations/us-central1/publishers/google/models/${config.model}`;

    console.log('Connecting to backend proxy:', wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket opened — sending auth setup');
      this.sendMessage({
        service_url: this.serviceUrl,
        app_password: config.appPassword,
        user_id: config.userId,
        persona: config.persona,
      });

      const tools = [
        { name: 'celebrate_moment', description: 'ユーザーが喜んでいる・達成したときに呼び出す', parameters: { type: 'object', properties: { message: { type: 'string' } }, required: ['message'] } },
        { name: 'offer_support', description: 'ユーザーが悲しい・疲れているときに呼び出す', parameters: { type: 'object', properties: { message: { type: 'string' } }, required: ['message'] } },
        { name: 'express_separation_anxiety', description: 'ユーザーがカメラを置こうとしているときに呼び出す', parameters: { type: 'object', properties: { message: { type: 'string' } }, required: ['message'] } },
        { name: 'report_visual_state', description: '映像の状態を報告する', parameters: { type: 'object', properties: { observation: { type: 'string' }, status_key: { type: 'string' }, emotion: { type: 'string' }, details: { type: 'string' } }, required: ['observation', 'status_key', 'emotion'] } },
      ];

      const sessionSetup = {
        setup: {
          model: this.modelUri,
          generation_config: {
            response_modalities: ['AUDIO'],
            temperature: config.temperature,
            speech_config: {
              voice_config: { prebuilt_voice_config: { voice_name: config.voice } },
            },
          },
          system_instruction: { parts: [{ text: config.systemInstruction }] },
          tools: { function_declarations: tools },
          proactivity: { proactiveAudio: config.proactiveAudio },
          realtime_input_config: {
            automatic_activity_detection: {
              disabled: config.disableActivityDetection,
              silence_duration_ms: config.silenceDuration,
              prefix_padding_ms: config.prefixPadding,
            },
          },
        },
      };

      if (config.inputTranscription) sessionSetup.setup.input_audio_transcription = {};
      if (config.outputTranscription) sessionSetup.setup.output_audio_transcription = {};
      if (config.grounding) {
        sessionSetup.setup.tools = { google_search: {} };
      }
      if (config.affectiveDialog) {
        sessionSetup.setup.generation_config.enable_affective_dialog = true;
      }

      this.sendMessage(sessionSetup);
      console.log('Session setup sent');
    };

    this.ws.onclose = (e) => {
      console.log('WebSocket closed:', e.code, e.reason);
      this.connected = false;
      window._niceguiOnDisconnect && window._niceguiOnDisconnect(e.code, e.reason);
    };

    this.ws.onerror = (e) => {
      console.error('WebSocket error:', e);
      window._niceguiOnError && window._niceguiOnError('WebSocket接続エラー');
    };

    this.ws.onmessage = (e) => this._onMessage(e);
  }

  _onMessage(event) {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error('Failed to parse WS message', err);
      return;
    }

    if (data.error === 'unauthorized') {
      window._niceguiOnAuthError && window._niceguiOnAuthError();
      return;
    }

    // Parse Gemini response format
    if (data.setupComplete) {
      this.connected = true;
      window._niceguiOnConnected && window._niceguiOnConnected();
      appendChatMessage('準備完了！', 'system');
      return;
    }

    if (data.serverContent?.turnComplete) return;

    if (data.serverContent?.interrupted) {
      appendChatMessage('[中断されました]', 'system');
      window._audioPlayer && window._audioPlayer.interrupt();
      return;
    }

    if (data.serverContent?.inputTranscription) {
      const t = data.serverContent.inputTranscription;
      appendChatMessage(t.text || '', 'user', t.finished);
      return;
    }

    if (data.serverContent?.outputTranscription) {
      const t = data.serverContent.outputTranscription;
      appendChatMessage(t.text || '', 'assistant', t.finished);
      return;
    }

    if (data.toolCall) {
      const calls = data.toolCall.functionCalls || [];
      calls.forEach(call => {
        const { name, args, id } = call;
        console.log('Tool call:', name, args);
        this._handleToolCall(name, args, id);
      });
      return;
    }

    const parts = data.serverContent?.modelTurn?.parts;
    if (parts?.length) {
      if (parts[0].text) {
        appendChatMessage(parts[0].text, 'assistant', true);
      } else if (parts[0].inlineData) {
        window._audioPlayer && window._audioPlayer.play(parts[0].inlineData.data);
      }
    }
  }

  _handleToolCall(name, args, callId) {
    const message = args.message || args.observation || '';

    if (name === 'celebrate_moment') {
      appendChatMessage(message, 'celebrate');
    } else if (name === 'offer_support') {
      appendChatMessage(message, 'support');
    } else if (name === 'express_separation_anxiety') {
      appendChatMessage(message, 'separation-anxiety');
    } else if (name === 'report_visual_state') {
      appendChatMessage(`👁 ${args.observation || ''} (${args.emotion || ''})`, 'system');
    }

    // Send tool response back
    this.sendMessage({
      tool_response: {
        function_responses: [{ id: callId, response: { result: 'ok' } }],
      },
    });
  }

  sendMessage(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendAudio(base64PCM) {
    this.sendMessage({
      realtime_input: { media_chunks: [{ mime_type: 'audio/pcm', data: base64PCM }] },
    });
  }

  sendImage(base64JPEG) {
    this.sendMessage({
      realtime_input: { media_chunks: [{ mime_type: 'image/jpeg', data: base64JPEG }] },
    });
  }

  sendText(text) {
    this.sendMessage({
      client_content: {
        turns: [{ role: 'user', parts: [{ text }] }],
        turn_complete: true,
      },
    });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }
}


// ─── Audio Player (24kHz PCM from Gemini) ──────────────────────────────────

class AudioPlayer {
  constructor() {
    this.ctx = null;
    this.worklet = null;
    this.gain = null;
    this.ready = false;
  }

  async init() {
    if (this.ready) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    await this.ctx.audioWorklet.addModule('/audio-processors/playback.worklet.js');
    this.worklet = new AudioWorkletNode(this.ctx, 'pcm-processor');
    this.gain = this.ctx.createGain();
    this.worklet.connect(this.gain);
    this.gain.connect(this.ctx.destination);
    this.ready = true;
  }

  async play(base64Audio) {
    if (!this.ready) await this.init();
    if (this.ctx.state === 'suspended') await this.ctx.resume();

    const binary = atob(base64Audio);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    const pcm16 = new Int16Array(bytes.buffer);
    const f32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) f32[i] = pcm16[i] / 32768;

    this.worklet.port.postMessage(f32);
  }

  interrupt() {
    this.worklet && this.worklet.port.postMessage('interrupt');
  }

  setVolume(v) {
    if (this.gain) this.gain.gain.value = Math.max(0, Math.min(1, v));
  }

  destroy() {
    this.ctx && this.ctx.close();
    this.ready = false;
  }
}


// ─── Audio Streamer (16kHz mic capture) ────────────────────────────────────

class AudioStreamer {
  constructor(client) {
    this.client = client;
    this.ctx = null;
    this.worklet = null;
    this.stream = null;
    this.running = false;
  }

  async start(deviceId) {
    const constraints = { audio: { sampleRate: 16000, echoCancellation: true, noiseSuppression: true } };
    if (deviceId) constraints.audio.deviceId = { exact: deviceId };

    this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    this.ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    await this.ctx.audioWorklet.addModule('/audio-processors/capture.worklet.js');
    this.worklet = new AudioWorkletNode(this.ctx, 'audio-capture-processor');

    this.worklet.port.onmessage = (e) => {
      if (!this.running || e.data.type !== 'audio') return;
      const pcm16 = new Int16Array(e.data.data.length);
      for (let i = 0; i < e.data.data.length; i++) {
        pcm16[i] = Math.max(-1, Math.min(1, e.data.data[i])) * 0x7fff;
      }
      const bytes = new Uint8Array(pcm16.buffer);
      let bin = '';
      for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
      this.client.sendAudio(btoa(bin));
    };

    const src = this.ctx.createMediaStreamSource(this.stream);
    src.connect(this.worklet);
    this.running = true;
    console.log('Mic streaming started');
  }

  stop() {
    this.running = false;
    this.worklet && this.worklet.disconnect();
    this.stream && this.stream.getTracks().forEach(t => t.stop());
    this.ctx && this.ctx.close();
    this.worklet = this.stream = this.ctx = null;
    console.log('Mic streaming stopped');
  }
}


// ─── Video Streamer (camera → JPEG frames) ─────────────────────────────────

class VideoStreamer {
  constructor(client) {
    this.client = client;
    this.stream = null;
    this.video = null;
    this.canvas = null;
    this.timer = null;
    this.running = false;
    this.previewEl = null;
  }

  async start(deviceId) {
    const constraints = { video: { width: { ideal: 640 }, height: { ideal: 480 } } };
    if (deviceId) constraints.video.deviceId = { exact: deviceId };

    this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    this.video = document.createElement('video');
    this.video.srcObject = this.stream;
    this.video.autoplay = true;
    this.video.playsInline = true;
    this.video.muted = true;

    await new Promise(resolve => { this.video.onloadedmetadata = resolve; });
    this.video.play();

    // Show preview if container exists
    const preview = document.getElementById('video-preview');
    if (preview) {
      preview.srcObject = this.stream;
      preview.hidden = false;
      this.previewEl = preview;
    }

    this.canvas = document.createElement('canvas');
    this.canvas.width = 640;
    this.canvas.height = 480;
    const ctx = this.canvas.getContext('2d');

    this.running = true;
    this.timer = setInterval(() => {
      if (!this.running) return;
      ctx.drawImage(this.video, 0, 0, 640, 480);
      this.canvas.toBlob(blob => {
        if (!blob) return;
        const reader = new FileReader();
        reader.onloadend = () => {
          const b64 = reader.result.split(',')[1];
          if (this.client && this.client.connected) this.client.sendImage(b64);
        };
        reader.readAsDataURL(blob);
      }, 'image/jpeg', 0.8);
    }, 1000);

    console.log('Camera streaming started');
  }

  stop() {
    this.running = false;
    this.timer && clearInterval(this.timer);
    this.stream && this.stream.getTracks().forEach(t => t.stop());
    if (this.previewEl) { this.previewEl.srcObject = null; this.previewEl.hidden = true; }
    this.video = this.stream = this.canvas = this.timer = this.previewEl = null;
    console.log('Camera streaming stopped');
  }
}


// ─── Chat DOM Utilities ─────────────────────────────────────────────────────

let _lastRole = null;
let _lastMsgEl = null;

function appendChatMessage(text, role, finished = true) {
  if (!text) return;
  const area = document.getElementById('chat-messages');
  if (!area) return;

  // For streaming (append to last message of same role)
  if (!finished && role === _lastRole && _lastMsgEl) {
    const textSpan = _lastMsgEl.querySelector('.msg-text');
    if (textSpan) { textSpan.textContent += text; area.scrollTop = area.scrollHeight; return; }
  }

  const el = document.createElement('div');
  el.style.cssText = 'margin:6px 0; padding:8px 12px; border-radius:8px; max-width:85%; word-wrap:break-word; font-size:14px;';

  if (role === 'user') {
    el.style.cssText += 'background:#1976d2; color:#fff; margin-left:auto; text-align:right;';
    el.innerHTML = `<span class="msg-text">${escapeHtml(text)}</span>`;
  } else if (role === 'assistant') {
    el.style.cssText += 'background:#2d2d2d; color:#e0e0e0;';
    el.innerHTML = `<span class="msg-text">${escapeHtml(text)}</span>`;
  } else if (role === 'system') {
    el.style.cssText += 'background:transparent; color:#888; font-size:12px; font-style:italic; max-width:100%; text-align:center;';
    el.innerHTML = `<span class="msg-text">${escapeHtml(text)}</span>`;
  } else if (role === 'celebrate') {
    el.style.cssText += 'background:linear-gradient(135deg,#ffd700,#ff8c00); color:#1a1a1a; font-weight:bold;';
    el.innerHTML = `<span>🎉</span> <span class="msg-text">${escapeHtml(text)}</span>`;
  } else if (role === 'support') {
    el.style.cssText += 'background:linear-gradient(135deg,#4fc3f7,#1976d2); color:#fff;';
    el.innerHTML = `<span>💙</span> <span class="msg-text">${escapeHtml(text)}</span>`;
  } else if (role === 'separation-anxiety') {
    el.style.cssText += 'background:linear-gradient(135deg,#ce93d8,#7b1fa2); color:#fff;';
    el.innerHTML = `<span>😢</span> <span class="msg-text">${escapeHtml(text)}</span>`;
  }

  area.appendChild(el);
  area.scrollTop = area.scrollHeight;

  if (!finished) { _lastRole = role; _lastMsgEl = el; }
  else { _lastRole = null; _lastMsgEl = null; }
}

function clearChat() {
  const area = document.getElementById('chat-messages');
  if (area) area.innerHTML = '';
  _lastRole = null;
  _lastMsgEl = null;
}

function escapeHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}


// ─── Global API (called from Python via ui.run_javascript) ─────────────────

window._geminiClient = null;
window._audioPlayer = null;
window._audioStreamer = null;
window._videoStreamer = null;

window.geminiConnect = async function(wsUrl, config) {
  if (window._geminiClient) {
    window._geminiClient.disconnect();
  }
  window._audioPlayer = new AudioPlayer();
  window._geminiClient = new GeminiClient();
  window._geminiClient.connect(wsUrl, config);
};

window.geminiDisconnect = function() {
  window._geminiClient && window._geminiClient.disconnect();
  window._audioStreamer && window._audioStreamer.stop();
  window._videoStreamer && window._videoStreamer.stop();
  window._audioPlayer && window._audioPlayer.destroy();
  window._geminiClient = window._audioStreamer = window._videoStreamer = window._audioPlayer = null;
  clearChat();
};

window.geminiStartAudio = async function(deviceId) {
  if (!window._geminiClient) return;
  window._audioStreamer = new AudioStreamer(window._geminiClient);
  await window._audioStreamer.start(deviceId || null);
};

window.geminiStopAudio = function() {
  window._audioStreamer && window._audioStreamer.stop();
  window._audioStreamer = null;
};

window.geminiStartVideo = async function(deviceId) {
  if (!window._geminiClient) return;
  window._videoStreamer = new VideoStreamer(window._geminiClient);
  await window._videoStreamer.start(deviceId || null);
};

window.geminiStopVideo = function() {
  window._videoStreamer && window._videoStreamer.stop();
  window._videoStreamer = null;
};

window.geminiSendText = function(text) {
  window._geminiClient && window._geminiClient.sendText(text);
};

window.geminiSetVolume = function(v) {
  window._audioPlayer && window._audioPlayer.setVolume(v);
};

// Enumerate media devices and return as JSON string
window.geminiListDevices = async function() {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true, video: true }).then(s => s.getTracks().forEach(t => t.stop())).catch(() => {});
    const devices = await navigator.mediaDevices.enumerateDevices();
    return JSON.stringify(devices.map(d => ({ kind: d.kind, deviceId: d.deviceId, label: d.label || d.deviceId.slice(0,8) })));
  } catch(e) {
    return '[]';
  }
};
</script>
"""
