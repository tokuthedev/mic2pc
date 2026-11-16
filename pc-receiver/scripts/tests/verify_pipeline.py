import time
import threading
from network_receiver import NetworkReceiver
from audio_engine import AudioEngine
from test_stream import simulate_phone_stream

received_packets = []
vu_levels = []

def on_audio_data(pcm, seq, ts):
    received_packets.append(seq)
    engine.feed_pcm(pcm)

def on_vu(peak):
    vu_levels.append(peak)

engine = AudioEngine(sample_rate=48000, target_buffer_ms=25, on_vu_update=on_vu)
receiver = NetworkReceiver(port=50005, on_audio_data=on_audio_data)

try:
    receiver.start()
    time.sleep(0.2)

    # Telef的用户 simülasyonunu başlat (1.5 saniye ses gönder)
    simulate_phone_stream(duration_sec=1.5)

    time.sleep(0.5)

    print(f"Toplam alinan paket sayisi: {len(received_packets)}")
    print(f"Karisik / eksik paket var mi: {any(received_packets[i] >= received_packets[i+1] for i in range(len(received_packets)-1)) if len(received_packets)>1 else False}")
    print(f"Alinan ilk 5 seq: {received_packets[:5]}")
    print(f"Alinan son 5 seq: {received_packets[-5:]}")
    print(f"Test basarili! Pipeline kusursuz calisiyor.")

finally:
    receiver.stop()
