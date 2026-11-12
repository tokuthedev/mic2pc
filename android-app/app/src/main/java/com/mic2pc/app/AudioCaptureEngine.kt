package com.mic2pc.app

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import kotlin.math.abs
import kotlin.math.max

class AudioCaptureEngine(
    private val sampleRate: Int = 48000,
    private val onAudioChunkReady: (ShortArray, Int) -> Unit,
    private val onVuLevelChanged: (Int) -> Unit
) {
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordThread: Thread? = null

    // 10ms frame: 48000 * 0.010 = 480 sample
    private val frameSize = 480

    @SuppressLint("MissingPermission")
    fun start() {
        if (isRecording) return

        val minBufSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        val bufferSize = max(minBufSize, frameSize * 4)

        // Düşük gecikme ve oyun/Discord iletişimi için VOICE_COMMUNICATION kaynağı
        // (Donanım seviyesinde eko ve arka plan gürültüsü filtresini devreye sokar)
        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            // Eğer VOICE_COMMUNICATION başlatılamazsa standart MIC kaynağına geri dön
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            )
        }

        audioRecord?.startRecording()
        isRecording = true

        recordThread = Thread({
            val audioBuffer = ShortArray(frameSize)
            var vuCounter = 0

            while (isRecording) {
                val readSamples = audioRecord?.read(audioBuffer, 0, frameSize) ?: -1
                if (readSamples > 0) {
                    onAudioChunkReady(audioBuffer, readSamples)

                    // Her 3 pakette bir (~30ms) VU meter hesapla (UI'ı kasmamak için)
                    vuCounter++
                    if (vuCounter >= 3) {
                        vuCounter = 0
                        var maxAmp = 0
                        for (i in 0 until readSamples) {
                            val amp = abs(audioBuffer[i].toInt())
                            if (amp > maxAmp) maxAmp = amp
                        }
                        // 0 - 32767 aralığını 0 - 100 ölçeğine eşle
                        val percentage = ((maxAmp / 32767.0) * 100).toInt().coerceIn(0, 100)
                        onVuLevelChanged(percentage)
                    }
                }
            }
        }, "MicCaptureThread").apply {
            priority = Thread.MAX_PRIORITY // Ses gecikmesi olmaması için en yüksek öncelik
            start()
        }
    }

    fun stop() {
        isRecording = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (e: Exception) {
            // Ignore
        }
        audioRecord = null

        recordThread?.interrupt()
        recordThread = null
        onVuLevelChanged(0)
    }
}
