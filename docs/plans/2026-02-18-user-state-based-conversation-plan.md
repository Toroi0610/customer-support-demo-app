# User State-Based Conversation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 映像分析後にユーザーの感情レベルを判断し、話しかけるべき時だけAIが話しかけるようにする。

**Architecture:** 新規 `UserStateManager` クラスがフロントエンドで感情履歴を保持・分類し、`evaluate()` で話しかけるべきか判断する。既存の `UserStateMonitor` と `VideoStreamer` のナッジ処理がこのマネージャーを経由するよう変更する。

**Tech Stack:** JavaScript (ES modules), React 19, Vite 7, Vitest (新規追加)

---

### Task 1: Set up test environment

**Files:**
- Modify: `package.json`
- Create: `vitest.config.js`

**Step 1: Install vitest**

Run: `npm install --save-dev vitest`

**Step 2: Create vitest config**

Create `vitest.config.js`:

```js
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
  },
});
```

**Step 3: Add test script to package.json**

Add to `scripts`: `"test": "vitest run"`

**Step 4: Verify setup**

Run: `npx vitest run`
Expected: No tests found (that's OK, confirms vitest works)

**Step 5: Commit**

```bash
git add package.json package-lock.json vitest.config.js
git commit -m "chore: add vitest for testing"
```

---

### Task 2: Create UserStateManager with emotion classification

**Files:**
- Create: `src/utils/user-state-manager.js`
- Create: `src/utils/__tests__/user-state-manager.test.js`

**Step 1: Write failing tests for emotion classification**

Create `src/utils/__tests__/user-state-manager.test.js`:

```js
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
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run src/utils/__tests__/user-state-manager.test.js`
Expected: FAIL — module not found

**Step 3: Write UserStateManager with emotion classification**

Create `src/utils/user-state-manager.js`:

```js
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
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run src/utils/__tests__/user-state-manager.test.js`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add src/utils/user-state-manager.js src/utils/__tests__/user-state-manager.test.js
git commit -m "feat: add UserStateManager with emotion classification"
```

---

### Task 3: Add evaluate() method — the core decision logic

**Files:**
- Modify: `src/utils/user-state-manager.js`
- Modify: `src/utils/__tests__/user-state-manager.test.js`

**Step 1: Write failing tests for evaluate()**

Append to test file:

```js
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
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run src/utils/__tests__/user-state-manager.test.js`
Expected: FAIL — evaluate is not a function

**Step 3: Implement evaluate() method**

Add to `UserStateManager` class in `src/utils/user-state-manager.js`:

```js
  /**
   * Evaluate an analysis result and decide whether the AI should speak.
   * @param {Object} analysis - Analysis result from frame analysis
   * @param {string} analysis.emotion - Detected emotion
   * @param {string} analysis.status_key - Status key
   * @param {string} analysis.observation - Observation text
   * @returns {{ shouldSpeak: boolean, level: string, reason: string }}
   */
  evaluate(analysis) {
    const emotion = analysis.emotion || "";
    const level = this.classifyEmotion(emotion);
    const now = Date.now();

    // Record in history
    this.emotionHistory.push({ emotion, level, timestamp: now, statusKey: analysis.status_key });
    if (this.emotionHistory.length > this.historyMaxLength) {
      this.emotionHistory.shift();
    }

    // First evaluation — always speak (greeting)
    if (this.isFirstEvaluation) {
      this.isFirstEvaluation = false;
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "initial" };
    }

    // HIGH — speak immediately
    if (level === "HIGH") {
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "high_emotion" };
    }

    // MEDIUM — speak if consecutive
    if (level === "MEDIUM") {
      const consecutiveCount = this._getConsecutiveMediumCount();
      if (consecutiveCount >= this.mediumConsecutiveThreshold) {
        this.lastSpokeAt = now;
        return { shouldSpeak: true, level, reason: "consecutive_medium" };
      }
      return { shouldSpeak: false, level, reason: "medium_not_consecutive" };
    }

    // LOW — speak if enough time has passed
    const elapsed = this.lastSpokeAt ? now - this.lastSpokeAt : Infinity;
    if (elapsed >= this.lowIntervalMs) {
      this.lastSpokeAt = now;
      return { shouldSpeak: true, level, reason: "low_interval" };
    }

    return { shouldSpeak: false, level, reason: "low_within_interval" };
  }

  /**
   * Count consecutive MEDIUM entries at the end of history.
   */
  _getConsecutiveMediumCount() {
    let count = 0;
    for (let i = this.emotionHistory.length - 1; i >= 0; i--) {
      if (this.emotionHistory[i].level === "MEDIUM") {
        count++;
      } else {
        break;
      }
    }
    return count;
  }
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run src/utils/__tests__/user-state-manager.test.js`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/utils/user-state-manager.js src/utils/__tests__/user-state-manager.test.js
git commit -m "feat: add evaluate() decision logic to UserStateManager"
```

---

### Task 4: Add shouldNudge() method for realtime video path

**Files:**
- Modify: `src/utils/user-state-manager.js`
- Modify: `src/utils/__tests__/user-state-manager.test.js`

**Step 1: Write failing tests for shouldNudge()**

Append to test file:

```js
describe("shouldNudge", () => {
  it("returns true when no emotion history (default to nudge)", () => {
    const manager = new UserStateManager();
    expect(manager.shouldNudge()).toBe(true);
  });

  it("returns true when current level is HIGH", () => {
    const manager = new UserStateManager();
    manager.evaluate({ emotion: "困っている", status_key: "troubled", observation: "test" });
    expect(manager.shouldNudge()).toBe(true);
  });

  it("returns true when current level is MEDIUM", () => {
    const manager = new UserStateManager();
    manager.isFirstEvaluation = false;
    manager.lastSpokeAt = Date.now();
    manager.evaluate({ emotion: "疲れている", status_key: "tired", observation: "test" });
    expect(manager.shouldNudge()).toBe(true);
  });

  it("returns false when current level is LOW and within interval", () => {
    const manager = new UserStateManager({ lowIntervalMs: 60000 });
    manager.isFirstEvaluation = false;
    manager.lastSpokeAt = Date.now();
    manager.evaluate({ emotion: "集中", status_key: "focused", observation: "test" });
    expect(manager.shouldNudge()).toBe(false);
  });

  it("returns true when current level is LOW but interval elapsed", () => {
    const manager = new UserStateManager({ lowIntervalMs: 60000 });
    manager.isFirstEvaluation = false;
    manager.lastSpokeAt = Date.now() - 70000;
    manager.evaluate({ emotion: "集中", status_key: "focused", observation: "test" });
    expect(manager.shouldNudge()).toBe(true);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run src/utils/__tests__/user-state-manager.test.js`
Expected: FAIL — shouldNudge is not a function

**Step 3: Implement shouldNudge()**

Add to `UserStateManager` class:

```js
  /**
   * Decide whether a realtime video nudge should be sent.
   * HIGH/MEDIUM: always nudge. LOW: only if interval has elapsed.
   */
  shouldNudge() {
    if (this.emotionHistory.length === 0) return true;

    const lastEntry = this.emotionHistory[this.emotionHistory.length - 1];
    if (lastEntry.level === "HIGH" || lastEntry.level === "MEDIUM") {
      return true;
    }

    // LOW — check interval
    const now = Date.now();
    const elapsed = this.lastSpokeAt ? now - this.lastSpokeAt : Infinity;
    return elapsed >= this.lowIntervalMs;
  }
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run src/utils/__tests__/user-state-manager.test.js`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/utils/user-state-manager.js src/utils/__tests__/user-state-manager.test.js
git commit -m "feat: add shouldNudge() for realtime video path control"
```

---

### Task 5: Integrate UserStateManager into UserStateMonitor

**Files:**
- Modify: `src/utils/user-monitor.js:7-35,150-175`

**Step 1: Import and instantiate UserStateManager in UserStateMonitor**

At top of `src/utils/user-monitor.js`, add import:

```js
import { UserStateManager } from "./user-state-manager.js";
```

In constructor, add after `this.stateHistory = [];`:

```js
    this.stateManager = new UserStateManager({
      lowIntervalMs: options.lowIntervalMs || 60000,
      mediumConsecutiveThreshold: options.mediumConsecutiveThreshold || 2,
    });
```

**Step 2: Replace direct onSignificantChange logic with StateManager evaluation**

In `_analyzeFrame()`, replace the block at lines 154-175 (from `const isFirst = ...` through `}`) with:

```js
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
```

**Step 3: Expose stateManager for nudge control**

Add a method to `UserStateMonitor`:

```js
  /**
   * Get the state manager instance (for external nudge control).
   */
  getStateManager() {
    return this.stateManager;
  }
```

**Step 4: Verify manually (build check)**

Run: `npx vite build`
Expected: Build succeeds with no errors

**Step 5: Commit**

```bash
git add src/utils/user-monitor.js
git commit -m "feat: integrate UserStateManager into UserStateMonitor"
```

---

### Task 6: Integrate nudge control into VideoStreamer

**Files:**
- Modify: `src/utils/media-utils.js:190-218`
- Modify: `src/components/LiveAPIDemo.jsx:439-451,527-584`

**Step 1: Add stateManager support to VideoStreamer**

In `media-utils.js`, modify `VideoStreamer` to accept a `shouldNudgeFn` callback. In the `start()` method options, add:

```js
this.shouldNudgeFn = options.shouldNudgeFn || null;
```

**Step 2: Use shouldNudgeFn in startCapturing()**

In `startCapturing()`, replace the nudge condition (lines 206-218) with:

```js
      // Overlay nudge text every N frames, but only if shouldNudgeFn allows it
      const shouldNudge = this.shouldNudgeFn ? this.shouldNudgeFn() : true;
      if (
        shouldNudge &&
        this.nudgeEveryNFrames > 0 &&
        this.nudgeText &&
        this.frameCount % this.nudgeEveryNFrames === 0
      ) {
        this.ctx.save();
        this.ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
        this.ctx.fillRect(0, this.canvas.height - 30, this.canvas.width, 30);
        this.ctx.fillStyle = "#ffffff";
        this.ctx.font = "16px sans-serif";
        this.ctx.fillText(this.nudgeText, 8, this.canvas.height - 9);
        this.ctx.restore();
      }
```

**Step 3: Connect in LiveAPIDemo.jsx**

In `toggleVideo()` (around line 447), pass `shouldNudgeFn` when starting the video streamer:

```js
const video = await videoStreamerRef.current.start({
  deviceId: selectedCamera,
  nudgeEveryNFrames: 10,
  nudgeText: "[report_visual_state] 映像の状況を報告してください",
  shouldNudgeFn: () => {
    if (userMonitorRef.current) {
      return userMonitorRef.current.getStateManager().shouldNudge();
    }
    return true; // Default: nudge if no monitor
  },
});
```

**Step 4: Pass lowIntervalMs to UserStateMonitor in toggleMonitoring()**

In `toggleMonitoring()` (around line 538), add options:

```js
const monitor = new UserStateMonitor({
  analysisUrl: "http://localhost:8081/analyze-frame",
  projectId: projectId,
  model: "gemini-2.0-flash",
  intervalMs: 5000,
  lowIntervalMs: 60000,
  mediumConsecutiveThreshold: 2,
  // ... rest of callbacks unchanged
});
```

**Step 5: Verify build**

Run: `npx vite build`
Expected: Build succeeds

**Step 6: Commit**

```bash
git add src/utils/media-utils.js src/components/LiveAPIDemo.jsx
git commit -m "feat: integrate nudge control into VideoStreamer and LiveAPIDemo"
```

---

### Task 7: Update system instructions

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx:57-83`

**Step 1: Update system instructions to reflect new behavior**

Replace the system instructions string (lines 57-83) to remove "every frame must report" language and add context about the state-based approach:

Key changes:
- Remove: `重要：映像の様子が変化するたびに、必ず "report_visual_state" ツールを呼び出してください`
- Add: `システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。指示が来ない間は、ユーザーが話しかけてきた時に自然に応答してください。`
- Keep all other instructions about being friendly, proactive on emotions, etc.

**Step 2: Verify build**

Run: `npx vite build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add src/components/LiveAPIDemo.jsx
git commit -m "feat: update system instructions for state-based conversation"
```

---

### Task 8: Manual integration test

**Step 1: Start the app**

Run: `npm run dev` (frontend) and `python server.py` (backend)

**Step 2: Verify behavior**

1. Connect to Gemini, turn on camera and monitoring
2. Sit normally (LOW) — AI should greet once, then be mostly quiet (talk at ~60s intervals)
3. Look confused/troubled — AI should speak up sooner
4. Return to normal — AI should quiet down again

**Step 3: Final commit if any adjustments needed**

```bash
git add -A
git commit -m "fix: adjustments from integration testing"
```
