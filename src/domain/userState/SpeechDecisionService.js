/**
 * SpeechDecisionService - domain service that decides whether the AI should speak.
 *
 * Replaces UserStateManager with a cleaner DDD-style service that separates
 * classification (EmotionClassificationService) from decision logic.
 */

import { EmotionLevel } from "./EmotionLevel.js";

export class SpeechDecisionService {
  /**
   * @param {Object} options
   * @param {number} [options.lowIntervalMs=60000]       - Min ms between LOW-emotion responses
   * @param {number} [options.mediumConsecutiveThreshold=2] - Consecutive MEDIUM count to trigger
   * @param {number} [options.historyMaxLength=20]       - Max entries in emotion history
   */
  constructor(options = {}) {
    this.lowIntervalMs = options.lowIntervalMs ?? 60_000;
    this.mediumConsecutiveThreshold = options.mediumConsecutiveThreshold ?? 2;
    this.historyMaxLength = options.historyMaxLength ?? 20;

    /** @type {Array<{emotion: string, level: string, timestamp: number, statusKey: string}>} */
    this.emotionHistory = [];
    this.lastSpokeAt = null;
    this._isFirstEvaluation = true;
  }

  /**
   * Evaluate whether the AI should respond to the current observation.
   *
   * @param {string} emotion   - Detected emotion label
   * @param {string} level     - EmotionLevel constant
   * @param {string} statusKey - Short status key from camera analysis
   * @returns {{ shouldSpeak: boolean, level: string, reason: string }}
   */
  evaluate(emotion, level, statusKey) {
    const now = Date.now();

    this.emotionHistory.push({ emotion, level, timestamp: now, statusKey });
    if (this.emotionHistory.length > this.historyMaxLength) {
      this.emotionHistory.shift();
    }

    // First evaluation → always greet the user
    if (this._isFirstEvaluation) {
      this._isFirstEvaluation = false;
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "initial" };
    }

    if (level === EmotionLevel.HIGH) {
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "high_emotion" };
    }

    if (level === EmotionLevel.MEDIUM) {
      const count = this._consecutiveMediumCount();
      if (count >= this.mediumConsecutiveThreshold) {
        this.lastSpokeAt = now;
        return { shouldSpeak: true, level, reason: "consecutive_medium" };
      }
      return { shouldSpeak: false, level, reason: "medium_not_consecutive" };
    }

    // LOW — respect the time interval
    const elapsed = this.lastSpokeAt ? now - this.lastSpokeAt : Infinity;
    if (elapsed >= this.lowIntervalMs) {
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "low_interval" };
    }
    return { shouldSpeak: false, level, reason: "low_within_interval" };
  }

  /**
   * Whether the monitor should nudge the AI regardless of the speech decision.
   * HIGH/MEDIUM always nudge; LOW respects the interval.
   */
  shouldNudge() {
    if (this.emotionHistory.length === 0) return true;

    const last = this.emotionHistory[this.emotionHistory.length - 1];
    if (last.level === EmotionLevel.HIGH || last.level === EmotionLevel.MEDIUM) {
      return true;
    }

    const elapsed = this.lastSpokeAt
      ? Date.now() - this.lastSpokeAt
      : Infinity;
    return elapsed >= this.lowIntervalMs;
  }

  _consecutiveMediumCount() {
    let count = 0;
    for (let i = this.emotionHistory.length - 1; i >= 0; i--) {
      if (this.emotionHistory[i].level === EmotionLevel.MEDIUM) {
        count++;
      } else {
        break;
      }
    }
    return count;
  }
}
