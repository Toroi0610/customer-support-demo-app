/**
 * SaveConversationMemoryUseCase - saves a completed conversation as a memory record.
 *
 * Delegates to MemoryPort (infrastructure) which calls the backend.
 */

export class SaveConversationMemoryUseCase {
  /**
   * @param {import("../../application/ports/MemoryPort.js").MemoryPort} memoryPort
   */
  constructor(memoryPort) {
    this._memoryPort = memoryPort;
  }

  /**
   * @param {{ userId: string, persona: string, conversation: import("../../domain/conversation/Conversation.js").Conversation, projectId: string }} params
   * @returns {Promise<{ memory_id: string, summary: string }>}
   */
  async execute({ userId, persona, conversation, projectId }) {
    const transcript = conversation.getTranscript();

    if (transcript.length === 0) {
      throw new Error("Cannot save an empty conversation");
    }

    return await this._memoryPort.saveMemory({
      userId,
      persona,
      transcript,
      emotions: conversation.emotionEvents,
      projectId,
    });
  }
}
