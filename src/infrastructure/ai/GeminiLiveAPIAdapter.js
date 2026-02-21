/**
 * GeminiLiveAPIAdapter - infrastructure adapter for the Gemini Live API.
 *
 * Implements AIConversationPort using a WebSocket connection proxied
 * through the Python backend. Isolates all Gemini protocol details
 * so the application layer stays agnostic of the underlying AI service.
 */

import { AIConversationPort } from "../../application/ports/AIConversationPort.js";

// Re-export so presentation-layer code can import from one location
export { GeminiLiveAPI } from "../../utils/gemini-api.js";

export class GeminiLiveAPIAdapter extends AIConversationPort {
  /**
   * @param {string} proxyUrl      - WebSocket URL of the backend proxy
   * @param {string} appPassword   - APP_PASSWORD sent in the handshake
   * @param {string} userId        - Stable user identifier
   * @param {string} persona       - Selected persona key
   * @param {Object} [options]     - Optional GeminiLiveAPI configuration
   */
  constructor(proxyUrl, appPassword, userId, persona, options = {}) {
    super();
    this._proxyUrl = proxyUrl;
    this._appPassword = appPassword;
    this._userId = userId;
    this._persona = persona;
    this._options = options;

    /** @type {import("../../utils/gemini-api.js").GeminiLiveAPI | null} */
    this._client = null;
    this._messageHandlers = [];
  }

  /**
   * Connect to the Gemini backend proxy.
   *
   * Dynamically imports GeminiLiveAPI to keep infrastructure details
   * out of the domain and application layers.
   *
   * @param {string} serviceUrl  - Gemini Live API endpoint (sent to proxy)
   * @param {Object} sessionConfig - Gemini session setup message body
   */
  async connect(serviceUrl, sessionConfig) {
    const { GeminiLiveAPI } = await import("../../utils/gemini-api.js");

    this._client = new GeminiLiveAPI(this._proxyUrl, {
      appPassword: this._appPassword,
      userId: this._userId,
      persona: this._persona,
      ...this._options,
    });

    // Forward all incoming messages to registered handlers
    this._client.onResponse = (message) => {
      for (const handler of this._messageHandlers) {
        handler(message);
      }
    };

    await this._client.connect(serviceUrl, sessionConfig);
  }

  async disconnect() {
    if (this._client) {
      this._client.disconnect();
      this._client = null;
    }
  }

  sendAudio(audioBase64) {
    this._client?.sendAudioMessage(audioBase64);
  }

  sendVideo(imageBase64) {
    this._client?.sendVideoFrame(imageBase64);
  }

  /**
   * Register a handler to receive parsed Gemini response messages.
   * @param {Function} handler
   */
  onMessage(handler) {
    this._messageHandlers.push(handler);
  }

  get isConnected() {
    return this._client !== null && !this._client.disconnected;
  }
}
