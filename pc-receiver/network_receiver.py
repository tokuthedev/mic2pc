import socket
import struct
import time
import threading
from typing import Callable, Optional, Tuple

MAGIC_HEADER = b"M2"  # 2 bytes identifier
HEADER_FORMAT = "!2sIQ"  # Magic (2s), Seq (uint32 - 4B), Timestamp ms (uint64 - 8B) = 14 bytes
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class NetworkReceiver:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 50005,
        on_audio_data: Optional[Callable[[bytes, int, int], None]] = None,
        on_stats_update: Optional[Callable[[float, float, int, int], None]] = None,
    ):
        """
        UDP Audio Stream Receiver
        :param host: Dinlenecek IP adresi (varsayılan 0.0.0.0)
        :param port: Dinlenecek UDP portu
        :param on_audio_data: Ses verisi geldiğinde çağrılır: func(pcm_bytes, seq, client_timestamp)
        :param on_stats_update: İstatistik güncellemesi: func(latency_ms, jitter_ms, loss_rate_pct, packets_per_sec)
        """
        self.host = host
        self.port = port
        self.on_audio_data = on_audio_data
        self.on_stats_update = on_stats_update

        self.running = False
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stats_thread: Optional[threading.Thread] = None

        # İstatistik değişkenleri
        self.total_packets_received = 0
        self.packets_lost = 0
        self.last_seq = -1
        self.last_transit_time = 0.0
        self.estimated_jitter = 0.0
        self.current_latency_ms = 0.0
        self.recent_packet_count = 0
        self.connected_client: Optional[Tuple[str, int]] = None

    def start(self):
        if self.running:
            return

        self.running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Hızlı döngü ve düşük gecikme için buffer boyutu ve SO_REUSEADDR
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Windows UDP soket tampon boyutu (gecikmeyi minimize etmek için çok büyük tutmuyoruz)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self._socket.bind((self.host, self.port))
        self._socket.settimeout(0.5)

        self.total_packets_received = 0
        self.packets_lost = 0
        self.last_seq = -1
        self.estimated_jitter = 0.0

        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()

        self._stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        self._stats_thread.start()

    def stop(self):
        self.running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._stats_thread and self._stats_thread.is_alive():
            self._stats_thread.join(timeout=1.0)

    def _receive_loop(self):
        while self.running:
            try:
                data, addr = self._socket.recvfrom(4096)
                if not data:
                    continue

                self.connected_client = addr
                receive_time_ms = int(time.time() * 1000)
                self.total_packets_received += 1
                self.recent_packet_count += 1

                seq = 0
                client_timestamp = 0
                pcm_payload = data

                # Başlık parsing (eğer paket başlığımız varsa)
                if len(data) >= HEADER_SIZE and data[:2] == MAGIC_HEADER:
                    magic, seq, client_timestamp = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
                    pcm_payload = data[HEADER_SIZE:]

                    # Sequence kontrolü ve paket kaybı hesabı
                    if self.last_seq != -1:
                        diff = seq - self.last_seq
                        if diff > 1:
                            self.packets_lost += (diff - 1)
                    self.last_seq = seq

                    # Gecikme ve Jitter hesabı (RFC 3550 yaklaşımı)
                    if client_timestamp > 0:
                        transit = receive_time_ms - client_timestamp
                        # Zaman uyumsuzluğu durumunda negatif çıkmaması için alt sınır 0
                        if transit >= 0:
                            self.current_latency_ms = transit
                        if self.last_transit_time != 0.0:
                            d = abs(transit - self.last_transit_time)
                            self.estimated_jitter += (d - self.estimated_jitter) / 16.0
                        self.last_transit_time = transit

                # Ses motoruna ilet
                if self.on_audio_data and len(pcm_payload) > 0:
                    self.on_audio_data(pcm_payload, seq, client_timestamp)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    # Soket kapandıysa veya hata oluştuysa
                    pass

    def _stats_loop(self):
        while self.running:
            time.sleep(0.5)
            total = self.total_packets_received + self.packets_lost
            loss_pct = (self.packets_lost / total * 100.0) if total > 0 else 0.0
            pps = self.recent_packet_count * 2  # 0.5 sn ölçüldüğü için * 2
            self.recent_packet_count = 0

            if self.on_stats_update:
                self.on_stats_update(
                    self.current_latency_ms,
                    self.estimated_jitter,
                    loss_pct,
                    pps,
                )
