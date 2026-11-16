package com.mic2pc.app

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.media.MediaRecorder
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.mic2pc.app.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: SharedPreferences

    private var selectedSource = MediaRecorder.AudioSource.VOICE_COMMUNICATION
    private var selectedGain = 1.0f
    private var keepScreenOn = false

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
        setupNavigation()
        setupListeners()
        setupSettingsControls()
        checkPermissions()

        // Uygulama açılışında arka planda sessizce güncelleme kontrolü yap
        AppUpdater.checkForUpdate(
            currentVersionCode = getCurrentVersionCode(),
            onUpdateFound = { updateInfo ->
                AppUpdater.showUpdateDialog(this, updateInfo)
            }
        )
    }

    private fun getCurrentVersionCode(): Int {
        return try {
            val pInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getPackageInfo(packageName, PackageManager.PackageInfoFlags.of(0))
            } else {
                @Suppress("DEPRECATION")
                packageManager.getPackageInfo(packageName, 0)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                pInfo.longVersionCode.toInt()
            } else {
                @Suppress("DEPRECATION")
                pInfo.versionCode
            }
        } catch (e: Exception) {
            1
        }
    }

    private fun getCurrentVersionName(): String {
        return try {
            packageManager.getPackageInfo(packageName, 0).versionName ?: "1.0.0"
        } catch (e: Exception) {
            "1.0.0"
        }
    }

    override fun onResume() {
        super.onResume()
        updateUiState(AudioStreamerService.isRunning)

        AudioStreamerService.onVuMeterUpdate = { vuLevel ->
            runOnUiThread {
                binding.pbVuMeter.progress = vuLevel
                binding.tvVuPercent.text = "$vuLevel%"
            }
        }

        AudioStreamerService.onStatsUpdate = { totalPackets, pps ->
            runOnUiThread {
                val kbps = (pps * 974 * 8) / 1000
                binding.tvPacketStats.text = "Paket: $totalPackets | Hız: $pps pkt/s (~$kbps kbps)"
            }
        }
    }

    override fun onPause() {
        super.onPause()
        AudioStreamerService.onVuMeterUpdate = null
        AudioStreamerService.onStatsUpdate = null
    }

    private fun setupNavigation() {
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_stream -> {
                    binding.layoutStreamTab.visibility = View.VISIBLE
                    binding.layoutSettingsTab.visibility = View.GONE
                    true
                }
                R.id.nav_settings -> {
                    binding.layoutStreamTab.visibility = View.GONE
                    binding.layoutSettingsTab.visibility = View.VISIBLE
                    true
                }
                else -> false
            }
        }
    }

    private fun loadSavedSettings() {
        val savedIp = prefs.getString("last_ip", "192.168.1.")
        val savedPort = prefs.getInt("last_port", 50005)
        binding.etTargetIp.setText(savedIp)
        binding.etTargetPort.setText(savedPort.toString())

        selectedSource = prefs.getInt("audio_source", MediaRecorder.AudioSource.VOICE_COMMUNICATION)
        selectedGain = prefs.getFloat("audio_gain", 1.0f)
        keepScreenOn = prefs.getBoolean("keep_screen_on", false)

        applyKeepScreenOn(keepScreenOn)
    }

    private fun saveSettings(ip: String, port: Int) {
        prefs.edit()
            .putString("last_ip", ip)
            .putInt("last_port", port)
            .apply()
    }

    private fun setupSettingsControls() {
        // Ses Kaynağı RadioGroup
        if (selectedSource == MediaRecorder.AudioSource.MIC) {
            binding.rbSourceRawMic.isChecked = true
        } else {
            binding.rbSourceVoiceComm.isChecked = true
        }

        binding.rgAudioSource.setOnCheckedChangeListener { _, checkedId ->
            selectedSource = if (checkedId == R.id.rbSourceRawMic) {
                MediaRecorder.AudioSource.MIC
            } else {
                MediaRecorder.AudioSource.VOICE_COMMUNICATION
            }
            prefs.edit().putInt("audio_source", selectedSource).apply()
            Toast.makeText(this, "Ses modu kaydedildi (Yayını yeniden başlatın)", Toast.LENGTH_SHORT).show()
        }

        // Kazanç Butonları
        binding.tvGainValue.text = "${selectedGain}x"
        val gainButtons = listOf(
            binding.btnGain10 to 1.0f,
            binding.btnGain15 to 1.5f,
            binding.btnGain20 to 2.0f,
            binding.btnGain25 to 2.5f
        )

        gainButtons.forEach { (btn, gainVal) ->
            btn.setOnClickListener {
                selectedGain = gainVal
                binding.tvGainValue.text = "${selectedGain}x"
                prefs.edit().putFloat("audio_gain", selectedGain).apply()
                Toast.makeText(this, "Kazanç ${gainVal}x olarak ayarlandı", Toast.LENGTH_SHORT).show()
            }
        }

        // Ekranı Açık Tut Switch
        binding.switchKeepScreenOn.isChecked = keepScreenOn
        binding.switchKeepScreenOn.setOnCheckedChangeListener { _, isChecked ->
            keepScreenOn = isChecked
            prefs.edit().putBoolean("keep_screen_on", isChecked).apply()
            applyKeepScreenOn(isChecked)
        }

        // Tema Butonları
        binding.btnThemeLavender.setOnClickListener {
            Toast.makeText(this, "Lavender Teması devrede", Toast.LENGTH_SHORT).show()
        }
        binding.btnThemeBlue.setOnClickListener {
            Toast.makeText(this, "Mavi Safir Teması devrede", Toast.LENGTH_SHORT).show()
        }
        binding.btnThemeGreen.setOnClickListener {
            Toast.makeText(this, "Zümrüt Yeşil Teması devrede", Toast.LENGTH_SHORT).show()
        }
        binding.btnThemeAmber.setOnClickListener {
            Toast.makeText(this, "Amber Teması devrede", Toast.LENGTH_SHORT).show()
        }

        // Otomatik Güncelleme (In-App Auto Update)
        val curVerName = getCurrentVersionName()
        val curVerCode = getCurrentVersionCode()
        binding.tvAppVersion.text = "Mevcut Sürüm: v$curVerName (Kod: $curVerCode)"

        binding.btnCheckUpdate.setOnClickListener {
            Toast.makeText(this, "Güncellemeler denetleniyor...", Toast.LENGTH_SHORT).show()
            AppUpdater.checkForUpdate(
                currentVersionCode = curVerCode,
                onUpdateFound = { updateInfo ->
                    AppUpdater.showUpdateDialog(this, updateInfo)
                },
                onUpToDate = {
                    Toast.makeText(this, "mic2pc en güncel sürümde! (v$curVerName)", Toast.LENGTH_SHORT).show()
                },
                onError = { err ->
                    Toast.makeText(this, "Güncelleme denetlenemedi: $err", Toast.LENGTH_SHORT).show()
                }
            )
        }
    }

    private fun applyKeepScreenOn(enable: Boolean) {
        if (enable) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
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
            putExtra(AudioStreamerService.EXTRA_SOURCE, selectedSource)
            putExtra(AudioStreamerService.EXTRA_GAIN, selectedGain)
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
        binding.tvVuPercent.text = "0%"
        binding.tvPacketStats.text = "Paket: 0 | Hız: 0 pkt/s"
    }

    private fun updateUiState(isStreaming: Boolean) {
        if (isStreaming) {
            binding.btnToggleStream.text = getString(R.string.btn_stop)
            binding.btnToggleStream.backgroundTintList =
                ColorStateList.valueOf(ContextCompat.getColor(this, R.color.m3_error))
            binding.btnToggleStream.setTextColor(
                ContextCompat.getColor(this, R.color.m3_on_error)
            )

            binding.tvStatus.text = getString(R.string.status_streaming)
            binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.m3_tertiary))
            binding.viewStatusDot.setBackgroundResource(R.drawable.circle_green)

            binding.etTargetIp.isEnabled = false
            binding.etTargetPort.isEnabled = false
        } else {
            binding.btnToggleStream.text = getString(R.string.btn_start)
            binding.btnToggleStream.backgroundTintList =
                ColorStateList.valueOf(ContextCompat.getColor(this, R.color.m3_primary))
            binding.btnToggleStream.setTextColor(
                ContextCompat.getColor(this, R.color.m3_on_primary)
            )

            binding.tvStatus.text = getString(R.string.status_disconnected)
            binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.m3_error))
            binding.viewStatusDot.setBackgroundResource(R.drawable.circle_red)

            binding.etTargetIp.isEnabled = true
            binding.etTargetPort.isEnabled = true
        }
    }
}
