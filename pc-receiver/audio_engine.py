import collections
import threading
import time
from typing import Callable, List, Optional, Tuple
import numpy as np
import sounddevice as sd


class AudioEngine:
    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 1,
        target_buffer_ms: int = 30,
        on_vu_update: Optional[Callable[[float], None]] = None,
    ):
        """
        Düşük gecikmeli ses çıkış motoru ve adaptif Jitter Buffer.
        :param sample_rate: 48000 Hz (önerilen) veya 44100 Hz
        :param channels: 1 (mono) veya 2 (stereo kopyalama)
        :param target_buffer_ms: Hedef jitter buffer boyutu (ms). 20-40 ms idealdir.
        :param on_vu_update: VU meter seviye callback'i (0.0 - 1.0)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.target_buffer_ms = target_buffer_ms
        self.on_vu_update = on_vu_update

        # Hedef buffer örnek sayısı (örneğin 48000 * 0.030 = 1440 örnek)
        self.target_buffer_samples = int(self.sample_rate * (self.target_buffer_ms / 1000.0))
        # Maksimum buffer: Hedefin 3 katını aşarsa ses gecikmesini düşürmek için atlar (drop)
        self.max_buffer_samples = self.target_buffer_samples * 3

        self.stream: Optional[sd.OutputStream] = None
        self.output_device_index: Optional[int] = None
        self.is_running = False

        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._is_prebuffering = True

        # VU meter için son seviye
        self.current_peak = 0.0

    @staticmethod
    def get_output_devices() -> List[Tuple[int, str, str]]:
        """
        Kullanılabilir tüm ses çıkış cihazlarını listeler.
        Dönüş: [(device_index, name, host_api)]
        """
        devices = []
        host_apis = {i: api["name"] for i, api in enumerate(sd.query_hostapis())}
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_output_channels"] > 0:
                api_name = host_apis.get(dev["hostapi"], "Bilinmeyen")
                devices.append((i, dev["name"], api_name))
        return devices

    def set_target_buffer_ms(self, ms: int):
        with self._lock:
            self.target_buffer_ms = max(10, min(200, ms))
            self.target_buffer_samples = int(self.sample_rate * (self.target_buffer_ms / 1000.0))
            self.max_buffer_samples = self.target_buffer_samples * 3

    def feed_pcm(self, pcm_bytes: bytes):
        """
        Gelen ham 16-bit PCM verisini tampona ekler.
        """
        if not self.is_running or not pcm_bytes:
            return

        with self._lock:
            self._buffer.extend(pcm_bytes)

            current_samples = len(self._buffer) // 2  # 16-bit = 2 bytes per sample

            # Eğer gecikme birikmişse (overrun), en eski verileri temizle
            if current_samples > self.max_buffer_samples:
                excess_bytes = (current_samples - self.target_buffer_samples) * 2
                self._buffer = self._buffer[excess_bytes:]

            # Prebuffering bitti mi kontrol et
            if self._is_prebuffering and current_samples >= self.target_buffer_samples:
                self._is_prebuffering = False

    def _audio_callback(self, outdata, frames, time_info, status):
        """
        SoundDevice donanım ses callback fonksiyonu.
        Düşük gecikme için minimum işlem yapar.
        """
        bytes_needed = frames * 2  # 16-bit mono = frames * 2 bytes

        with self._lock:
            buffer_len = len(self._buffer)

            # Yeterli veri yoksa (underrun) veya hala prebuffering yapılıyorsa
            if self._is_prebuffering or buffer_len < bytes_needed:
                if buffer_len < bytes_needed:
                    self._is_prebuffering = True  # Tekrar dolana kadar sessizlik bas
                outdata.fill(0)
                return

            # Tampondan veriyi al
            chunk = self._buffer[:bytes_needed]
            self._buffer = self._buffer[bytes_needed:]

        # PCM 16-bit int -> float32 [-1.0, 1.0]
        data16 = np.frombuffer(chunk, dtype=np.int16)
        data_float = data16.astype(np.float32) / 32768.0

        # Eğer çıkış kanalı stereo ise mono veriyi iki kanala çoğalt
        if self.channels == 2:
            outdata[:] = np.column_stack((data_float, data_float))
        else:
            outdata[:] = data_float.reshape(-1, 1)

        # VU Meter hesaplama (Peak amplitude)
        peak = float(np.max(np.abs(data_float))) if len(data_float) > 0 else 0.0
        self.current_peak = peak
        if self.on_vu_update:
            self.on_vu_update(peak)

    def start(self, device_index: Optional[int] = None):
        """
        Ses akışını başlatır.
        :param device_index: Çıkış yapılacak cihazın indeksi (None ise sistem varsayılanı)
        """
        if self.is_running:
            self.stop()

        self.output_device_index = device_index
        with self._lock:
            self._buffer.clear()
            self._is_prebuffering = True

        # Seçilen cihazın kanal desteğini doğrula
        dev_info = sd.query_devices(device_index) if device_index is not None else sd.default.device[1]
        out_channels = 2 if dev_info["max_output_channels"] >= 2 else 1
        self.channels = out_channels

        # Düşük gecikmeli OutputStream (blocksize=240 sample = 5ms @ 48kHz)
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            device=device_index,
            channels=self.channels,
            dtype="float32",
            latency="low",
            blocksize=240,
            callback=self._audio_callback,
        )
        self.stream.start()
        self.is_running = True

    def stop(self):
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        with self._lock:
            self._buffer.clear()
            self._is_prebuffering = True
        self.current_peak = 0.0
