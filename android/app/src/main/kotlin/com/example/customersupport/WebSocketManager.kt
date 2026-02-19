package com.example.customersupport

import android.util.Base64
import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.util.concurrent.TimeUnit

class WebSocketManager(
    private val serverUrl: String,
    private val listener: WebSocketListener2
) {
    companion object {
        private const val TAG = "WebSocketManager"
    }

    private var webSocket: WebSocket? = null
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    fun connect() {
        val request = Request.Builder()
            .url(serverUrl)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected")
                listener.onConnected()
                sendSetupMessage()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "Received text: $text")
                handleMessage(text)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                Log.d(TAG, "Received bytes: ${bytes.size()}")
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closing: $code $reason")
                webSocket.close(1000, null)
                listener.onDisconnected(reason)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure: ${t.message}")
                listener.onError(t.message ?: "Unknown error")
            }
        })
    }

    private fun sendSetupMessage() {
        // Gemini Live APIのセットアップメッセージを送信
        val setupMessage = JsonObject().apply {
            add("setup", JsonObject().apply {
                addProperty("model", "models/gemini-2.0-flash-live-001")
                add("generation_config", JsonObject().apply {
                    addProperty("response_modalities", "text")
                    addProperty("speech_config", "")
                })
                add("system_instruction", JsonObject().apply {
                    add("parts", com.google.gson.JsonArray().apply {
                        add(JsonObject().apply {
                            addProperty("text", buildSystemPrompt())
                        })
                    })
                })
            })
        }
        webSocket?.send(gson.toJson(setupMessage))
    }

    private fun buildSystemPrompt(): String {
        return """あなたは親切なカスタマーサポートエージェントです。
お客様の問題を丁寧に解決してください。

対応できる業務:
- 商品に関する質問
- 返金・返品の手続き
- 注文状況の確認
- クレームの受付
- 一般的なお問い合わせ

常に丁寧で、共感的な対応を心がけてください。"""
    }

    fun sendTextMessage(text: String) {
        val message = JsonObject().apply {
            add("client_content", JsonObject().apply {
                add("turns", com.google.gson.JsonArray().apply {
                    add(JsonObject().apply {
                        addProperty("role", "user")
                        add("parts", com.google.gson.JsonArray().apply {
                            add(JsonObject().apply {
                                addProperty("text", text)
                            })
                        })
                    })
                })
                addProperty("turn_complete", true)
            })
        }
        webSocket?.send(gson.toJson(message))
    }

    fun sendAudioChunk(audioData: ByteArray) {
        val base64Audio = Base64.encodeToString(audioData, Base64.NO_WRAP)
        val message = JsonObject().apply {
            add("realtime_input", JsonObject().apply {
                add("media_chunks", com.google.gson.JsonArray().apply {
                    add(JsonObject().apply {
                        addProperty("mime_type", "audio/pcm;rate=16000")
                        addProperty("data", base64Audio)
                    })
                })
            })
        }
        webSocket?.send(gson.toJson(message))
    }

    private fun handleMessage(text: String) {
        try {
            val json = JsonParser.parseString(text).asJsonObject

            when {
                json.has("setupComplete") -> {
                    listener.onSetupComplete()
                }
                json.has("serverContent") -> {
                    val serverContent = json.getAsJsonObject("serverContent")
                    if (serverContent.has("modelTurn")) {
                        val modelTurn = serverContent.getAsJsonObject("modelTurn")
                        if (modelTurn.has("parts")) {
                            val parts = modelTurn.getAsJsonArray("parts")
                            for (part in parts) {
                                val partObj = part.asJsonObject
                                if (partObj.has("text")) {
                                    val textContent = partObj.get("text").asString
                                    listener.onTextReceived(textContent)
                                } else if (partObj.has("inlineData")) {
                                    val inlineData = partObj.getAsJsonObject("inlineData")
                                    val mimeType = inlineData.get("mimeType").asString
                                    val data = inlineData.get("data").asString
                                    if (mimeType.startsWith("audio/")) {
                                        val audioBytes = Base64.decode(data, Base64.NO_WRAP)
                                        listener.onAudioReceived(audioBytes)
                                    }
                                }
                            }
                        }
                    }
                    if (serverContent.has("turnComplete") && serverContent.get("turnComplete").asBoolean) {
                        listener.onTurnComplete()
                    }
                }
                json.has("toolCall") -> {
                    val toolCall = json.getAsJsonObject("toolCall")
                    listener.onToolCall(toolCall)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing message: ${e.message}")
        }
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
    }
}

interface WebSocketListener2 {
    fun onConnected()
    fun onDisconnected(reason: String)
    fun onError(error: String)
    fun onSetupComplete()
    fun onTextReceived(text: String)
    fun onAudioReceived(audioData: ByteArray)
    fun onTurnComplete()
    fun onToolCall(toolCall: com.google.gson.JsonObject)
}
