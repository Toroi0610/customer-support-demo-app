/**
 * UserObservation - entity representing the result of one camera frame analysis.
 *
 * Created by AnalyzeUserStateUseCase from the backend API response.
 */

export class UserObservation {
  /**
   * @param {{ observation: string, statusKey: string, emotion: string,
   *           details: string, significantChange: boolean, timestamp?: Date }} params
   */
  constructor({
    observation,
    statusKey,
    emotion,
    details,
    significantChange,
    timestamp,
  }) {
    this.observation = observation || "";
    this.statusKey = statusKey || "";
    this.emotion = emotion || "";
    this.details = details || "";
    this.significantChange = Boolean(significantChange);
    this.timestamp = timestamp || new Date();
  }

  isSignificant() {
    return this.significantChange;
  }

  /**
   * Build from the raw JSON returned by the /analyze-frame endpoint.
   * @param {Object} data - API response object
   * @returns {UserObservation}
   */
  static fromAPIResponse(data) {
    return new UserObservation({
      observation: data.observation,
      statusKey: data.status_key,
      emotion: data.emotion,
      details: data.details,
      significantChange: data.significant_change,
    });
  }
}
