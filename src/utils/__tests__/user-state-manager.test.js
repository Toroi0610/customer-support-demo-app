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
});
