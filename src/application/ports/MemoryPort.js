/**
 * MemoryPort - interface (port) for memory persistence operations.
 *
 * Implemented by BackendAPIClient in the infrastructure layer.
 */

export class MemoryPort {
  /**
   * Save a conversation as a persistent memory.
   *
   * @param {{ userId: string, persona: string, transcript: Array,
   *           emotions: string[], projectId: string }} params
   * @returns {Promise<{ memory_id: string, summary: string }>}
   */
  async saveMemory(params) {
    throw new Error("saveMemory() must be implemented by the infrastructure adapter");
  }

  /**
   * List recent memories for a user+persona.
   *
   * @param {{ userId: string, persona: string, limit?: number }} params
   * @returns {Promise<{ memories: Array }>}
   */
  async listMemories(params) {
    throw new Error("listMemories() must be implemented by the infrastructure adapter");
  }
}
