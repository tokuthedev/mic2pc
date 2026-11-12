package com.mic2pc.app

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.nio.ByteBuffer
import java.nio.ByteOrder

class UdpAudioSender(
    private val targetIp: String,
    private val targetPort: Int
) {
    private var socket: DatagramSocket? = null
    private var inetAddress: InetAddress? = null
    private var sequenceNumber: Int = 0

    // Magic Header: 'M', '2' (0x4D, 0x32)
    // Format: Magic(2) + Seq(4) + TimestampMs(8) = 14 bytes header
    private val headerBuffer = ByteBuffer.allocate(14).apply {
        order(ByteOrder.BIG_ENDIAN)
    }

    var totalPacketsSent: Long = 0
        private set

    init {
        socket = DatagramSocket().apply {
            // Düşük gecikme için soket tamponu
            sendBufferSize = 65536
        }
        inetAddress = InetAddress.getByName(targetIp)
    }

    fun sendPcmChunk(pcmData: ShortArray, length: Int) {
        val dest = inetAddress ?: return
        val sock = socket ?: return

        val byteCount = length * 2
        val packetBuffer = ByteArray(14 + byteCount)

        // Başlık yazma
        val timestampMs = System.currentTimeMillis()
        packetBuffer[0] = 0x4D.toByte() // 'M'
        packetBuffer[1] = 0x32.toByte() // '2'

        // Sequence number (Big Endian)
        packetBuffer[2] = (sequenceNumber ushr 24).toByte()
        packetBuffer[3] = (sequenceNumber ushr 16).toByte()
        packetBuffer[4] = (sequenceNumber ushr 8).toByte()
        packetBuffer[5] = sequenceNumber.toByte()
        sequenceNumber++

        // Timestamp ms (Big Endian)
        for (i in 0..7) {
            packetBuffer[6 + i] = (timestampMs ushr (56 - i * 8)).toByte()
        }

        // PCM verisini Little-Endian olarak byte dizisine kopyala
        var offset = 14
        for (i in 0 until length) {
            val s = pcmData[i].toInt()
            packetBuffer[offset++] = (s and 0xFF).toByte()
            packetBuffer[offset++] = ((s ushr 8) and 0xFF).toByte()
        }

        val packet = DatagramPacket(packetBuffer, packetBuffer.size, dest, targetPort)
        try {
            sock.send(packet)
            totalPacketsSent++
        } catch (e: Exception) {
            // Ağ geçişi veya paket atma durumu
        }
    }

    fun close() {
        try {
            socket?.close()
        } catch (e: Exception) {
            // Ignore
        }
        socket = null
    }
}
