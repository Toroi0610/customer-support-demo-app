/**
 * AnalyzeUserStateUseCase - orchestrates video frame analysis and speech decision.
 *
 * Composes:
 *   - BackendAPIClient (infrastructure) — calls /analyze-frame
 *   - EmotionClassificationService (domain) — maps emotion to level
 *   - SpeechDecisionService (domain) — decides if AI should speak
 */

import { EmotionClassificationService } from "../../domain/userState/EmotionClassificationService.js";
import { SpeechDecisionService } from "../../domain/userState/SpeechDecisionService.js";
import { UserObservation } from "../../domain/userState/UserObservation.js";

export class AnalyzeUserStateUseCase {
  /**
   * @param {import("../../infrastructure/api/BackendAPIClient.js").BackendAPIClient} apiClient
   * @param {Object} [options] - SpeechDecisionService options
   */
  constructor(apiClient, options = {}) {
    this._apiClient = apiClient;
    this._classifier = new EmotionClassificationService();
    this._speechDecision = new SpeechDecisionService(options);
  }

  /**
   * Analyze a video frame and determine how the AI should respond.
   *
   * @param {string} imageBase64
   * @param {string} previousStatus
   * @param {string} projectId
   * @param {string} [model]
   * @returns {Promise<{ observation: UserObservation, shouldSpeak: boolean, level: string, reason: string }>}
   */
  async execute(imageBase64, previousStatus, projectId, model) {
    const data = await this._apiClient.analyzeFrame(
      imageBase64,
      previousStatus,
      projectId,
      model
    );
    const observation = UserObservation.fromAPIResponse(data);
    const level = this._classifier.classify(observation.emotion);
    const decision = this._speechDecision.evaluate(
      observation.emotion,
      level,
      observation.statusKey
    );

    return {
      observation,
      shouldSpeak: decision.shouldSpeak,
      level: decision.level,
      reason: decision.reason,
    };
  }

  /** Whether the monitor should send a nudge to the AI right now. */
  shouldNudge() {
    return this._speechDecision.shouldNudge();
  }
}
