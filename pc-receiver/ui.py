import os
import sys
import socket
import threading
import time
from typing import List, Optional, Tuple
import customtkinter as ctk
import pystray
from PIL import Image, ImageTk

from audio_engine import AudioEngine
from network_receiver import NetworkReceiver

# Modern Koyu Tema Yapılandırması
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# PyInstaller bundle desteği (sys._MEIPASS)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(BASE_DIR, "icon.png")
ICO_PATH = os.path.join(BASE_DIR, "icon.ico")

FONT_FAMILY = "Segoe UI"


def get_local_ip_addresses() -> List[str]:
    """Bilgisayarın yerel ağdaki IP adreslerini listeler."""
    ips = []
    try:
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


class Mic2PcApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("mic2pc • Ultra Low-Latency Virtual Mic")
        self.geometry("640x760")
        self.minsize(580, 720)
        self.configure(fg_color="#0D1117")  # Sleek modern derin koyu arka plan

        if os.path.exists(ICO_PATH):
            try:
                self.iconbitmap(ICO_PATH)
            except Exception:
                pass

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

        # GUI'yi oluştur
        self._build_ui()

        # Sistem tepsisi entegrasyonu
        self.tray_icon: Optional[pystray.Icon] = None
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)

        # Cihaz listesini doldur
        self._refresh_audio_devices()

    def _build_ui(self):
        # 1. HEADER (Logo + Başlık + Durum Hapı)
        self.header_card = ctk.CTkFrame(self, corner_radius=14, fg_color="#161B22", border_width=1, border_color="#21262D")
        self.header_card.pack(fill="x", padx=18, pady=(16, 10))

        header_layout = ctk.CTkFrame(self.header_card, fg_color="transparent")
        header_layout.pack(fill="x", padx=16, pady=14)

        # Logo
        if os.path.exists(ICON_PATH):
            try:
                pil_logo = Image.open(ICON_PATH).resize((46, 46), Image.Resampling.LANCZOS)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(46, 46))
                self.logo_label = ctk.CTkLabel(header_layout, text="", image=self.logo_img)
                self.logo_label.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        title_container = ctk.CTkFrame(header_layout, fg_color="transparent")
        title_container.pack(side="left", fill="both", expand=True)

        app_title = ctk.CTkLabel(
            title_container,
            text="mic2pc Receiver",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color="#F0F6FC",
            anchor="w"
        )
        app_title.pack(anchor="w")

        sub_title = ctk.CTkLabel(
            title_container,
            text="Sanal Ses Sürücüsü • 48 kHz 16-bit PCM Akışı",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#8B949E",
            anchor="w"
        )
        sub_title.pack(anchor="w")

        # Üst Sağ: Canlı Durum Hapı (Pill Badge)
        self.status_pill = ctk.CTkFrame(header_layout, corner_radius=20, fg_color="#21262D", border_width=1, border_color="#30363D")
        self.status_pill.pack(side="right", padx=(8, 0))

        self.status_dot = ctk.CTkLabel(
            self.status_pill,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color="#F85149"
        )
        self.status_dot.pack(side="left", padx=(10, 4), pady=4)

        self.status_text = ctk.CTkLabel(
            self.status_pill,
            text="DURDURULDU",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#C9D1D9"
        )
        self.status_text.pack(side="left", padx=(0, 10), pady=4)

        # 2. IP ADRESİ KARTI (Kolay Kopyalama ile)
        self.ip_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#161B22", border_width=1, border_color="#21262D")
        self.ip_card.pack(fill="x", padx=18, pady=(0, 10))

        local_ips = get_local_ip_addresses()
        self.primary_ip = local_ips[0] if local_ips else "127.0.0.1"

        ip_content = ctk.CTkFrame(self.ip_card, fg_color="transparent")
        ip_content.pack(fill="x", padx=16, pady=10)

        ip_icon_lbl = ctk.CTkLabel(ip_content, text="📡", font=ctk.CTkFont(family=FONT_FAMILY, size=16))
        ip_icon_lbl.pack(side="left", padx=(0, 8))

        ip_desc = ctk.CTkLabel(
            ip_content,
            text=f"Telefonunuza bu IP'yi girin:  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#8B949E"
        )
        ip_desc.pack(side="left")

        self.ip_badge = ctk.CTkLabel(
            ip_content,
            text=f" {self.primary_ip} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#1F2937",
            corner_radius=6,
            text_color="#58A6FF"
        )
        self.ip_badge.pack(side="left", padx=(0, 10))

        self.copy_btn = ctk.CTkButton(
            ip_content,
            text="Kopyala",
            width=68,
            height=26,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#21262D",
            hover_color="#30363D",
            command=self._copy_ip
        )
        self.copy_btn.pack(side="right")

        # 3. METRİKLER (Dashboard: Gecikme, Jitter, Paket Kaybı, Hız)
        self.metrics_container = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics_container.pack(fill="x", padx=18, pady=(0, 10))
        self.metrics_container.columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")

        self.metric_latency = self._create_metric_card(self.metrics_container, 0, "Gecikme (Ping)", "0 ms", "#58A6FF")
        self.metric_jitter = self._create_metric_card(self.metrics_container, 1, "Jitter Dalgalanma", "0.0 ms", "#A371F7")
        self.metric_loss = self._create_metric_card(self.metrics_container, 2, "Paket Kaybı", "%0.0", "#3FB950")
        self.metric_pps = self._create_metric_card(self.metrics_container, 3, "Paket Hızı", "0 pps", "#E3B341")

        # 4. CANLI VU METER (Ses Seviyesi)
        self.vu_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#161B22", border_width=1, border_color="#21262D")
        self.vu_card.pack(fill="x", padx=18, pady=(0, 10))

        vu_header = ctk.CTkFrame(self.vu_card, fg_color="transparent")
        vu_header.pack(fill="x", padx=16, pady=(12, 6))

        vu_title = ctk.CTkLabel(
            vu_header,
            text="Canlı Mikrofon Seviyesi",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#F0F6FC"
        )
        vu_title.pack(side="left")

        self.vu_percent_label = ctk.CTkLabel(
            vu_header,
            text="0%",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#8B949E"
        )
        self.vu_percent_label.pack(side="right")

        self.vu_progress = ctk.CTkProgressBar(
            self.vu_card,
            height=14,
            corner_radius=7,
            fg_color="#0D1117",
            progress_color="#238636"
        )
        self.vu_progress.pack(fill="x", padx=16, pady=(0, 14))
        self.vu_progress.set(0.0)

        # 5. AYARLAR KARTI (Aygıt, Port, Jitter Buffer)
        self.settings_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#161B22", border_width=1, border_color="#21262D")
        self.settings_card.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # Aygıt Seçimi
        dev_label = ctk.CTkLabel(
            self.settings_card,
            text="Sanal Ses Çıkışı (Discord / Oyun için VB-CABLE):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#C9D1D9"
        )
        dev_label.pack(anchor="w", padx=16, pady=(12, 4))

        self.dev_combo = ctk.CTkComboBox(
            self.settings_card,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color="#0D1117",
            border_color="#30363D",
            button_color="#21262D",
            button_hover_color="#30363D",
            values=["Yükleniyor..."],
            command=self._on_device_selected
        )
        self.dev_combo.pack(fill="x", padx=16, pady=(0, 10))

        # Port & Jitter Buffer Yan Yana
        row_settings = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        row_settings.pack(fill="x", padx=16, pady=(0, 12))
        row_settings.columnconfigure(0, weight=1)
        row_settings.columnconfigure(1, weight=2)

        # Port
        port_box = ctk.CTkFrame(row_settings, fg_color="transparent")
        port_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        port_title = ctk.CTkLabel(
            port_box,
            text="UDP Dinleme Portu:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#C9D1D9"
        )
        port_title.pack(anchor="w", pady=(0, 4))

        self.port_entry = ctk.CTkEntry(
            port_box,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color="#0D1117",
            border_color="#30363D"
        )
        self.port_entry.insert(0, "50005")
        self.port_entry.pack(fill="x")

        # Jitter Slider
        jitter_box = ctk.CTkFrame(row_settings, fg_color="transparent")
        jitter_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.jitter_label = ctk.CTkLabel(
            jitter_box,
            text="Jitter Buffer: 25 ms (İdeal: 20-35ms)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#C9D1D9"
        )
        self.jitter_label.pack(anchor="w", pady=(0, 8))

        self.jitter_slider = ctk.CTkSlider(
            jitter_box,
            from_=10,
            to=100,
            number_of_steps=18,
            progress_color="#1F6FEB",
            button_color="#58A6FF",
            button_hover_color="#79C0FF",
            command=self._on_jitter_slider_change
        )
        self.jitter_slider.set(25)
        self.jitter_slider.pack(fill="x", pady=(2, 0))

        # 6. ALT AKSİYON BUTONLARI
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=18, pady=(4, 16))

        self.toggle_button = ctk.CTkButton(
            self.action_frame,
            text="▶  Hizmeti Başlat",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            height=46,
            corner_radius=10,
            fg_color="#238636",
            hover_color="#2EA043",
            command=self._toggle_service
        )
        self.toggle_button.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.tray_button = ctk.CTkButton(
            self.action_frame,
            text="Tepsiye Küçült",
            width=130,
            height=46,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            corner_radius=10,
            fg_color="#21262D",
            hover_color="#30363D",
            border_width=1,
            border_color="#30363D",
            command=self._minimize_to_tray
        )
        self.tray_button.pack(side="right")

    def _create_metric_card(self, parent, col, title, initial_val, accent_color):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#161B22", border_width=1, border_color="#21262D")
        card.grid(row=0, column=col, padx=4, sticky="nsew")

        lbl_t = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color="#8B949E"
        )
        lbl_t.pack(pady=(8, 0))

        lbl_v = ctk.CTkLabel(
            card,
            text=initial_val,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=accent_color
        )
        lbl_v.pack(pady=(2, 8))
        return lbl_v

    def _copy_ip(self):
        self.clipboard_clear()
        self.clipboard_append(self.primary_ip)
        self.copy_btn.configure(text="Kopyalandı! ✔", fg_color="#238636")
        self.after(1500, lambda: self.copy_btn.configure(text="Kopyala", fg_color="#21262D"))

    def _refresh_audio_devices(self):
        self.devices = AudioEngine.get_output_devices()
        device_names = []
        preferred_idx = 0

        for i, (idx, name, api) in enumerate(self.devices):
            display_name = f"[{idx}] {name} ({api})"
            device_names.append(display_name)
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
                    self.audio_engine.start(self.selected_device_index)
                break

    def _on_jitter_slider_change(self, value):
        val_int = int(value)
        self.jitter_label.configure(text=f"Jitter Buffer: {val_int} ms (İdeal: 20-35ms)")
        self.audio_engine.set_target_buffer_ms(val_int)

    def _on_vu_update(self, peak: float):
        display_val = min(1.0, peak * 1.5)
        self.after(0, lambda: self._update_vu_ui(display_val))

    def _update_vu_ui(self, val: float):
        self.vu_progress.set(val)
        percent = int(val * 100)
        self.vu_percent_label.configure(text=f"{percent}%")

        if val > 0.85:
            self.vu_progress.configure(progress_color="#DA3633")  # Kırpılma / Kırmızı
        elif val > 0.65:
            self.vu_progress.configure(progress_color="#D29922")  # Sarı
        else:
            self.vu_progress.configure(progress_color="#238636")  # Temiz Yeşil

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
            self.status_dot.configure(text_color="#3FB950")
            self.status_text.configure(text=f"SES AKIYOR ({client[0]})", text_color="#3FB950")
            self.status_pill.configure(border_color="#238636")
        else:
            self.status_dot.configure(text_color="#D29922")
            self.status_text.configure(text="BEKLENİYOR...", text_color="#D29922")
            self.status_pill.configure(border_color="#9E6A03")

        self.metric_latency.configure(text=f"{int(latency_ms)} ms")
        if latency_ms < 25:
            self.metric_latency.configure(text_color="#3FB950")
        elif latency_ms < 50:
            self.metric_latency.configure(text_color="#D29922")
        else:
            self.metric_latency.configure(text_color="#F85149")

        self.metric_jitter.configure(text=f"{jitter_ms:.1f} ms")
        self.metric_loss.configure(text=f"%{loss_pct:.1f}")
        self.metric_loss.configure(text_color="#F85149" if loss_pct > 2.0 else "#3FB950")
        self.metric_pps.configure(text=f"{pps} pps")

    def _toggle_service(self):
        if not self.is_active:
            try:
                port = int(self.port_entry.get().strip())
            except ValueError:
                port = 50005

            self.network_receiver.port = port
            self.audio_engine.start(self.selected_device_index)
            self.network_receiver.start()

            self.is_active = True
            self.toggle_button.configure(
                text="■  Hizmeti Durdur",
                fg_color="#DA3633",
                hover_color="#B62324",
            )
            self.status_dot.configure(text_color="#D29922")
            self.status_text.configure(text="BEKLENİYOR...", text_color="#D29922")
            self.status_pill.configure(border_color="#9E6A03")
            self.port_entry.configure(state="disabled")
        else:
            self.network_receiver.stop()
            self.audio_engine.stop()

            self.is_active = False
            self.toggle_button.configure(
                text="▶  Hizmeti Başlat",
                fg_color="#238636",
                hover_color="#2EA043",
            )
            self.status_dot.configure(text_color="#F85149")
            self.status_text.configure(text="DURDURULDU", text_color="#C9D1D9")
            self.status_pill.configure(border_color="#30363D")
            self.port_entry.configure(state="normal")
            self.vu_progress.set(0.0)
            self.vu_percent_label.configure(text="0%")

    def _minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            if os.path.exists(ICON_PATH):
                image = Image.open(ICON_PATH).resize((64, 64))
            else:
                image = Image.new("RGBA", (64, 64), color=(59, 130, 246))

            menu = pystray.Menu(
                pystray.MenuItem("mic2pc'yi Aç", self._restore_from_tray, default=True),
                pystray.MenuItem("Çıkış Yap", self._exit_application),
            )
            self.tray_icon = pystray.Icon("mic2pc", image, "mic2pc Receiver", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _restore_from_tray(self, icon=None, item=None):
        self.after(0, self.deiconify)

    def _on_close_button(self):
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
