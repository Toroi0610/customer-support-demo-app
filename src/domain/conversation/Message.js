/**
 * Message - value object for a single conversation turn.
 *
 * Immutable: create a new Message rather than mutating an existing one.
 */

export const MessageRole = Object.freeze({
  USER: "user",
  ASSISTANT: "assistant",
  UNKNOWN: "unknown",
});

export class Message {
  /**
   * @param {{ role: string, text: string }} params
   */
  constructor({ role, text }) {
    this.role = Object.values(MessageRole).includes(role)
      ? role
      : MessageRole.UNKNOWN;
    this.text = text || "";
    Object.freeze(this);
  }

  isEmpty() {
    return !this.text.trim();
  }

  toDict() {
    return { role: this.role, text: this.text };
  }

  static fromDict(data) {
    return new Message({ role: data.role, text: data.text });
  }
}
