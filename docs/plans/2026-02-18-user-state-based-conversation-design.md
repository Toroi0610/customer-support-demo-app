# User State-Based Conversation Design

## Overview

映像確認後、ユーザーの状態を内部で保持し、話しかけるべき状態かどうかを判断してから話しかける仕組みを導入する。

## Current Behavior

- 5秒ごとの監視パスで状態変化を検知 → 即座にAIが話しかける
- 10フレームごとのリアルタイムナッジ → AIが毎回映像について報告・話す
- 初回検知 → 必ず挨拶

## Desired Behavior

- 映像分析結果をUserStateManagerで評価し、感情レベルに応じて話しかけるかどうかを判断
- HIGH（困っている・悲しい・怒り）→ 即座に話しかける
- MEDIUM（困惑・疲労）→ 連続検知で話しかける
- LOW（集中・通常・笑顔）→ 一定間隔ごとに軽く声かけ

## Architecture

```
現状:  映像分析 → 変化検知 → 即座にAIに通知
変更後: 映像分析 → 変化検知 → UserStateManager（判断） → 必要な時だけAIに通知
```

### Emotion Levels

| Level | Emotions | Action |
|-------|----------|--------|
| HIGH | 困っている、悲しい、怒り、泣いている | 即座に話しかける |
| MEDIUM | 困惑、疲れている、不安 | 2回連続で同じなら話しかける |
| LOW | 集中、通常、笑顔、作業中 | 60秒間隔で軽く声かけ |

### Changes

1. **New: `src/utils/user-state-manager.js`** — 状態保持・判断ロジック
2. **Modified: `user-monitor.js`** — onSignificantChangeの前にStateManagerを経由
3. **Modified: `LiveAPIDemo.jsx`** — StateManagerの初期化・接続、ナッジの制御
4. **Modified: System instructions** — 「毎回必ず報告」→「指示があった時に報告」に変更

### UserStateManager Responsibilities

- 感情の履歴を保持（直近N件）
- 現在の感情をHIGH/MEDIUM/LOWに分類
- HIGHなら即 shouldSpeak=true
- MEDIUMなら連続検知で shouldSpeak=true
- LOWなら最後に話しかけてからの経過時間で判断
- リアルタイムパスのナッジもLOWの時は間引く

### Data Flow

```
[5秒監視] → analysis → StateManager.evaluate(analysis)
  → shouldSpeak: true  → onSignificantChange → AI話しかける
  → shouldSpeak: false → onStateUpdate のみ（UI更新、AIは黙る）

[リアルタイム映像ナッジ] → StateManager.shouldNudge()
  → true  → ナッジテキスト付きで送信
  → false → ナッジなしで送信（またはスキップ）
```

## Decisions

- 判断ロジックはフロントエンドに配置（レイテンシ低減）
- 感情変化ベースで判断（状態遷移ではなく感情レベル重視）
- LOW状態でもたまに軽く声かけ（完全に黙らない）
