package com.example.customersupport

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.customersupport.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
    }

    private fun setupUI() {
        binding.btnStartSupport.setOnClickListener {
            val serverUrl = binding.etServerUrl.text.toString().trim()
            if (serverUrl.isEmpty()) {
                Toast.makeText(this, getString(R.string.error_empty_url), Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val intent = Intent(this, CustomerSupportActivity::class.java).apply {
                putExtra(CustomerSupportActivity.EXTRA_SERVER_URL, serverUrl)
            }
            startActivity(intent)
        }

        // デフォルトのサーバーURLを設定
        binding.etServerUrl.setText(getString(R.string.default_server_url))
    }
}
