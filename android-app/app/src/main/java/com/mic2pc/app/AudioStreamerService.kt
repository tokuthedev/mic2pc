package com.mic2pc.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class AudioStreamerService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var wakeLock: PowerManager.WakeLock? = null
    private var audioCapture: AudioCaptureEngine? = null
    private var udpSender: UdpAudioSender? = null

    companion object {
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        const val EXTRA_IP = "EXTRA_IP"
        const val EXTRA_PORT = "EXTRA_PORT"
        const val CHANNEL_ID = "mic2pc_stream_channel"
        const val NOTIFICATION_ID = 1001

        // UI ile iletişim için callback'ler
        var onVuMeterUpdate: ((Int) -> Unit)? = null
        var onStatsUpdate: ((Long, Int) -> Unit)? = null
        var isRunning: Boolean = false
            private set
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "mic2pc:AudioStreamerWakeLock"
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val ip = intent.getStringExtra(EXTRA_IP) ?: "192.168.1.1"
                val port = intent.getIntExtra(EXTRA_PORT, 50005)
                startStreaming(ip, port)
            }
            ACTION_STOP -> {
                stopStreaming()
            }
        }
        return START_NOT_STICKY
    }

    private fun startStreaming(ip: String, port: Int) {
        if (isRunning) return
        isRunning = true

        wakeLock?.acquire(12 * 60 * 60 * 1000L) // 12 saat maksimum

        val notification = createNotification("Sese başlandı: $ip:$port")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        serviceScope.launch {
            try {
                udpSender = UdpAudioSender(ip, port)
                audioCapture = AudioCaptureEngine(
                    sampleRate = 48000,
                    onAudioChunkReady = { chunk, length ->
                        udpSender?.sendPcmChunk(chunk, length)
                    },
                    onVuLevelChanged = { level ->
                        onVuMeterUpdate?.invoke(level)
                    }
                )
                audioCapture?.start()

                // İstatistik raporlama döngüsü (her saniye)
                var lastPacketCount = 0L
                while (isRunning) {
                    delay(1000)
                    val total = udpSender?.totalPacketsSent ?: 0L
                    val pps = (total - lastPacketCount).toInt()
                    lastPacketCount = total
                    onStatsUpdate?.invoke(total, pps)
                }
            } catch (e: Exception) {
                stopStreaming()
            }
        }
    }

    private fun stopStreaming() {
        isRunning = false
        audioCapture?.stop()
        audioCapture = null
        udpSender?.close()
        udpSender = null

        if (wakeLock?.isHeld == true) {
            wakeLock?.release()
        }

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "mic2pc Ses Yayını",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Arka planda mikrofon yayını devam ediyor"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(contentText: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("mic2pc Aktif")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        stopStreaming()
        serviceScope.cancel()
        super.onDestroy()
    }
}
