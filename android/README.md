# カスタマーサポートデモ - Android アプリ

Google Gemini Live API を使用したAI搭載カスタマーサポートのAndroidアプリです。

## 機能

- **音声対話**: マイクを使ったリアルタイム音声コミュニケーション
- **テキストチャット**: テキスト入力による問い合わせ
- **AI応答**: Gemini Live APIによる自然な会話
- **ツール機能**:
  - 返金処理 (`process_refund`)
  - 人的サポートへの転送 (`connect_to_human`)
  - 会話終了 (`end_conversation`)

## セットアップ

### 前提条件

- Android Studio Hedgehog (2023.1.1) 以降
- Android SDK API 26 以上
- JDK 11 以上

### ビルド手順

1. Android Studio でプロジェクトを開く
2. Gradle の同期を待つ
3. バックエンドサーバーを起動:
   ```bash
   cd ..  # プロジェクトルートへ
   python server.py
   ```
4. アプリを実行してサーバーURLを入力:
   - **エミュレータ**: `ws://10.0.2.2:8080`
   - **実機 (同一LAN)**: `ws://<サーバーIPアドレス>:8080`

## アーキテクチャ

```
android/app/src/main/kotlin/com/example/customersupport/
├── MainActivity.kt              # 起動画面（サーバーURL入力）
├── CustomerSupportActivity.kt   # メインチャット画面
├── WebSocketManager.kt          # WebSocket接続管理
├── AudioRecorder.kt             # マイク録音
├── AudioPlayer.kt               # 音声再生
├── model/
│   └── Message.kt               # メッセージデータクラス
└── adapter/
    └── MessageAdapter.kt        # RecyclerView アダプター
```

## 技術スタック

- **言語**: Kotlin
- **最低API**: 26 (Android 8.0)
- **ターゲットAPI**: 34 (Android 14)
- **ネットワーク**: OkHttp WebSocket
- **JSON**: Gson
- **UIコンポーネント**: Material Design 3
- **非同期処理**: Kotlin Coroutines
