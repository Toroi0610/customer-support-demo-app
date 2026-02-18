import { describe, it, expect } from "vitest";
import { UserStateManager } from "../user-state-manager.js";

describe("UserStateManager", () => {
  describe("classifyEmotion", () => {
    it("classifies 困っている as HIGH", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("困っている")).toBe("HIGH");
    });

    it("classifies 悲しい as HIGH", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("悲しい")).toBe("HIGH");
    });

    it("classifies 怒り as HIGH", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("怒り")).toBe("HIGH");
    });

    it("classifies 困惑 as MEDIUM", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("困惑")).toBe("MEDIUM");
    });

    it("classifies 疲れている as MEDIUM", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("疲れている")).toBe("MEDIUM");
    });

    it("classifies 笑顔 as LOW", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("笑顔")).toBe("LOW");
    });

    it("classifies 集中 as LOW", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("集中")).toBe("LOW");
    });

    it("classifies unknown emotions as LOW", () => {
      const manager = new UserStateManager();
      expect(manager.classifyEmotion("不明な感情")).toBe("LOW");
    });
  });

  describe("evaluate", () => {
    it("returns shouldSpeak: true on first evaluation", () => {
      const manager = new UserStateManager();
      const result = manager.evaluate({ emotion: "通常", status_key: "normal", observation: "test" });
      expect(result.shouldSpeak).toBe(true);
      expect(result.reason).toBe("initial");
    });

    it("returns shouldSpeak: true for HIGH emotions", () => {
      const manager = new UserStateManager();
      manager.isFirstEvaluation = false;
      manager.lastSpokeAt = Date.now();
      const result = manager.evaluate({ emotion: "困っている", status_key: "troubled", observation: "test" });
      expect(result.shouldSpeak).toBe(true);
      expect(result.level).toBe("HIGH");
    });

    it("returns shouldSpeak: false for single MEDIUM emotion", () => {
      const manager = new UserStateManager();
      manager.isFirstEvaluation = false;
      manager.lastSpokeAt = Date.now();
      const result = manager.evaluate({ emotion: "疲れている", status_key: "tired", observation: "test" });
      expect(result.shouldSpeak).toBe(false);
    });

    it("returns shouldSpeak: true for consecutive MEDIUM emotions", () => {
      const manager = new UserStateManager();
      manager.isFirstEvaluation = false;
      manager.lastSpokeAt = Date.now();
      // First MEDIUM
      manager.evaluate({ emotion: "疲れている", status_key: "tired", observation: "test" });
      // Second MEDIUM (consecutive)
      const result = manager.evaluate({ emotion: "疲れている", status_key: "tired", observation: "test" });
      expect(result.shouldSpeak).toBe(true);
      expect(result.reason).toBe("consecutive_medium");
    });

    it("returns shouldSpeak: false for LOW within interval", () => {
      const manager = new UserStateManager({ lowIntervalMs: 60000 });
      manager.isFirstEvaluation = false;
      manager.lastSpokeAt = Date.now();
      const result = manager.evaluate({ emotion: "集中", status_key: "focused", observation: "test" });
      expect(result.shouldSpeak).toBe(false);
    });

    it("returns shouldSpeak: true for LOW after interval elapsed", () => {
      const manager = new UserStateManager({ lowIntervalMs: 60000 });
      manager.isFirstEvaluation = false;
      manager.lastSpokeAt = Date.now() - 70000; // 70 seconds ago
      const result = manager.evaluate({ emotion: "集中", status_key: "focused", observation: "test" });
      expect(result.shouldSpeak).toBe(true);
      expect(result.reason).toBe("low_interval");
    });
  });
});
