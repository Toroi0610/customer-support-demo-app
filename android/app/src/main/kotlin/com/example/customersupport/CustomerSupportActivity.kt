package com.example.customersupport

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.customersupport.adapter.MessageAdapter
import com.example.customersupport.databinding.ActivityCustomerSupportBinding
import com.example.customersupport.model.Message
import com.example.customersupport.model.MessageType
import com.google.gson.JsonObject

class CustomerSupportActivity : AppCompatActivity(), WebSocketListener2 {

    companion object {
        const val EXTRA_SERVER_URL = "extra_server_url"
        private const val REQUEST_PERMISSIONS = 100
    }

    private lateinit var binding: ActivityCustomerSupportBinding
    private lateinit var messageAdapter: MessageAdapter
    private val mainHandler = Handler(Looper.getMainLooper())

    private var webSocketManager: WebSocketManager? = null
    private var audioRecorder: AudioRecorder? = null
    private var audioPlayer: AudioPlayer? = null
    private var serverUrl: String = ""

    // 現在の応答テキストを蓄積するバッファ
    private val currentAgentResponse = StringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCustomerSupportBinding.inflate(layoutInflater)
        setContentView(binding.root)

        serverUrl = intent.getStringExtra(EXTRA_SERVER_URL) ?: ""

        setupRecyclerView()
        setupUI()
        checkPermissionsAndConnect()
    }

    private fun setupRecyclerView() {
        messageAdapter = MessageAdapter()
        binding.rvMessages.apply {
            layoutManager = LinearLayoutManager(this@CustomerSupportActivity).apply {
                stackFromEnd = true
            }
            adapter = messageAdapter
        }
    }

    private fun setupUI() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = getString(R.string.support_title)

        binding.btnSend.setOnClickListener {
            val text = binding.etMessage.text.toString().trim()
            if (text.isNotEmpty()) {
                sendTextMessage(text)
                binding.etMessage.text?.clear()
            }
        }

        binding.btnMic.setOnClickListener {
            toggleRecording()
        }

        binding.toolbar.setNavigationOnClickListener {
            onBackPressed()
        }
    }

    private fun checkPermissionsAndConnect() {
        val permissions = arrayOf(Manifest.permission.RECORD_AUDIO)
        val notGranted = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (notGranted.isEmpty()) {
            connectToServer()
        } else {
            ActivityCompat.requestPermissions(this, notGranted.toTypedArray(), REQUEST_PERMISSIONS)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_PERMISSIONS) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                connectToServer()
            } else {
                addSystemMessage(getString(R.string.permission_denied))
                connectToServer() // テキストのみで接続
            }
        }
    }

    private fun connectToServer() {
        addSystemMessage(getString(R.string.connecting))
        binding.progressBar.visibility = View.VISIBLE

        audioPlayer = AudioPlayer()
        audioRecorder = AudioRecorder(this) { audioData ->
            webSocketManager?.sendAudioChunk(audioData)
        }

        webSocketManager = WebSocketManager(serverUrl, this)
        webSocketManager?.connect()
    }

    private fun toggleRecording() {
        if (audioRecorder?.isRecording == true) {
            audioRecorder?.stopRecording()
            binding.btnMic.setImageResource(android.R.drawable.ic_btn_speak_now)
            binding.btnMic.alpha = 1.0f
            addUserMessage(getString(R.string.audio_sent))
        } else {
            val started = audioRecorder?.startRecording() ?: false
            if (started) {
                binding.btnMic.setImageResource(android.R.drawable.ic_media_pause)
                binding.btnMic.alpha = 0.5f
                Toast.makeText(this, getString(R.string.recording_started), Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, getString(R.string.recording_failed), Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun sendTextMessage(text: String) {
        addUserMessage(text)
        webSocketManager?.sendTextMessage(text)
    }

    private fun addUserMessage(text: String) {
        mainHandler.post {
            val messages = messageAdapter.currentList.toMutableList()
            messages.add(Message(content = text, type = MessageType.USER))
            messageAdapter.submitList(messages)
            scrollToBottom()
        }
    }

    private fun addAgentMessage(text: String) {
        mainHandler.post {
            val messages = messageAdapter.currentList.toMutableList()
            messages.add(Message(content = text, type = MessageType.AGENT))
            messageAdapter.submitList(messages)
            scrollToBottom()
        }
    }

    private fun addSystemMessage(text: String) {
        mainHandler.post {
            val messages = messageAdapter.currentList.toMutableList()
            messages.add(Message(content = text, type = MessageType.SYSTEM))
            messageAdapter.submitList(messages)
            scrollToBottom()
        }
    }

    private fun scrollToBottom() {
        binding.rvMessages.post {
            if (messageAdapter.itemCount > 0) {
                binding.rvMessages.smoothScrollToPosition(messageAdapter.itemCount - 1)
            }
        }
    }

    private fun updateConnectionStatus(connected: Boolean) {
        mainHandler.post {
            binding.progressBar.visibility = View.GONE
            binding.tvConnectionStatus.text = if (connected) {
                getString(R.string.connected)
            } else {
                getString(R.string.disconnected)
            }
            binding.tvConnectionStatus.setTextColor(
                ContextCompat.getColor(
                    this,
                    if (connected) android.R.color.holo_green_dark else android.R.color.holo_red_dark
                )
            )
        }
    }

    // WebSocketListener2 implementation

    override fun onConnected() {
        // セットアップメッセージを送信するため、まだ接続完了とは表示しない
    }

    override fun onDisconnected(reason: String) {
        updateConnectionStatus(false)
        addSystemMessage(getString(R.string.disconnected_reason, reason))
    }

    override fun onError(error: String) {
        updateConnectionStatus(false)
        addSystemMessage(getString(R.string.connection_error, error))
        mainHandler.post {
            binding.progressBar.visibility = View.GONE
        }
    }

    override fun onSetupComplete() {
        updateConnectionStatus(true)
        addSystemMessage(getString(R.string.connected_ready))
    }

    override fun onTextReceived(text: String) {
        // テキストをバッファに蓄積
        currentAgentResponse.append(text)
    }

    override fun onAudioReceived(audioData: ByteArray) {
        audioPlayer?.playAudio(audioData)
    }

    override fun onTurnComplete() {
        // ターン完了時にバッファの内容をメッセージとして追加
        val responseText = currentAgentResponse.toString().trim()
        if (responseText.isNotEmpty()) {
            addAgentMessage(responseText)
            currentAgentResponse.clear()
        }
    }

    override fun onToolCall(toolCall: JsonObject) {
        val toolCallsArray = toolCall.getAsJsonArray("functionCalls")
        toolCallsArray?.forEach { element ->
            val functionCall = element.asJsonObject
            val name = functionCall.get("name")?.asString ?: "unknown"
            val args = functionCall.get("args")?.toString() ?: "{}"

            when (name) {
                "process_refund" -> {
                    addSystemMessage(getString(R.string.tool_refund))
                }
                "connect_to_human" -> {
                    addSystemMessage(getString(R.string.tool_connect_human))
                }
                "end_conversation" -> {
                    addSystemMessage(getString(R.string.tool_end_conversation))
                    mainHandler.postDelayed({
                        finish()
                    }, 2000)
                }
                else -> {
                    addSystemMessage(getString(R.string.tool_generic, name))
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        audioRecorder?.stopRecording()
        audioPlayer?.release()
        webSocketManager?.disconnect()
    }
}
