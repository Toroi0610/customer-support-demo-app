# アーキテクチャ設計 (DDD)

このプロジェクトはドメイン駆動設計 (DDD) に基づいて整理されています。

---

## レイヤー構成

```
┌─────────────────────────────────────────────────────────────────┐
│  Presentation Layer  (UI / API Handlers)                        │
│  src/presentation/  ·  server.py (HTTP/WS handlers)            │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer  (Use Cases / DTOs)                         │
│  src/application/   ·  application/                            │
├─────────────────────────────────────────────────────────────────┤
│  Domain Layer  (Entities / Value Objects / Domain Services)     │
│  src/domain/        ·  domain/                                 │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure Layer  (DB / AI / External APIs)               │
│  src/infrastructure/ · infrastructure/                         │
└─────────────────────────────────────────────────────────────────┘
```

各レイヤーは **内側のレイヤーのみ** に依存します。外側のレイヤーを参照してはいけません。

---

## バックエンド (Python)

```
domain/
├── conversation/
│   ├── message.py              # Message エンティティ (role, text)
│   └── conversation.py         # Conversation 集約 (メッセージ + 感情イベント)
├── memory/
│   ├── memory_record.py        # MemoryRecord エンティティ
│   ├── emotion.py              # Emotion 値オブジェクト
│   ├── importance.py           # Importance 値オブジェクト (0.0–1.0)
│   ├── memory_repository.py    # MemoryRepository 抽象インターフェース
│   └── memory_format_service.py# MemoryFormatService ドメインサービス
├── user_observation/
│   ├── user_observation.py     # UserObservation エンティティ
│   ├── emotion_level.py        # EmotionLevel 列挙型 (HIGH/MEDIUM/LOW)
│   └── status_key.py           # StatusKey 値オブジェクト
└── persona/
    ├── persona.py              # Persona エンティティ
    └── persona_type.py         # PersonaType 列挙型

application/
├── dto.py                      # DTO定義 (SaveMemoryRequest, AnalyzeFrameRequest 等)
├── analyze_user_state.py       # AnalyzeUserStateUseCase
├── save_conversation_memory.py # SaveConversationMemoryUseCase
└── recall_memories.py          # RecallMemoriesUseCase

infrastructure/
├── google_auth.py              # GoogleAuthService (ADC)
├── vertex_ai_embedding.py      # VertexAIEmbeddingService
├── chromadb_repository.py      # ChromaDBMemoryRepository (MemoryRepository実装)
└── gemini_proxy.py             # GeminiProxy (WebSocket双方向プロキシ)

server.py                       # エントリポイント (HTTP/WS ルーティング)
memory-mcp/                     # 既存のメモリMCPサーバー (後方互換)
```

---

## フロントエンド (JavaScript / React)

```
src/
├── domain/
│   ├── conversation/
│   │   ├── Message.js                      # Message 値オブジェクト
│   │   └── Conversation.js                 # Conversation 集約
│   ├── userState/
│   │   ├── EmotionLevel.js                 # EmotionLevel 定数
│   │   ├── EmotionClassificationService.js # 感情分類ドメインサービス
│   │   ├── SpeechDecisionService.js        # 発話判断ドメインサービス
│   │   └── UserObservation.js              # UserObservation エンティティ
│   ├── memory/
│   │   └── MemoryRecord.js                 # MemoryRecord エンティティ
│   └── persona/
│       ├── PersonaType.js                  # PersonaType 定数
│       └── Persona.js                      # Persona エンティティ
│
├── application/
│   ├── ports/
│   │   ├── AIConversationPort.js           # AI通信インターフェース (Port)
│   │   └── MemoryPort.js                   # メモリ操作インターフェース (Port)
│   └── useCases/
│       ├── StartConversationUseCase.js     # 会話セッション開始
│       ├── AnalyzeUserStateUseCase.js      # フレーム解析 + 発話判断
│       └── SaveConversationMemoryUseCase.js# 会話をメモリとして保存
│
├── infrastructure/
│   ├── ai/
│   │   └── GeminiLiveAPIAdapter.js         # AIConversationPort 実装
│   ├── media/
│   │   ├── AudioStreamer.js                # マイク取得 (media-utils.js のre-export)
│   │   └── VideoStreamer.js                # カメラフレーム取得 (re-export)
│   └── api/
│       └── BackendAPIClient.js             # MemoryPort + HTTP クライアント
│
├── presentation/
│   └── (今後コンポーネント分割予定)
│
└── utils/                                  # 既存ユーティリティ (後方互換)
    ├── gemini-api.js
    ├── media-utils.js
    ├── tools.js
    ├── user-state-manager.js
    └── user-monitor.js
```

---

## 境界づけられたコンテキスト (Bounded Contexts)

| コンテキスト | 責務 | 主な集約/エンティティ |
|---|---|---|
| **Conversation** | 会話セッション管理・トランスクリプト | Conversation, Message |
| **Memory** | 過去会話の永続化・想起 | MemoryRecord, Emotion, Importance |
| **UserObservation** | カメラフレーム解析・感情検出 | UserObservation, EmotionLevel, StatusKey |
| **Persona** | AIキャラクター設定管理 | Persona, PersonaType |

---

## 依存の方向

```
server.py / React Components
        ↓
  Application (Use Cases)
        ↓
     Domain (純粋)
        ↑
  Infrastructure (具体実装)
```

- **Domain** は他のどのレイヤーにも依存しない（Python標準ライブラリのみ）
- **Application** は Domain インターフェース (Repository, Port) に依存
- **Infrastructure** は Domain インターフェースを実装し、外部サービスを呼ぶ
- **Presentation** はユースケースを呼び出すが、Domain に直接触らない

---

## 主要な設計パターン

| パターン | 実装例 |
|---|---|
| **Repository** | `MemoryRepository` (抽象) → `ChromaDBMemoryRepository` (具体) |
| **Port & Adapter** | `AIConversationPort` → `GeminiLiveAPIAdapter` |
| **Use Case (Interactor)** | `AnalyzeUserStateUseCase`, `SaveConversationMemoryUseCase` |
| **Value Object** | `EmotionLevel`, `StatusKey`, `Importance`, `PersonaType` |
| **Aggregate Root** | `Conversation` (メッセージ + 感情イベントを管理) |
| **Domain Service** | `EmotionClassificationService`, `MemoryFormatService` |
