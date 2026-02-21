/**
 * Conversation - aggregate root for a single chat session.
 *
 * Holds the ordered list of messages and any user emotion events observed
 * during the session (used when saving memory at the end).
 */

import { Message, MessageRole } from "./Message.js";

export class Conversation {
  constructor() {
    /** @type {Message[]} */
    this.messages = [];
    /** @type {string[]} */
    this.emotionEvents = [];
    this.startedAt = new Date();
  }

  /**
   * Append a message if non-empty, returning the Message entity.
   * @param {string} role
   * @param {string} text
   * @returns {Message}
   */
  addMessage(role, text) {
    const message = new Message({ role, text });
    if (!message.isEmpty()) {
      this.messages.push(message);
    }
    return message;
  }

  /**
   * Record an observed user emotion event for the session summary.
   * @param {string} emotion
   */
  addEmotionEvent(emotion) {
    if (emotion) {
      this.emotionEvents.push(emotion);
    }
  }

  /** Return transcript as plain dicts for serialization. */
  getTranscript() {
    return this.messages.map((m) => m.toDict());
  }

  isEmpty() {
    return this.messages.length === 0;
  }

  get messageCount() {
    return this.messages.length;
  }
}
