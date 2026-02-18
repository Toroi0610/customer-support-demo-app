import { UserStateManager } from "./user-state-manager.js";

/**
 * User State Monitor
 * Independently monitors video frames and detects significant changes in the user's state.
 * When a change is detected, triggers a callback to notify the AI to speak.
 */

export class UserStateMonitor {
  /**
   * @param {Object} options
   * @param {string} options.analysisUrl - URL of the frame analysis endpoint
   * @param {string|null} options.appPassword - App password for Authorization header (optional)
   * @param {string} options.projectId - Google Cloud project ID
   * @param {string} options.model - Gemini model ID for analysis
   * @param {number} options.intervalMs - Monitoring interval in milliseconds (default: 5000)
   * @param {function} options.onSignificantChange - Callback when significant change detected
   * @param {function} options.onStateUpdate - Callback for every state update (for UI)
   * @param {function} options.onError - Callback for errors
   */
  constructor(options = {}) {
    this.analysisUrl = options.analysisUrl || "http://localhost:8080/analyze-frame";
    this.appPassword = options.appPassword || null;
    this.projectId = options.projectId || "";
    this.model = options.model || "gemini-2.0-flash";
    this.intervalMs = options.intervalMs || 5000;
    this.onSignificantChange = options.onSignificantChange || (() => {});
    this.onStateUpdate = options.onStateUpdate || (() => {});
    this.onError = options.onError || console.error;

    this.isMonitoring = false;
    this.monitorTimer = null;
    this.videoElement = null;
    this.canvas = null;
    this.ctx = null;
    this.previousStatusKey = null;
    this.analysisInProgress = false;
    this.stateHistory = [];
    this.stateManager = new UserStateManager({
      lowIntervalMs: options.lowIntervalMs || 60000,
      mediumConsecutiveThreshold: options.mediumConsecutiveThreshold || 2,
    });
  }

  /**
   * Start monitoring a video element
   * @param {HTMLVideoElement} videoElement - The video element to capture frames from
   */
  start(videoElement) {
    if (this.isMonitoring) {
      console.warn("UserStateMonitor: Already monitoring");
      return;
    }

    if (!videoElement) {
      throw new Error("UserStateMonitor: No video element provided");
    }

    this.videoElement = videoElement;

    // Create canvas for frame capture
    this.canvas = document.createElement("canvas");
    this.canvas.width = 640;
    this.canvas.height = 480;
    this.ctx = this.canvas.getContext("2d");

    this.isMonitoring = true;
    this.previousStatusKey = null;
    this.stateHistory = [];

    console.log(`UserStateMonitor: Started (interval: ${this.intervalMs}ms)`);

    // Run first analysis immediately
    this._analyzeFrame();

    // Then run at intervals
    this.monitorTimer = setInterval(() => {
      this._analyzeFrame();
    }, this.intervalMs);
  }

  /**
   * Stop monitoring
   */
  stop() {
    this.isMonitoring = false;

    if (this.monitorTimer) {
      clearInterval(this.monitorTimer);
      this.monitorTimer = null;
    }

    this.videoElement = null;
    this.canvas = null;
    this.ctx = null;

    console.log("UserStateMonitor: Stopped");
  }

  /**
   * Capture and analyze a single frame
   */
  async _analyzeFrame() {
    if (!this.isMonitoring || this.analysisInProgress) return;
    if (!this.videoElement || this.videoElement.readyState < 2) return;

    this.analysisInProgress = true;

    try {
      // Capture frame from video
      this.ctx.drawImage(
        this.videoElement,
        0,
        0,
        this.canvas.width,
        this.canvas.height
      );

      // Convert to base64 JPEG
      const dataUrl = this.canvas.toDataURL("image/jpeg", 0.7);
      const base64Image = dataUrl.split(",")[1];

      // Send to analysis endpoint
      const authHeaders = { "Content-Type": "application/json" };
      if (this.appPassword) {
        authHeaders["Authorization"] = `Bearer ${this.appPassword}`;
      }
      const response = await fetch(this.analysisUrl, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          image: base64Image,
          previous_status: this.previousStatusKey || "",
          project_id: this.projectId,
          model: this.model,
        }),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status}`);
      }

      const analysis = await response.json();

      if (analysis.error) {
        throw new Error(analysis.error);
      }

      const timestamp = new Date().toLocaleTimeString("ja-JP");
      const stateEntry = {
        ...analysis,
        timestamp,
        previousStatusKey: this.previousStatusKey,
      };

      // Keep last 20 entries
      this.stateHistory.push(stateEntry);
      if (this.stateHistory.length > 20) {
        this.stateHistory.shift();
      }

      // Always notify UI of state update
      this.onStateUpdate(stateEntry);

      // Evaluate with state manager
      const evaluation = this.stateManager.evaluate(analysis);
      const previousKey = this.previousStatusKey;
      this.previousStatusKey = analysis.status_key;

      if (evaluation.shouldSpeak) {
        console.log(
          `UserStateMonitor: Should speak (${evaluation.reason}, level: ${evaluation.level}) ${previousKey || "初回検知"} -> ${analysis.status_key}: ${analysis.observation}`
        );
        this.onSignificantChange(analysis, previousKey || "初回検知");
      } else {
        console.log(
          `UserStateMonitor: Silent (${evaluation.reason}, level: ${evaluation.level}) ${analysis.status_key}: ${analysis.observation}`
        );
      }
    } catch (error) {
      console.error("UserStateMonitor: Analysis error:", error);
      this.onError(error);
    } finally {
      this.analysisInProgress = false;
    }
  }

  /**
   * Get the state manager instance (for external nudge control).
   */
  getStateManager() {
    return this.stateManager;
  }

  /**
   * Get the current monitoring state
   */
  getState() {
    return {
      isMonitoring: this.isMonitoring,
      currentStatusKey: this.previousStatusKey,
      historyLength: this.stateHistory.length,
      lastEntry:
        this.stateHistory.length > 0
          ? this.stateHistory[this.stateHistory.length - 1]
          : null,
    };
  }
}
