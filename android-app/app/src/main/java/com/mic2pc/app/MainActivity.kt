package com.mic2pc.app

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.mic2pc.app.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: SharedPreferences

    private val requiredPermissions = mutableListOf(
        Manifest.permission.RECORD_AUDIO
    ).apply {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val micGranted = results[Manifest.permission.RECORD_AUDIO] ?: false
        if (!micGranted) {
            Toast.makeText(this, R.string.perm_mic_required, Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = getSharedPreferences("mic2pc_prefs", Context.MODE_PRIVATE)

        loadSavedSettings()
        setupListeners()
        checkPermissions()
    }

    override fun onResume() {
        super.onResume()
        updateUiState(AudioStreamerService.isRunning)

        // Servisten gelen VU meter ve İstatistik güncellemelerini UI'a bağla
        AudioStreamerService.onVuMeterUpdate = { vuLevel ->
            runOnUiThread {
                binding.pbVuMeter.progress = vuLevel
            }
        }

        AudioStreamerService.onStatsUpdate = { totalPackets, pps ->
            runOnUiThread {
                val kbps = (pps * 974 * 8) / 1000 // Yaklaşık kilobit/sn
                binding.tvPacketStats.text = "Gönderilen: $totalPackets | Hız: $pps pkt/s (~$kbps kbps)"
            }
        }
    }

    override fun onPause() {
        super.onPause()
        // Arka plandayken UI callback'ini kaldırarak bellek sızıntısını önle
        AudioStreamerService.onVuMeterUpdate = null
        AudioStreamerService.onStatsUpdate = null
    }

    private fun loadSavedSettings() {
        val savedIp = prefs.getString("last_ip", "192.168.1.")
        val savedPort = prefs.getInt("last_port", 50005)
        binding.etTargetIp.setText(savedIp)
        binding.etTargetPort.setText(savedPort.toString())
    }

    private fun saveSettings(ip: String, port: Int) {
        prefs.edit()
            .putString("last_ip", ip)
            .putInt("last_port", port)
            .apply()
    }

    private fun checkPermissions() {
        val missingPermissions = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missingPermissions.isNotEmpty()) {
            permissionLauncher.launch(missingPermissions.toTypedArray())
        }
    }

    private fun setupListeners() {
        binding.btnToggleStream.setOnClickListener {
            if (AudioStreamerService.isRunning) {
                stopStream()
            } else {
                startStream()
            }
        }
    }

    private fun startStream() {
        val ip = binding.etTargetIp.text.toString().trim()
        val portStr = binding.etTargetPort.text.toString().trim()

        if (ip.isEmpty()) {
            binding.tilIp.error = "IP adresi girin"
            return
        }
        binding.tilIp.error = null

        val port = portStr.toIntOrNull() ?: 50005
        saveSettings(ip, port)

        val intent = Intent(this, AudioStreamerService::class.java).apply {
            action = AudioStreamerService.ACTION_START
            putExtra(AudioStreamerService.EXTRA_IP, ip)
            putExtra(AudioStreamerService.EXTRA_PORT, port)
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }

        updateUiState(true)
    }

    private fun stopStream() {
        val intent = Intent(this, AudioStreamerService::class.java).apply {
            action = AudioStreamerService.ACTION_STOP
        }
        startService(intent)

        updateUiState(false)
        binding.pbVuMeter.progress = 0
        binding.tvPacketStats.text = "Gönderilen Paket: 0 | Bit Hızı: 0 kbps"
    }

    private fun updateUiState(isStreaming: Boolean) {
        if (isStreaming) {
            binding.btnToggleStream.text = getString(R.string.btn_stop)
            binding.btnToggleStream.backgroundTintList =
                ColorStateList.valueOf(ContextCompat.getColor(this, R.color.accent_red))

            binding.tvStatus.text = getString(R.string.status_streaming)
            binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.accent_green))
            binding.viewStatusDot.setBackgroundResource(R.drawable.circle_green)

            binding.etTargetIp.isEnabled = false
            binding.etTargetPort.isEnabled = false
        } else {
            binding.btnToggleStream.text = getString(R.string.btn_start)
            binding.btnToggleStream.backgroundTintList =
                ColorStateList.valueOf(ContextCompat.getColor(this, R.color.accent_green))

            binding.tvStatus.text = getString(R.string.status_disconnected)
            binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.accent_red))
            binding.viewStatusDot.setBackgroundResource(R.drawable.circle_red)

            binding.etTargetIp.isEnabled = true
            binding.etTargetPort.isEnabled = true
        }
    }
}
