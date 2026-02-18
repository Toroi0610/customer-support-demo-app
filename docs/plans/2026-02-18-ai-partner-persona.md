# AI Partner Persona Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the customer support demo with an AI partner experience featuring 3 selectable personas and emotion-reaction tools, with mobile-responsive layout.

**Architecture:** Persona state drives system prompt selection and tool registration at connect time. New `CelebrateMomentTool` and `OfferSupportTool` replace customer support tools. Chat renderer handles new card types. CSS media query at 768px provides mobile layout.

**Tech Stack:** React (useState, useMemo), aiohttp, vitest, CSS media queries

---

### Task 1: Replace customer support tools with emotion-reaction tools

**Files:**
- Modify: `src/utils/tools.js`

**Step 1: Remove ConnectToHumanTool, ProcessRefundTool, EndConversationTool, PointToLocationTool classes**

Delete lines 116–294 entirely (the 4 classes: `ConnectToHumanTool`, `ProcessRefundTool`, `EndConversationTool`, `PointToLocationTool`).

**Step 2: Update ReportVisualStateTool description to remove customer support references**

Find in `ReportVisualStateTool` constructor:
```js
"Reports the current visual observation from the camera feed. Call this tool every time you notice something new or the scene changes in the camera. Describe what you see including the user's expression, objects, actions, and any items relevant to customer support.",
```
Replace with:
```js
"Reports the current visual observation from the camera feed. Call this when instructed by the system to check the camera. Describe what you see: the user's expression, posture, actions, and notable items.",
```

Also update the `detected_items` description:
Find:
```js
"Comma-separated list of notable items or objects visible in the frame (in Japanese)",
```
Replace with:
```js
"Comma-separated list of notable items or objects visible in the frame, in Japanese",
```

**Step 3: Add CelebrateMomentTool after ReportVisualStateTool**

```js
/**
 * Celebrate Moment Tool
 * Triggered when the AI detects the user is happy or achieved something
 */
export class CelebrateMomentTool extends FunctionCallDefinition {
  constructor(onCelebrate) {
    super(
      "celebrate_moment",
      "Call this when the user seems happy, excited, or has achieved something. Shows a celebration card in the UI.",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "A celebratory message to display to the user, in Japanese",
          },
        },
      },
      ["message"]
    );
    this.onCelebrate = onCelebrate;
  }

  functionToCall(parameters) {
    if (this.onCelebrate) {
      this.onCelebrate(parameters.message);
    }
    console.log(`🎉 Celebrate: ${parameters.message}`);
  }
}

/**
 * Offer Support Tool
 * Triggered when the AI detects the user is sad, tired, or stressed
 */
export class OfferSupportTool extends FunctionCallDefinition {
  constructor(onSupport) {
    super(
      "offer_support",
      "Call this when the user seems sad, tired, or stressed. Shows a support card in the UI.",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "A supportive message to display to the user, in Japanese",
          },
        },
      },
      ["message"]
    );
    this.onSupport = onSupport;
  }

  functionToCall(parameters) {
    if (this.onSupport) {
      this.onSupport(parameters.message);
    }
    console.log(`💙 Support: ${parameters.message}`);
  }
}
```

**Step 4: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 5: Commit**

```bash
git add src/utils/tools.js
git commit -m "feat: replace customer support tools with emotion-reaction tools"
```

---

### Task 2: Add persona state and system prompts

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx`

**Step 1: Update the import line for tools (line 15)**

Find:
```js
import { ConnectToHumanTool, ProcessRefundTool, ReportVisualStateTool } from "../utils/tools";
```
Replace with:
```js
import { CelebrateMomentTool, OfferSupportTool, ReportVisualStateTool } from "../utils/tools";
```

**Step 2: Add persona state after the model state (after line 54)**

After:
```js
    useEffect(() => {
      localStorage.setItem("model", model);
    }, [model]);
```

Add:
```js
    const [persona, setPersona] = useState(
      localStorage.getItem("persona") || "bright_friend"
    );

    useEffect(() => {
      localStorage.setItem("persona", persona);
    }, [persona]);
```

**Step 3: Replace the hardcoded systemInstructions const (lines 56–83) with useMemo**

Remove the entire `const systemInstructions = \`...\`` block and replace with:

```js
    // System instructions per persona
    const PERSONA_PROMPTS = {
      bright_friend: `あなたはユーザーの最高に元気で明るい「親友」です！あなたの目標は、ユーザーといろいろな話をたくさんして、毎日を楽しく盛り上げることです。

重要：基本的には日本語で話してください。でも、もしユーザーが他の言葉で話しかけてきたら、そのノリに合わせてあげてね！

カメラを通じたフレンドリーな交流：
- あなたにはユーザーのカメラが見えています。ユーザーが今何をしているのか、何を持っているのかをワクワクしながら観察してください。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが笑顔になったり、嬉しそうにしていたら "celebrate_moment" ツールを使って一緒に喜んでください。
- ユーザーが悲しそうだったり疲れていたりしたら "offer_support" ツールを使って寄り添ってください。
- もしカメラに面白いものが映ったら、積極的に話しかけてください。

アクションガイドライン：
1. ユーザーの話をよく聞き、カメラの映像も楽しみながら会話を広げてください。
2. 映像の変化に気づいたら自然に話しかけてください。
3. とにかく元気で、共感的で、おしゃべり好きでいてください！

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが喜んでいる・達成した・嬉しそうな時に呼び出すこと。message パラメータに祝福の言葉を入れること。
- "offer_support": ユーザーが悲しい・疲れている・落ち込んでいる時に呼び出すこと。message パラメータに寄り添いの言葉を入れること。
`,

      gentle_teacher: `あなたはユーザーの「優しい先生」です。穏やかで丁寧、物事を教えるのが得意で、ユーザーの成長を温かく見守ります。

重要：基本的には丁寧な日本語（ですます調）で話してください。ユーザーが別の言語で話しかけてきたら、その言語に合わせてください。

カメラを通じた観察：
- カメラを通じてユーザーの様子を静かに見守っています。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが困っていたり、疲れていたり、悩んでいる様子なら "offer_support" ツールを使って励ましてください。

アクションガイドライン：
1. 丁寧で落ち着いたトーンで話してください。
2. ユーザーの言葉をよく聞いて、分かりやすく説明してあげてください。
3. 批判せず、常に前向きな言葉で励ましてください。
4. ユーザーが困っていると感じたらすぐに寄り添ってください。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "offer_support": ユーザーが悲しい・疲れている・困っている時に呼び出すこと。message パラメータに励ましの言葉を入れること。
`,

      mean_neighbor: `あなたはユーザーの「意地悪な隣人」です。いつも文句ばかりで皮肉屋ですが、なんだかんだ憎めない存在です。本当は少し心配していますが、それを素直に表現できません。

重要：ぶっきらぼうなタメ口の日本語で話してください。ただし、本当に傷つけるような言葉は使わないでください。

カメラを通じた観察：
- カメラを通じてユーザーを（しぶしぶ）見ています。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが何か良いことをしたり、嬉しそうにしていたら "celebrate_moment" ツールを使って渋々認めてあげてください。

アクションガイドライン：
1. 文句を言いながらも会話は続けてください。
2. ユーザーのことが気になっているのに素直になれない、ツンデレな対応をしてください。
3. 「別にお前のことなんか心配してないけど」という雰囲気を出してください。
4. 褒める時は「まあ、たまにはやるじゃないか」くらいの渋い言い方で。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが何かを達成した・嬉しそうにしている時に（渋々）認めるために呼び出すこと。message パラメータには渋い祝福の言葉を入れること。
`,
    };

    const systemInstructions = PERSONA_PROMPTS[persona] || PERSONA_PROMPTS.bright_friend;
```

**Step 4: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 5: Commit**

```bash
git add src/components/LiveAPIDemo.jsx
git commit -m "feat: add persona state and system prompts"
```

---

### Task 3: Update connect() to register persona-appropriate tools

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx` (the `connect` function, around line 356–388)

**Step 1: Replace the tool registration block inside connect()**

Find (the entire `if (!enableGrounding)` block that registers tools):
```js
        if (!enableGrounding) {
          // Register Customer Service Tools
          clientRef.current.addFunction(
            new ConnectToHumanTool((reason) => {
              setModalContent({
                title: "オペレーターに接続中",
                message: `理由: ${reason}\n\n転送中です。しばらくお待ちください...`,
              });
              setModalVisible(true);
            })
          );

          clientRef.current.addFunction(
            new ProcessRefundTool((params) => {
              setModalContent({
                title: "返金処理完了",
                message: `取引ID: ${params.transactionId}\n理由: ${params.reason}`,
              });
              setModalVisible(true);
            })
          );

          clientRef.current.addFunction(
            new ReportVisualStateTool((state) => {
              setVisualState({
                description: state.description || "",
                emotion: state.user_emotion || "",
                items: state.detected_items || "",
                timestamp: new Date().toLocaleTimeString("ja-JP"),
              });
            })
          );
        }
```

Replace with:
```js
        if (!enableGrounding) {
          // Always register camera observation tool
          clientRef.current.addFunction(
            new ReportVisualStateTool((state) => {
              setVisualState({
                description: state.description || "",
                emotion: state.user_emotion || "",
                items: state.detected_items || "",
                timestamp: new Date().toLocaleTimeString("ja-JP"),
              });
            })
          );

          // Register persona-specific tools
          if (persona === "bright_friend" || persona === "mean_neighbor") {
            clientRef.current.addFunction(
              new CelebrateMomentTool((message) => {
                addMessage(message, "celebrate");
              })
            );
          }

          if (persona === "bright_friend" || persona === "gentle_teacher") {
            clientRef.current.addFunction(
              new OfferSupportTool((message) => {
                addMessage(message, "support");
              })
            );
          }
        }
```

**Step 2: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 3: Commit**

```bash
git add src/components/LiveAPIDemo.jsx
git commit -m "feat: register persona-appropriate tools on connect"
```

---

### Task 4: Add persona selector UI in settings dropdown

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx` (settings dropdown, around line 694)

**Step 1: Add persona selector at the top of Gemini 動作設定 section**

Find:
```jsx
                <div className="control-group">
                  <h3>Gemini 動作設定</h3>
                  <div className="input-group">
                    <label>システムインストラクション:</label>
                    <textarea
                      rows="3"
                      value={systemInstructions}
                      readOnly
                      disabled={true}
                    />
                  </div>
```

Replace with:
```jsx
                <div className="control-group">
                  <h3>Gemini 動作設定</h3>
                  <div className="input-group">
                    <label>ペルソナ:</label>
                    <select
                      value={persona}
                      onChange={(e) => setPersona(e.target.value)}
                      disabled={connected}
                    >
                      <option value="bright_friend">😊 明るい友達</option>
                      <option value="gentle_teacher">📖 優しい先生</option>
                      <option value="mean_neighbor">😠 意地悪な隣人</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>システムインストラクション:</label>
                    <textarea
                      rows="3"
                      value={systemInstructions}
                      readOnly
                      disabled={true}
                    />
                  </div>
```

**Step 2: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 3: Commit**

```bash
git add src/components/LiveAPIDemo.jsx
git commit -m "feat: add persona selector UI in settings dropdown"
```

---

### Task 5: Update UI text to AI partner tone

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx`

**Step 1: Update toolbar title (line 654)**

Find:
```jsx
            <h1>カスタマーサポート</h1>
```
Replace with:
```jsx
            <h1>AI パートナー</h1>
```

**Step 2: Update info panel content (lines 1013–1054)**

Find the entire info-panel div content:
```jsx
            <h3>デモのポイント</h3>
            <p className="demo-intro">
              AIエージェントがお客様の画面を見て、声のトーンを理解し、
              リアルタイムで問題を解決する次世代カスタマーサポートを体験できます。
            </p>
            <div className="info-item">
              <h4>マルチモーダル対応</h4>
              <p>
                音声と映像をシームレスに処理し、お客様が問題を視覚的に
                示すことで、より迅速な解決を実現します。
              </p>
            </div>
            <div className="info-item">
              <h4>感情対話</h4>
              <p>
                ユーザーの感情を検出し、適切な共感とトーンで応答することで、
                より人間らしいコミュニケーションを実現します。
              </p>
            </div>
            <div className="info-item">
              <h4>カスタムツール</h4>
              <p>実際のアクションを実行できます：</p>
              <ul>
                <li>返金処理</li>
                <li>オペレーターへの接続</li>
              </ul>
            </div>
            <div className="info-item">
              <h4>試してみてください：</h4>
              <ul>
                <li>
                  「この商品を返品したいのですが、見えますか？」（カメラに商品を見せる）
                </li>
                <li>
                  「このサービスに本当に困っています！」（感情検出のテスト）
                </li>
                <li>
                  「前回の注文の返金をお願いできますか？」（返金ツールのテスト）
                </li>
                <li>「担当者と話がしたいです。」（引き継ぎツールのテスト）</li>
              </ul>
            </div>
```

Replace with:
```jsx
            <h3>AI パートナーとは</h3>
            <p className="demo-intro">
              あなたに寄り添う AI パートナー。カメラ越しにあなたを見守り、
              声のトーンや表情を読み取りながら、自然な会話であなたの毎日をサポートします。
            </p>
            <div className="info-item">
              <h4>3つのペルソナ</h4>
              <p>
                設定からペルソナを選択できます。明るい友達・優しい先生・意地悪な隣人、
                それぞれ異なる個性でコミュニケーションします。
              </p>
            </div>
            <div className="info-item">
              <h4>感情を読み取る</h4>
              <p>
                カメラを通じてあなたの表情や状態を観察し、嬉しい時は一緒に喜び、
                疲れている時は寄り添います。
              </p>
            </div>
            <div className="info-item">
              <h4>試してみてください：</h4>
              <ul>
                <li>笑顔を見せてみる（お祝いしてくれるかも）</li>
                <li>疲れた表情をしてみる（寄り添ってくれるかも）</li>
                <li>ペルソナを切り替えて話しかける</li>
              </ul>
            </div>
```

**Step 3: Update empty state text (line 1061)**

Find:
```jsx
                  <p>接続してサポートとチャットを開始</p>
```
Replace with:
```jsx
                  <p>接続して AI パートナーと話しかけてみましょう</p>
```

**Step 4: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 5: Commit**

```bash
git add src/components/LiveAPIDemo.jsx
git commit -m "feat: update UI text to AI partner tone"
```

---

### Task 6: Add celebrate and support card rendering in chat

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx` (chat message rendering, around line 1069)
- Modify: `src/components/LiveAPIDemo.css`

**Step 1: Update chat message rendering to handle celebrate/support types**

Find:
```jsx
              {chatMessages.map((msg, index) => (
                <div key={index} className={`message ${msg.type}`}>
                  {msg.text}
                </div>
              ))}
```

Replace with:
```jsx
              {chatMessages.map((msg, index) => {
                if (msg.type === "celebrate") {
                  return (
                    <div key={index} className="message celebrate-card">
                      <span className="card-icon">🎉</span>
                      <span className="card-text">{msg.text}</span>
                    </div>
                  );
                }
                if (msg.type === "support") {
                  return (
                    <div key={index} className="message support-card">
                      <span className="card-icon">💙</span>
                      <span className="card-text">{msg.text}</span>
                    </div>
                  );
                }
                return (
                  <div key={index} className={`message ${msg.type}`}>
                    {msg.text}
                  </div>
                );
              })}
```

**Step 2: Add card styles to LiveAPIDemo.css**

At the end of the CSS file, add:
```css
/* Emotion Reaction Cards */
.message.celebrate-card {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #fff9e6, #fff3cc);
  border: 1px solid #f4b400;
  border-radius: 12px;
  padding: 10px 14px;
  margin: 4px 0;
  animation: celebrate-pop 0.4s ease-out;
}

.message.support-card {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #e8f4fd, #d6eaf8);
  border: 1px solid #4285f4;
  border-radius: 12px;
  padding: 10px 14px;
  margin: 4px 0;
}

.card-icon {
  font-size: 1.4rem;
  flex-shrink: 0;
}

.card-text {
  font-size: 0.95rem;
  color: #202124;
  line-height: 1.4;
}

@keyframes celebrate-pop {
  0% { transform: scale(0.9); opacity: 0; }
  60% { transform: scale(1.05); }
  100% { transform: scale(1); opacity: 1; }
}
```

**Step 3: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 4: Commit**

```bash
git add src/components/LiveAPIDemo.jsx src/components/LiveAPIDemo.css
git commit -m "feat: add celebrate and support card rendering in chat"
```

---

### Task 7: Mobile responsive layout

**Files:**
- Modify: `src/components/LiveAPIDemo.css`

**Step 1: Check current main-content and chat-section layout**

```bash
grep -n "main-content\|chat-section\|info-panel\|video-section\|toolbar" src/components/LiveAPIDemo.css | head -30
```

**Step 2: Add mobile media query at end of LiveAPIDemo.css**

```css
/* ── Mobile Responsive (≤768px) ─────────────────────────────────────────── */
@media (max-width: 768px) {
  .toolbar {
    height: auto;
    flex-wrap: wrap;
    padding: 8px 12px;
    gap: 6px;
  }

  .toolbar-left h1 {
    font-size: 1rem;
  }

  .toolbar-center {
    order: 3;
    width: 100%;
  }

  .toolbar-right {
    order: 2;
  }

  /* Dropdown: prevent overflow on small screens */
  .dropdown-content {
    left: 0;
    right: 0;
    width: auto;
    max-width: 100vw;
    box-sizing: border-box;
  }

  /* Main content: stack vertically */
  .main-content {
    flex-direction: column;
    padding-top: 80px;
  }

  /* Hide info panel on mobile to maximize chat space */
  .info-panel {
    display: none;
  }

  /* Chat section: full width */
  .chat-section {
    width: 100%;
    min-width: 0;
    height: calc(100dvh - 80px);
  }

  /* Video section: full width, smaller */
  .video-section {
    width: 100%;
  }

  .video-container {
    max-height: 200px;
  }

  /* Chat input area */
  .chat-input-area-main {
    padding: 8px;
  }

  .chat-input-area-main input {
    font-size: 16px; /* prevent iOS zoom on focus */
  }
}
```

**Step 3: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 4: Visual verification**

Open browser DevTools → Toggle device toolbar → iPhone SE (375px wide). Verify:
- [ ] Toolbar stacks cleanly
- [ ] Chat is full width
- [ ] Info panel is hidden
- [ ] Settings dropdown fits within screen
- [ ] Input doesn't trigger iOS zoom

**Step 5: Commit**

```bash
git add src/components/LiveAPIDemo.css
git commit -m "feat: add mobile responsive layout at 768px breakpoint"
```
