/**
 * EmotionClassificationService - pure domain service.
 *
 * Maps Japanese emotion strings to urgency levels.
 * Contains only business rules — no I/O, no framework dependencies.
 */

import { EmotionLevel } from "./EmotionLevel.js";

const EMOTION_MAP = {
  // ── HIGH (immediate response) ───────────────────────────────────────────────
  困っている: EmotionLevel.HIGH,
  悲しい: EmotionLevel.HIGH,
  怒り: EmotionLevel.HIGH,
  泣いている: EmotionLevel.HIGH,
  怒っている: EmotionLevel.HIGH,
  イライラ: EmotionLevel.HIGH,
  落ち込んでいる: EmotionLevel.HIGH,

  // ── MEDIUM (conditional response) ──────────────────────────────────────────
  困惑: EmotionLevel.MEDIUM,
  疲れている: EmotionLevel.MEDIUM,
  不安: EmotionLevel.MEDIUM,
  戸惑い: EmotionLevel.MEDIUM,
  心配: EmotionLevel.MEDIUM,

  // ── LOW (interval-based response) ──────────────────────────────────────────
  集中: EmotionLevel.LOW,
  通常: EmotionLevel.LOW,
  普通: EmotionLevel.LOW,
  笑顔: EmotionLevel.LOW,
  作業中: EmotionLevel.LOW,
  リラックス: EmotionLevel.LOW,
  楽しそう: EmotionLevel.LOW,
  真剣: EmotionLevel.LOW,
  不在: EmotionLevel.LOW,
};

export class EmotionClassificationService {
  /**
   * Classify an emotion string into HIGH, MEDIUM, or LOW.
   * Falls back to LOW for unknown / empty values.
   *
   * @param {string} emotion - Japanese emotion label
   * @returns {string} EmotionLevel constant
   */
  classify(emotion) {
    if (!emotion) return EmotionLevel.LOW;

    // Direct match
    if (EMOTION_MAP[emotion]) {
      return EMOTION_MAP[emotion];
    }

    // Partial match — check if the label contains a known keyword
    for (const [keyword, level] of Object.entries(EMOTION_MAP)) {
      if (emotion.includes(keyword)) {
        return level;
      }
    }

    return EmotionLevel.LOW;
  }
}
