/**
 * MemoryRecord - entity representing a stored conversation summary.
 *
 * Produced by the backend memory endpoint and consumed by the session-start
 * logic to display past conversation context.
 */

export class MemoryRecord {
  /**
   * @param {{ summary: string, emotion: string, importance: number,
   *           daysAgo: number, timestamp?: string, relevance?: number }} params
   */
  constructor({ summary, emotion, importance, daysAgo, timestamp, relevance }) {
    this.summary = summary || "";
    this.emotion = emotion || "";
    this.importance = typeof importance === "number" ? importance : 0.5;
    this.daysAgo = daysAgo || 0;
    this.timestamp = timestamp || "";
    this.relevance = relevance ?? null;
  }

  /** Human-readable "when" label in Japanese. */
  get whenLabel() {
    if (this.daysAgo === 0) return "今日";
    if (this.daysAgo === 1) return "昨日";
    return `${this.daysAgo}日前`;
  }

  /**
   * Build from a backend DTO (snake_case keys).
   * @param {Object} dto
   * @returns {MemoryRecord}
   */
  static fromDTO(dto) {
    return new MemoryRecord({
      summary: dto.summary,
      emotion: dto.emotion,
      importance: dto.importance,
      daysAgo: dto.days_ago,
      timestamp: dto.timestamp,
      relevance: dto.relevance,
    });
  }
}
