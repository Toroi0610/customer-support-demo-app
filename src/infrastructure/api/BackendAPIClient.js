/**
 * BackendAPIClient - HTTP client for all backend REST API operations.
 *
 * Implements MemoryPort and also provides analyzeFrame() used by
 * AnalyzeUserStateUseCase. Centralises all fetch() calls in one place
 * so base URL and auth headers are configured once.
 */

import { MemoryPort } from "../../application/ports/MemoryPort.js";

export class BackendAPIClient extends MemoryPort {
  /**
   * @param {string} baseUrl    - Backend base URL (e.g. "http://localhost:8080")
   * @param {string} appPassword - APP_PASSWORD for Bearer auth
   */
  constructor(baseUrl, appPassword) {
    super();
    this._baseUrl = baseUrl || "";
    this._appPassword = appPassword || "";
  }

  get _headers() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this._appPassword}`,
    };
  }

  /**
   * Analyze a video frame via the /analyze-frame endpoint.
   *
   * @param {string} imageBase64
   * @param {string} previousStatus
   * @param {string} projectId
   * @param {string} [model]
   * @returns {Promise<Object>}
   */
  async analyzeFrame(
    imageBase64,
    previousStatus,
    projectId,
    model = "gemini-2.0-flash"
  ) {
    const response = await fetch(`${this._baseUrl}/analyze-frame`, {
      method: "POST",
      headers: this._headers,
      body: JSON.stringify({
        image: imageBase64,
        previous_status: previousStatus,
        project_id: projectId,
        model,
      }),
    });

    if (!response.ok) {
      throw new Error(`Frame analysis failed: ${response.status}`);
    }
    return response.json();
  }

  // ── MemoryPort implementation ─────────────────────────────────────────────

  async saveMemory({ userId, persona, transcript, emotions, projectId }) {
    const response = await fetch(`${this._baseUrl}/memory/save`, {
      method: "POST",
      headers: this._headers,
      body: JSON.stringify({
        user_id: userId,
        persona,
        transcript,
        emotions,
        project_id: projectId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Memory save failed: ${response.status}`);
    }
    return response.json();
  }

  async listMemories({ userId, persona, limit = 10 }) {
    const params = new URLSearchParams({
      user_id: userId,
      persona,
      limit: String(limit),
    });
    const response = await fetch(`${this._baseUrl}/memory/list?${params}`, {
      headers: this._headers,
    });

    if (!response.ok) {
      throw new Error(`Memory list failed: ${response.status}`);
    }
    return response.json();
  }
}
