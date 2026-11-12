import socket
import threading
import time
from typing import List, Optional, Tuple
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

from audio_engine import AudioEngine
from network_receiver import NetworkReceiver

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def get_local_ip_addresses() -> List[str]:
    """Bilgisayarın yerel ağdaki IP adreslerini listeler."""
    ips = []
    try:
        # Harici bir hedefe geçici UDP soketi açarak aktif arayüzün IP'sini bul
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        ips.append(primary_ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    return ips if ips else ["127.0.0.1"]


def create_tray_icon_image():
    """Sistem tepsisi için basit bir mikrofon ikonu çizer."""
    image = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Mikrofon gövdesi (mavi/mor yuvarlak dikdörtgen)
    draw.rounded_rectangle([22, 10, 42, 38], radius=10, fill="#3B82F6")
    # Mikrofon çanağı (U şekli)
    draw.arc([16, 20, 48, 46], start=0, end=180, fill="#93C5FD", width=4)
    # Mikrofon ayağı
    draw.line([32, 46, 32, 56], fill="#93C5FD", width=4)
    draw.line([22, 56, 42, 56], fill="#93C5FD", width=4)
    return image


class Mic2PcApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("mic2pc - Ultra Düşük Gecikmeli Sanal Mikrofon Alıcısı")
        self.geometry("640x720")
        self.minsize(580, 680)

        # Temel bileşenler
        self.audio_engine = AudioEngine(
            sample_rate=48000,
            target_buffer_ms=25,
            on_vu_update=self._on_vu_update,
        )
        self.network_receiver = NetworkReceiver(
            port=50005,
            on_audio_data=self._on_audio_data,
            on_stats_update=self._on_stats_update,
        )

        self.devices: List[Tuple[int, str, str]] = []
        self.selected_device_index: Optional[int] = None
        self.is_active = False

        # GUI Elemanlarını oluştur
        self._build_ui()

        # Sistem tepsisi entegrasyonu
        self.tray_icon: Optional[pystray.Icon] = None
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)

        # Cihaz listesini doldur
        self._refresh_audio_devices()

    def _build_ui(self):
        # Üst Başlık & Durum
        self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E222D")
        self.header_frame.pack(fill="x", padx=16, pady=(16, 8))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🎙️ mic2pc Receiver",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#60A5FA",
        )
        self.title_label.pack(pady=(12, 2))

        local_ips = get_local_ip_addresses()
        ip_text = f"PC Yerel IP: {', '.join(local_ips)}  |  Mobil cihazınızda bu IP'yi girin"
        self.ip_info_label = ctk.CTkLabel(
            self.header_frame,
            text=ip_text,
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
        )
        self.ip_info_label.pack(pady=(0, 10))

        # Ayarlar Kartı
        self.settings_frame = ctk.CTkFrame(self, corner_radius=12)
        self.settings_frame.pack(fill="x", padx=16, pady=8)

        # UDP Port Ayarı
        self.port_label = ctk.CTkLabel(
            self.settings_frame,
            text="UDP Dinleme Portu:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.port_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.port_entry = ctk.CTkEntry(self.settings_frame, width=120)
        self.port_entry.insert(0, "50005")
        self.port_entry.grid(row=0, column=1, sticky="w", padx=16, pady=(14, 4))

        # Çıkış Aygıtı Seçimi (VB-Cable / Sanal Giriş)
        self.dev_label = ctk.CTkLabel(
            self.settings_frame,
            text="Ses Çıkış Aygıtı (VB-CABLE / Virtual Audio):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.dev_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 4))

        self.dev_combo = ctk.CTkComboBox(
            self.settings_frame,
            width=560,
            values=["Yükleniyor..."],
            command=self._on_device_selected,
        )
        self.dev_combo.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))

        # Jitter Buffer Ayarı
        self.jitter_label = ctk.CTkLabel(
            self.settings_frame,
            text="Jitter Buffer Boyutu: 25 ms (Önerilen: 20-35ms)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.jitter_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 2))

        self.jitter_slider = ctk.CTkSlider(
            self.settings_frame,
            from_=10,
            to=100,
            number_of_steps=18,
            command=self._on_jitter_slider_change,
        )
        self.jitter_slider.set(25)
        self.jitter_slider.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))

        # İstatistikler ve Canlı Durum Kartı
        self.stats_frame = ctk.CTkFrame(self, corner_radius=12)
        self.stats_frame.pack(fill="x", padx=16, pady=8)

        self.status_badge = ctk.CTkLabel(
            self.stats_frame,
            text="● DURDURULDU",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#EF4444",
        )
        self.status_badge.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6))

        self.sender_label = ctk.CTkLabel(
            self.stats_frame,
            text="Bağlı Mobil Cihaz: Bekleniyor...",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
        )
        self.sender_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 8))

        # Gecikme, Jitter ve Paket Kaybı Metrikleri
        self.metrics_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.metrics_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        self.metrics_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.metric_latency = self._create_metric_box(self.metrics_frame, 0, "Gecikme (Latency)", "0 ms")
        self.metric_jitter = self._create_metric_box(self.metrics_frame, 1, "Jitter", "0.0 ms")
        self.metric_loss = self._create_metric_box(self.metrics_frame, 2, "Paket Kaybı", "%0.0")
        self.metric_pps = self._create_metric_box(self.metrics_frame, 3, "Paket/sn", "0 pps")

        # VU Meter (Canlı Ses Seviyesi)
        self.vu_frame = ctk.CTkFrame(self, corner_radius=12)
        self.vu_frame.pack(fill="x", padx=16, pady=8)

        self.vu_label = ctk.CTkLabel(
            self.vu_frame,
            text="Mikrofon Ses Seviyesi (VU Meter):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.vu_label.pack(anchor="w", padx=16, pady=(12, 4))

        self.vu_progress = ctk.CTkProgressBar(self.vu_frame, height=18, corner_radius=6)
        self.vu_progress.pack(fill="x", padx=16, pady=(0, 12))
        self.vu_progress.set(0.0)
        self.vu_progress.configure(progress_color="#10B981")

        # Kontrol Butonları
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=16, pady=(12, 16))

        self.toggle_button = ctk.CTkButton(
            self.button_frame,
            text="Hizmeti Başlat",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            fg_color="#10B981",
            hover_color="#059669",
            command=self._toggle_service,
        )
        self.toggle_button.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.tray_button = ctk.CTkButton(
            self.button_frame,
            text="Arka Plana / Tepsiye Küçült",
            font=ctk.CTkFont(size=13),
            height=46,
            fg_color="#374151",
            hover_color="#4B5563",
            command=self._minimize_to_tray,
        )
        self.tray_button.pack(side="right", padx=(8, 0))

    def _create_metric_box(self, parent, col, title, initial_val):
        box = ctk.CTkFrame(parent, corner_radius=8, fg_color="#1E222D")
        box.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")

        lbl_t = ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=11), text_color="#9CA3AF")
        lbl_t.pack(pady=(6, 0))

        lbl_v = ctk.CTkLabel(box, text=initial_val, font=ctk.CTkFont(size=15, weight="bold"))
        lbl_v.pack(pady=(0, 6))
        return lbl_v

    def _refresh_audio_devices(self):
        self.devices = AudioEngine.get_output_devices()
        device_names = []
        preferred_idx = 0

        for i, (idx, name, api) in enumerate(self.devices):
            display_name = f"[{idx}] {name} ({api})"
            device_names.append(display_name)
            # Eğer VB-Audio Cable veya Virtual ses aygıtı varsa öncelikli seç
            name_lower = name.lower()
            if "cable input" in name_lower or "vb-audio" in name_lower or "virtual" in name_lower:
                preferred_idx = i

        if device_names:
            self.dev_combo.configure(values=device_names)
            self.dev_combo.set(device_names[preferred_idx])
            self.selected_device_index = self.devices[preferred_idx][0]
        else:
            self.dev_combo.configure(values=["Ses çıkış aygıtı bulunamadı!"])

    def _on_device_selected(self, choice):
        for idx, name, api in self.devices:
            if choice.startswith(f"[{idx}]"):
                self.selected_device_index = idx
                if self.is_active:
                    # Çalışırken cihaz değiştirildiyse motoru yeniden başlat
                    self.audio_engine.start(self.selected_device_index)
                break

    def _on_jitter_slider_change(self, value):
        val_int = int(value)
        self.jitter_label.configure(text=f"Jitter Buffer Boyutu: {val_int} ms (Önerilen: 20-35ms)")
        self.audio_engine.set_target_buffer_ms(val_int)

    def _on_vu_update(self, peak: float):
        # Peak 0.0 - 1.0 arası gelir, logaritmik görünüm için küçük amplifikasyon
        display_val = min(1.0, peak * 1.5)
        self.after(0, lambda: self._update_vu_ui(display_val))

    def _update_vu_ui(self, val: float):
        self.vu_progress.set(val)
        if val > 0.85:
            self.vu_progress.configure(progress_color="#EF4444")  # Kırmızı (Kırpılma / Clipping)
        elif val > 0.65:
            self.vu_progress.configure(progress_color="#F59E0B")  # Sarı
        else:
            self.vu_progress.configure(progress_color="#10B981")  # Yeşil

    def _on_audio_data(self, pcm_bytes: bytes, seq: int, client_timestamp: int):
        self.audio_engine.feed_pcm(pcm_bytes)

    def _on_stats_update(self, latency_ms: float, jitter_ms: float, loss_pct: float, pps: int):
        self.after(
            0,
            lambda: self._update_stats_ui(latency_ms, jitter_ms, loss_pct, pps),
        )

    def _update_stats_ui(self, latency_ms: float, jitter_ms: float, loss_pct: float, pps: int):
        if not self.is_active:
            return

        client = self.network_receiver.connected_client
        if client:
            self.sender_label.configure(text=f"Bağlı Mobil Cihaz: {client[0]}:{client[1]}")
            self.status_badge.configure(text="● SES ALINIYOR (CANLI)", text_color="#10B981")
        else:
            self.sender_label.configure(text="Bağlı Mobil Cihaz: Bekleniyor (Telefondan bağlanın)...")
            self.status_badge.configure(text="● DİNLENİYOR (BEKLEMEDE)", text_color="#F59E0B")

        # Metrikleri güncelle
        self.metric_latency.configure(text=f"{int(latency_ms)} ms")
        if latency_ms < 25:
            self.metric_latency.configure(text_color="#10B981")
        elif latency_ms < 50:
            self.metric_latency.configure(text_color="#F59E0B")
        else:
            self.metric_latency.configure(text_color="#EF4444")

        self.metric_jitter.configure(text=f"{jitter_ms:.1f} ms")
        self.metric_loss.configure(text=f"%{loss_pct:.1f}")
        self.metric_loss.configure(text_color="#EF4444" if loss_pct > 2.0 else "#9CA3AF")
        self.metric_pps.configure(text=f"{pps} pps")

    def _toggle_service(self):
        if not self.is_active:
            # Başlat
            try:
                port = int(self.port_entry.get().strip())
            except ValueError:
                port = 50005

            self.network_receiver.port = port
            self.audio_engine.start(self.selected_device_index)
            self.network_receiver.start()

            self.is_active = True
            self.toggle_button.configure(
                text="Hizmeti Durdur",
                fg_color="#EF4444",
                hover_color="#DC2626",
            )
            self.status_badge.configure(text="● DİNLENİYOR (BEKLEMEDE)", text_color="#F59E0B")
            self.port_entry.configure(state="disabled")
        else:
            # Durdur
            self.network_receiver.stop()
            self.audio_engine.stop()

            self.is_active = False
            self.toggle_button.configure(
                text="Hizmeti Başlat",
                fg_color="#10B981",
                hover_color="#059669",
            )
            self.status_badge.configure(text="● DURDURULDU", text_color="#EF4444")
            self.sender_label.configure(text="Bağlı Mobil Cihaz: Bekleniyor...")
            self.port_entry.configure(state="normal")
            self.vu_progress.set(0.0)

    def _minimize_to_tray(self):
        self.withdraw()  # Pencereyi gizle
        if not self.tray_icon:
            image = create_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Göster", self._restore_from_tray, default=True),
                pystray.MenuItem("Çıkış", self._exit_application),
            )
            self.tray_icon = pystray.Icon("mic2pc", image, "mic2pc Receiver", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _restore_from_tray(self, icon=None, item=None):
        self.after(0, self.deiconify)

    def _on_close_button(self):
        # Kapatıldığında doğrudan çıkmak yerine temizleyip kapat
        self._exit_application()

    def _exit_application(self, icon=None, item=None):
        if self.is_active:
            self.network_receiver.stop()
            self.audio_engine.stop()

        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        self.destroy()


def run_app():
    app = Mic2PcApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
