/**
 * EmotionLevel - urgency classification for detected user emotions.
 *
 * HIGH   → AI speaks immediately (distress signals)
 * MEDIUM → AI speaks after consecutive detections
 * LOW    → AI speaks at periodic intervals (neutral / positive states)
 */

export const EmotionLevel = Object.freeze({
  HIGH: "HIGH",
  MEDIUM: "MEDIUM",
  LOW: "LOW",
});
