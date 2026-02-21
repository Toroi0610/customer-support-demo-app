/**
 * AIConversationPort - interface (port) for AI conversation services.
 *
 * Defines the contract that infrastructure adapters must fulfill.
 * The domain and application layers only depend on this interface,
 * never on the concrete Gemini implementation.
 *
 * JavaScript doesn't have abstract classes, so this class throws
 * on every method to enforce the contract at runtime during development.
 */

export class AIConversationPort {
  /**
   * Connect to the AI service.
   * @param {string} serviceUrl
   * @param {Object} sessionConfig - Gemini setup message body
   * @returns {Promise<void>}
   */
  async connect(serviceUrl, sessionConfig) {
    throw new Error("connect() must be implemented by the infrastructure adapter");
  }

  /** Disconnect from the AI service. */
  async disconnect() {
    throw new Error("disconnect() must be implemented by the infrastructure adapter");
  }

  /**
   * Send a base64-encoded audio chunk.
   * @param {string} audioBase64
   */
  sendAudio(audioBase64) {
    throw new Error("sendAudio() must be implemented by the infrastructure adapter");
  }

  /**
   * Send a base64-encoded video frame.
   * @param {string} imageBase64
   */
  sendVideo(imageBase64) {
    throw new Error("sendVideo() must be implemented by the infrastructure adapter");
  }

  /**
   * Register a callback to receive incoming AI messages.
   * @param {Function} handler - Called with each parsed message object
   */
  onMessage(handler) {
    throw new Error("onMessage() must be implemented by the infrastructure adapter");
  }

  /** Whether the connection is currently active. @returns {boolean} */
  get isConnected() {
    throw new Error("isConnected must be implemented by the infrastructure adapter");
  }
}
