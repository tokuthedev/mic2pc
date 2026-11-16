import socket
import struct
import time
import numpy as np

def simulate_phone_stream(ip="127.0.0.1", port=50005, duration_sec=2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sample_rate = 48000
    frame_samples = 480  # 10ms frame
    seq = 0
    t = 0.0

    print(f"Telefon akisi simule ediliyor: {ip}:{port} ({duration_sec} sn)...")
    end_time = time.time() + duration_sec

    while time.time() < end_time:
        # 440 Hz sinüs tonu üret (test sesi)
        chunk_t = np.linspace(t, t + (frame_samples / sample_rate), frame_samples, endpoint=False)
        t += (frame_samples / sample_rate)
        sine_wave = (np.sin(2 * np.pi * 440 * chunk_t) * 16000).astype(np.int16)

        pcm_bytes = sine_wave.tobytes()
        timestamp_ms = int(time.time() * 1000)

        # Header: Magic(2B), Seq(4B), Timestamp(8B) = 14B
        header = struct.pack("!2sIQ", b"M2", seq, timestamp_ms)
        packet = header + pcm_bytes

        sock.sendto(packet, (ip, port))
        seq += 1
        time.sleep(0.010)  # 10ms per frame

    sock.close()
    print(f"Simulasyon bitti! Toplam gonderilen paket: {seq}")

if __name__ == "__main__":
    simulate_phone_stream()
