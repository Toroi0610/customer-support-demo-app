/**
 * StartConversationUseCase - initializes a new conversation session.
 *
 * Responsibilities:
 *   1. Connect the AI port to the backend WebSocket proxy
 *   2. Return a new Conversation aggregate for the session
 */

import { Conversation } from "../../domain/conversation/Conversation.js";

export class StartConversationUseCase {
  /**
   * @param {import("../../application/ports/AIConversationPort.js").AIConversationPort} aiPort
   */
  constructor(aiPort) {
    this._aiPort = aiPort;
  }

  /**
   * Connect to the AI service and return a fresh Conversation aggregate.
   *
   * @param {{ serviceUrl: string, sessionConfig: Object }} params
   * @returns {Promise<Conversation>}
   */
  async execute({ serviceUrl, sessionConfig }) {
    await this._aiPort.connect(serviceUrl, sessionConfig);
    return new Conversation();
  }
}
