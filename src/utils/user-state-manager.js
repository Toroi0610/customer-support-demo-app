/**
 * User State Manager
 * Maintains user emotion history and decides whether the AI should speak.
 */

const EMOTION_MAP = {
  // HIGH — speak immediately
  "困っている": "HIGH",
  "悲しい": "HIGH",
  "怒り": "HIGH",
  "泣いている": "HIGH",
  "怒っている": "HIGH",
  "イライラ": "HIGH",
  "落ち込んでいる": "HIGH",
  // MEDIUM — speak if consecutive
  "困惑": "MEDIUM",
  "疲れている": "MEDIUM",
  "不安": "MEDIUM",
  "戸惑い": "MEDIUM",
  "心配": "MEDIUM",
  // LOW — speak at intervals
  "集中": "LOW",
  "通常": "LOW",
  "普通": "LOW",
  "笑顔": "LOW",
  "作業中": "LOW",
  "リラックス": "LOW",
  "楽しそう": "LOW",
  "真剣": "LOW",
  "不在": "LOW",
};

export class UserStateManager {
  constructor(options = {}) {
    this.lowIntervalMs = options.lowIntervalMs ?? 60000;
    this.mediumConsecutiveThreshold = options.mediumConsecutiveThreshold ?? 2;
    this.historyMaxLength = options.historyMaxLength ?? 20;

    this.emotionHistory = [];
    this.lastSpokeAt = null;
    this.isFirstEvaluation = true;
  }

  /**
   * Classify an emotion string into HIGH, MEDIUM, or LOW.
   */
  classifyEmotion(emotion) {
    if (!emotion) return "LOW";

    // Direct match
    if (EMOTION_MAP[emotion]) {
      return EMOTION_MAP[emotion];
    }

    // Partial match — check if emotion contains a known keyword
    for (const [keyword, level] of Object.entries(EMOTION_MAP)) {
      if (emotion.includes(keyword)) {
        return level;
      }
    }

    return "LOW";
  }

  /**
   * Evaluate an analysis result and decide whether the AI should speak.
   * @param {Object} analysis - { emotion, status_key, observation }
   * @returns {{ shouldSpeak: boolean, level: string, reason: string }}
   */
  evaluate(analysis) {
    const emotion = analysis.emotion || "";
    const level = this.classifyEmotion(emotion);
    const now = Date.now();

    // Record in history
    this.emotionHistory.push({ emotion, level, timestamp: now, statusKey: analysis.status_key });
    if (this.emotionHistory.length > this.historyMaxLength) {
      this.emotionHistory.shift();
    }

    // First evaluation — always speak (greeting)
    if (this.isFirstEvaluation) {
      this.isFirstEvaluation = false;
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "initial" };
    }

    // HIGH — speak immediately
    if (level === "HIGH") {
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "high_emotion" };
    }

    // MEDIUM — speak if consecutive
    if (level === "MEDIUM") {
      const consecutiveCount = this._getConsecutiveMediumCount();
      if (consecutiveCount >= this.mediumConsecutiveThreshold) {
        this.lastSpokeAt = now;
        return { shouldSpeak: true, level, reason: "consecutive_medium" };
      }
      return { shouldSpeak: false, level, reason: "medium_not_consecutive" };
    }

    // LOW — speak if enough time has passed
    const elapsed = this.lastSpokeAt ? now - this.lastSpokeAt : Infinity;
    if (elapsed >= this.lowIntervalMs) {
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "low_interval" };
    }

    return { shouldSpeak: false, level, reason: "low_within_interval" };
  }

  /**
   * Decide whether a realtime video nudge should be sent.
   * HIGH/MEDIUM: always nudge. LOW: only if interval has elapsed.
   */
  shouldNudge() {
    if (this.emotionHistory.length === 0) return true;

    const lastEntry = this.emotionHistory[this.emotionHistory.length - 1];
    if (lastEntry.level === "HIGH" || lastEntry.level === "MEDIUM") {
      return true;
    }

    // LOW — check interval
    const now = Date.now();
    const elapsed = this.lastSpokeAt ? now - this.lastSpokeAt : Infinity;
    return elapsed >= this.lowIntervalMs;
  }

  /**
   * Count consecutive MEDIUM entries at the end of history.
   */
  _getConsecutiveMediumCount() {
    let count = 0;
    for (let i = this.emotionHistory.length - 1; i >= 0; i--) {
      if (this.emotionHistory[i].level === "MEDIUM") {
        count++;
      } else {
        break;
      }
    }
    return count;
  }
}
