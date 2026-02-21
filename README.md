# Customer Support Demo App

次世代カスタマーサポートエージェントのデモアプリケーションです。
Gemini Live API を活用したマルチモーダル対話・感情検出・メモリ管理機能を、
**ドメイン駆動設計 (DDD) 4層アーキテクチャ** で実装しています。

---

## 主な機能

- **マルチモーダル入力**: カメラ映像・マイク音声をリアルタイムで処理
- **感情検出**: ユーザーの表情・発話から感情レベル (HIGH / MEDIUM / LOW) を判定し、応答トーンを調整
- **会話メモリ**: 過去の会話を意味ベクトルで保存・想起し、継続的なサポートを実現
- **ペルソナ管理**: AIキャラクター設定をドメインオブジェクトとして管理
- **WebSocketプロキシ**: ブラウザ ↔ Gemini Live API 間の認証付き双方向通信

---

## アーキテクチャ

このプロジェクトは DDD に基づく4層構造を採用しています。詳細は [`ARCHITECTURE.md`](./ARCHITECTURE.md) を参照してください。

```
Presentation  →  Application  →  Domain  ←  Infrastructure
```

### Bounded Context（境界づけられたコンテキスト）

| コンテキスト | 責務 | 主要クラス |
|---|---|---|
| **Conversation** | 会話セッション管理・トランスクリプト | `Conversation`, `Message` |
| **Memory** | 過去会話の永続化・意味的な想起 | `MemoryRecord`, `MemoryRepository` |
| **UserObservation** | カメラ解析・感情検出・発話判断 | `UserObservation`, `EmotionLevel` |
| **Persona** | AIキャラクター設定管理 | `Persona`, `PersonaType` |

---

## プロジェクト構造

### バックエンド (Python)

```
domain/                            # Domain層 — エンティティ・値オブジェクト・インターフェース
├── conversation/
│   ├── conversation.py            # Conversation 集約
│   └── message.py                 # Message エンティティ
├── memory/
│   ├── memory_record.py           # MemoryRecord エンティティ
│   ├── emotion.py                 # Emotion 値オブジェクト
│   ├── importance.py              # Importance 値オブジェクト (0.0–1.0)
│   ├── memory_repository.py       # MemoryRepository 抽象インターフェース
│   └── memory_format_service.py   # MemoryFormatService ドメインサービス
├── user_observation/
│   ├── user_observation.py        # UserObservation エンティティ
│   ├── emotion_level.py           # EmotionLevel 列挙型 (HIGH/MEDIUM/LOW)
│   └── status_key.py              # StatusKey 値オブジェクト
└── persona/
    ├── persona.py                 # Persona エンティティ
    └── persona_type.py            # PersonaType 列挙型

application/                       # Application層 — ユースケース・DTO
├── dto.py                         # SaveMemoryRequest, AnalyzeFrameRequest 等
├── analyze_user_state.py          # AnalyzeUserStateUseCase
├── save_conversation_memory.py    # SaveConversationMemoryUseCase
└── recall_memories.py             # RecallMemoriesUseCase

infrastructure/                    # Infrastructure層 — 外部API・DB実装
├── google_auth.py                 # GoogleAuthService (ADC)
├── vertex_ai_embedding.py         # VertexAIEmbeddingService
├── chromadb_repository.py         # ChromaDBMemoryRepository (MemoryRepository 実装)
└── gemini_proxy.py                # GeminiProxy (WebSocket双方向プロキシ)

server.py                          # Presentation層 — HTTP/WebSocket ハンドラ
```

### フロントエンド (JavaScript / React)

```
src/
├── domain/                        # Domain層
│   ├── conversation/
│   │   ├── Conversation.js        # Conversation 集約
│   │   └── Message.js             # Message 値オブジェクト
│   ├── userState/
│   │   ├── EmotionLevel.js        # EmotionLevel 定数
│   │   ├── EmotionClassificationService.js
│   │   ├── SpeechDecisionService.js
│   │   └── UserObservation.js     # UserObservation エンティティ
│   ├── memory/
│   │   └── MemoryRecord.js        # MemoryRecord エンティティ
│   └── persona/
│       ├── Persona.js             # Persona エンティティ
│       └── PersonaType.js         # PersonaType 列挙型
│
├── application/                   # Application層
│   ├── ports/
│   │   ├── AIConversationPort.js  # AI通信インターフェース (Port)
│   │   └── MemoryPort.js          # メモリ操作インターフェース (Port)
│   └── useCases/
│       ├── StartConversationUseCase.js
│       ├── AnalyzeUserStateUseCase.js
│       └── SaveConversationMemoryUseCase.js
│
├── infrastructure/                # Infrastructure層
│   ├── ai/
│   │   └── GeminiLiveAPIAdapter.js  # AIConversationPort 実装
│   ├── api/
│   │   └── BackendAPIClient.js      # MemoryPort + HTTP クライアント
│   └── media/
│       ├── AudioStreamer.js
│       └── VideoStreamer.js
│
├── components/
│   └── LiveAPIDemo.jsx            # メインUIコンポーネント
│
└── utils/                         # レガシーコード（後方互換のため維持）
    ├── gemini-api.js
    ├── media-utils.js
    ├── tools.js
    └── user-state-manager.js
```

---

## セットアップ

### 前提条件

- Python 3.11+
- Node.js 18+
- Google Cloud プロジェクト（Vertex AI API 有効化済み）

### 1. バックエンド

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# Google Cloud 認証（ADC）
gcloud auth application-default login

# 環境変数の設定
cp .env.example .env
# .env を編集して GOOGLE_CLOUD_PROJECT 等を設定

# プロキシサーバーの起動
python server.py
```

### 2. フロントエンド

別ターミナルで起動してください。

```bash
# 依存パッケージのインストール
npm install

# 開発サーバーの起動
npm run dev
```

ブラウザで [http://localhost:5173](http://localhost:5173) を開いてください。

---

## 設定項目

| 項目 | デフォルト値 | 説明 |
|---|---|---|
| Google Cloud Project ID | — | Google Cloud プロジェクトID |
| Proxy URL | `ws://localhost:8080` | バックエンドWebSocket URL |
| Model ID | 最新のGemini Liveプレビュー | 使用するGeminiモデル |
| Voice | — | エージェントの音声設定 |
| Affective Dialog | 有効 | 感情検出・共感応答の有効化 |

---

## 開発ガイド

コーディング規則・レイヤー規則・命名規則は [`CLAUDE.md`](./CLAUDE.md) に記載しています。
新機能を追加する際は必ず参照してください。

### テスト

```bash
# Pythonテスト
pytest

# JavaScriptテスト
npm run test
```

### デプロイ

```bash
# バックエンド（Cloud Run）
./deploy-backend.sh

# フロントエンド（Firebase Hosting）
./deploy-frontend.sh
```

---

## 技術スタック

| 分類 | 技術 |
|---|---|
| フロントエンド | React 19, Vite 7 |
| バックエンド | Python (aiohttp, websockets) |
| AI | Gemini Live API (Google Cloud Vertex AI) |
| ベクトルDB | ChromaDB |
| 埋め込みモデル | Vertex AI Embedding |
| 認証 | Google Application Default Credentials (ADC) |
| テスト | Vitest (JS), pytest (Python) |
