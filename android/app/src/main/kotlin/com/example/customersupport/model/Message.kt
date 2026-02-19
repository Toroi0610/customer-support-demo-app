package com.example.customersupport.model

import java.util.Date

data class Message(
    val id: String = java.util.UUID.randomUUID().toString(),
    val content: String,
    val type: MessageType,
    val timestamp: Date = Date()
)

enum class MessageType {
    USER,       // ユーザーのメッセージ
    AGENT,      // AIエージェントのメッセージ
    SYSTEM,     // システムメッセージ（接続状態など）
    TOOL        // ツール実行結果
}
