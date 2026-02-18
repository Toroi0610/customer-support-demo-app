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
    this.lowIntervalMs = options.lowIntervalMs || 60000;
    this.mediumConsecutiveThreshold = options.mediumConsecutiveThreshold || 2;
    this.historyMaxLength = options.historyMaxLength || 20;

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
}
