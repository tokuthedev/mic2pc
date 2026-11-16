import os
import sys
import socket
import threading
import time
import subprocess
import ctypes
from typing import List, Optional, Tuple, Dict
import customtkinter as ctk
import pystray
from PIL import Image

from audio_engine import AudioEngine
from network_receiver import NetworkReceiver

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(BASE_DIR, "icon.png")
ICO_PATH = os.path.join(BASE_DIR, "icon.ico")


def load_custom_fonts():
    """Windows oturumuna Manrope font ailesini geçici olarak kaydeder."""
    fonts_dir = os.path.join(BASE_DIR, "fonts")
    if os.path.exists(fonts_dir):
        FR_PRIVATE = 0x10
        for font_file in os.listdir(fonts_dir):
            if font_file.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(fonts_dir, font_file)
                try:
                    ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
                except Exception:
                    pass


# Manrope fontunu yükle
load_custom_fonts()
FONT_FAMILY = "Manrope"


def get_material_icon(icon_name: str, hex_color: str, size: Tuple[int, int] = (22, 22)) -> Optional[ctk.CTkImage]:
    """Material Symbols ikonunu belirtilen renkte ve boyutta dinamik üretir."""
    icon_file = os.path.join(BASE_DIR, "icons", f"{icon_name}.png")
    if not os.path.exists(icon_file):
        return None
    try:
        img = Image.open(icon_file).convert("RGBA")
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        _, _, _, alpha = img.split()
        colored = Image.merge(
            "RGBA",
            (
                alpha.point(lambda p: r if p > 0 else 0),
                alpha.point(lambda p: g if p > 0 else 0),
                alpha.point(lambda p: b if p > 0 else 0),
                alpha,
            ),
        )
        return ctk.CTkImage(light_image=colored, dark_image=colored, size=size)
    except Exception:
        return None

# Material Design 3 Renk Temaları
THEMES: Dict[str, Dict[str, str]] = {
    "Lavender": {
        "primary": "#D0BCFF",
        "on_primary": "#381E72",
        "primary_container": "#4F378B",
        "on_primary_container": "#EADDFF",
        "accent": "#7ADC9A",
    },
    "Sapphire": {
        "primary": "#A8C7FA",
        "on_primary": "#042B6B",
        "primary_container": "#0842A0",
        "on_primary_container": "#D3E3FD",
        "accent": "#6DD58C",
    },
    "Mint": {
        "primary": "#6DD58C",
        "on_primary": "#003915",
        "primary_container": "#0A5323",
        "on_primary_container": "#C4EED0",
        "accent": "#A8C7FA",
    },
    "Sunset": {
        "primary": "#FFB787",
        "on_primary": "#4F2500",
        "primary_container": "#703800",
        "on_primary_container": "#FFDCC5",
        "accent": "#6DD58C",
    },
    "Rose": {
        "primary": "#FFB1C8",
        "on_primary": "#5E1133",
        "primary_container": "#852349",
        "on_primary_container": "#FFD9E2",
        "accent": "#6DD58C",
    },
}

# Material 3 Dark Surface Renkleri
M3_SURFACE = "#141218"
M3_SURFACE_CONTAINER_LOW = "#1D1B20"
M3_SURFACE_CONTAINER = "#211F26"
M3_SURFACE_CONTAINER_HIGH = "#2B2930"
M3_SURFACE_CONTAINER_HIGHEST = "#36343B"
M3_ON_SURFACE = "#E6E0E9"
M3_ON_SURFACE_VARIANT = "#CAC4D0"
M3_OUTLINE = "#49454F"
M3_SECONDARY_CONTAINER = "#4A4458"
M3_ON_SECONDARY_CONTAINER = "#E8DEF8"
M3_ERROR = "#F2B8B5"
M3_ON_ERROR = "#601410"

STRINGS: Dict[str, Dict[str, str]] = {
    "tr": {
        "title": "mic2pc • Material 3 Sanal Mikrofon",
        "nav_stream": "  Yayın",
        "nav_stats": "  İstatistikler",
        "nav_settings": "  Ayarlar",
        "status_stopped": "Durduruldu",
        "status_waiting": "Bekleniyor",
        "status_streaming": "Ses Akıyor",
        "ip_label": "Telefondan Bağlanılacak IP: ",
        "copy": "Kopyala",
        "copied": "Kopyalandı! ✔",
        "metric_latency": "Gecikme (Ping)",
        "metric_jitter": "Jitter",
        "metric_loss": "Paket Kaybı",
        "metric_pps": "Paket/sn",
        "vu_title": "Canlı Mikrofon Seviyesi",
        "output_device_label": "Aktif Ses Çıkışı (Discord / Oyunlar için VB-CABLE):",
        "btn_start": "▶  Hizmeti Başlat",
        "btn_stop": "■  Hizmeti Durdur",
        "stats_title": "Ağ ve Ses Tanılama",
        "stat_client": "Bağlı Mobil Cihaz:",
        "stat_latency": "Ortalama Ağ Gecikmesi:",
        "stat_jitter": "Jitter Dalgalanması:",
        "stat_loss": "Kayıp Paket Oranı:",
        "stat_packets": "Toplam Alınan Paket:",
        "stat_rate": "Anlık Akış Hızı:",
        "stat_buffer": "Jitter Buffer Doluluğu:",
        "stat_gain": "Aktif Kazanç (Gain):",
        "stat_client_default": "Bağlantı bekleniyor...",
        "stat_buffer_default": "25 ms (Stabil)",
        "stat_gain_default": "1.0x (Varsayılan)",
        "settings_title": "Uygulama ve Ses Ayarları",
        "lang_section": "🌐  Dil / Language",
        "theme_section": "🎨  Material 3 Renk Teması",
        "gain_section": "🔊  Mikrofon Kazancı (Gain Booster)",
        "gain_desc": "Kazanç: {}x — Sesi az giden telefonlar için artırın",
        "net_section": "🌐  Ağ ve Gecikme Ayarları",
        "jitter_desc": "Jitter Buffer: {} ms (İdeal: 20-35ms)",
        "port_label": "UDP Dinleme Portu:",
        "firewall_section": "🛡️  Sistem İzinleri ve Güvenlik Duvarı",
        "firewall_desc": "Windows'un her açılışta izin sormasını kalıcı olarak engellemek için tek tıkla kural ekleyin.",
        "firewall_btn": "🛡️  Güvenlik Duvarına Kalıcı İzin Ekle",
        "tray_open": "mic2pc'yi Aç",
        "tray_exit": "Çıkış Yap",
    },
    "en": {
        "title": "mic2pc • Material 3 Virtual Microphone",
        "nav_stream": "  Stream",
        "nav_stats": "  Analytics",
        "nav_settings": "  Settings",
        "status_stopped": "Stopped",
        "status_waiting": "Waiting",
        "status_streaming": "Streaming",
        "ip_label": "Connect via Phone IP: ",
        "copy": "Copy",
        "copied": "Copied! ✔",
        "metric_latency": "Latency (Ping)",
        "metric_jitter": "Jitter",
        "metric_loss": "Packet Loss",
        "metric_pps": "Packets/s",
        "vu_title": "Live Microphone Level",
        "output_device_label": "Active Audio Output (VB-CABLE for Discord / Games):",
        "btn_start": "▶  Start Service",
        "btn_stop": "■  Stop Service",
        "stats_title": "Network & Audio Diagnostics",
        "stat_client": "Connected Mobile Device:",
        "stat_latency": "Average Network Latency:",
        "stat_jitter": "Jitter Fluctuation:",
        "stat_loss": "Packet Loss Ratio:",
        "stat_packets": "Total Received Packets:",
        "stat_rate": "Instant Stream Rate:",
        "stat_buffer": "Jitter Buffer Occupancy:",
        "stat_gain": "Active Gain:",
        "stat_client_default": "Waiting for connection...",
        "stat_buffer_default": "25 ms (Stable)",
        "stat_gain_default": "1.0x (Default)",
        "settings_title": "Application & Audio Settings",
        "lang_section": "🌐  Language / Dil",
        "theme_section": "🎨  Material 3 Color Theme",
        "gain_section": "🔊  Microphone Gain Booster",
        "gain_desc": "Gain: {}x — Increase for quiet phone microphones",
        "net_section": "🌐  Network & Latency Settings",
        "jitter_desc": "Jitter Buffer: {} ms (Ideal: 20-35ms)",
        "port_label": "UDP Listening Port:",
        "firewall_section": "🛡️  System Permissions & Firewall",
        "firewall_desc": "Add a permanent firewall rule with one click to stop Windows asking every launch.",
        "firewall_btn": "🛡️  Add Permanent Firewall Rule",
        "tray_open": "Open mic2pc",
        "tray_exit": "Exit",
    },
}


def get_local_ip_addresses() -> List[str]:
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

        self.current_lang = "tr"
        self.title(self.t("title"))
        self.geometry("860x680")
        self.minsize(780, 620)
        self.configure(fg_color=M3_SURFACE)

        if os.path.exists(ICO_PATH):
            try:
                self.iconbitmap(ICO_PATH)
            except Exception:
                pass

        # Aktif Tema
        self.current_theme_name = "Lavender"
        self.theme = THEMES[self.current_theme_name]

        # Ses ve Ağ Motoru
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

        # UI Navigasyon
        self.active_tab = "stream"
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self.tab_frames: Dict[str, ctk.CTkFrame] = {}

        self._build_main_layout()

        # Sistem tepsisi entegrasyonu
        self.tray_icon: Optional[pystray.Icon] = None
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)

        self._refresh_audio_devices()

    def t(self, key: str, *args) -> str:
        lang_dict = STRINGS.get(self.current_lang, STRINGS["tr"])
        val = lang_dict.get(key, key)
        if args:
            try:
                return val.format(*args)
            except Exception:
                return val
        return val

    def _build_main_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---------------- SOL: M3 NAVIGATION RAIL ----------------
        self.nav_rail = ctk.CTkFrame(
            self,
            width=200,
            corner_radius=0,
            fg_color=M3_SURFACE_CONTAINER_LOW,
            border_width=0,
        )
        self.nav_rail.grid(row=0, column=0, sticky="nsew")
        self.nav_rail.grid_propagate(False)

        # Üst Başlık & Logo
        logo_frame = ctk.CTkFrame(self.nav_rail, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 24))

        if os.path.exists(ICON_PATH):
            try:
                pil_logo = Image.open(ICON_PATH).resize((38, 38), Image.Resampling.LANCZOS)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(38, 38))
                lbl_logo = ctk.CTkLabel(logo_frame, text="", image=self.logo_img)
                lbl_logo.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        lbl_app_name = ctk.CTkLabel(
            logo_frame,
            text="mic2pc",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        lbl_app_name.pack(side="left")

        # Navigasyon Butonları
        self.nav_icons = {
            "stream": "wifi_tethering",
            "stats": "analytics",
            "settings": "settings"
        }
        self._create_nav_button("stream", self.t("nav_stream"), "wifi_tethering")
        self._create_nav_button("stats", self.t("nav_stats"), "analytics")
        self._create_nav_button("settings", self.t("nav_settings"), "settings")

        # Alt Kısım: Durum Hapı
        self.nav_status_frame = ctk.CTkFrame(
            self.nav_rail,
            corner_radius=16,
            fg_color=M3_SURFACE_CONTAINER_HIGH,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        self.nav_status_frame.pack(side="bottom", fill="x", padx=14, pady=18)

        self.nav_status_dot = ctk.CTkLabel(
            self.nav_status_frame,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=M3_ERROR,
        )
        self.nav_status_dot.pack(side="left", padx=(10, 4), pady=6)

        self.nav_status_lbl = ctk.CTkLabel(
            self.nav_status_frame,
            text=self.t("status_stopped"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        self.nav_status_lbl.pack(side="left", padx=(0, 10), pady=6)

        # ---------------- SAĞ: İÇERİK ALANI ----------------
        self.content_area = ctk.CTkFrame(self, fg_color=M3_SURFACE, corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=16)

        # Sekmeleri Oluştur
        self._build_stream_tab()
        self._build_stats_tab()
        self._build_settings_tab()

        # Varsayılan sekmeyi aç
        self._select_tab("stream")

    def _create_nav_button(self, tab_id: str, label: str, icon_name: str):
        icon_img = get_material_icon(icon_name, M3_ON_SURFACE_VARIANT, size=(22, 22))
        btn = ctk.CTkButton(
            self.nav_rail,
            text=label,
            image=icon_img,
            compound="left",
            height=46,
            corner_radius=23,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            anchor="w",
            fg_color="transparent",
            hover_color=M3_SURFACE_CONTAINER_HIGH,
            text_color=M3_ON_SURFACE_VARIANT,
            command=lambda: self._select_tab(tab_id),
        )
        btn.pack(fill="x", padx=12, pady=4)
        self.nav_buttons[tab_id] = btn

    def _select_tab(self, tab_id: str):
        self.active_tab = tab_id
        for tid, btn in self.nav_buttons.items():
            icon_name = self.nav_icons.get(tid, "")
            if tid == tab_id:
                active_icon = get_material_icon(icon_name, self.theme["on_primary_container"], size=(22, 22))
                btn.configure(
                    fg_color=self.theme["primary_container"],
                    text_color=self.theme["on_primary_container"],
                    image=active_icon,
                )
            else:
                inactive_icon = get_material_icon(icon_name, M3_ON_SURFACE_VARIANT, size=(22, 22))
                btn.configure(
                    fg_color="transparent",
                    text_color=M3_ON_SURFACE_VARIANT,
                    image=inactive_icon,
                )

        for tid, frame in self.tab_frames.items():
            if tid == tab_id:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # ================= 1. YAYIN SEKMESİ (STREAM) =================
    def _build_stream_tab(self):
        tab = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_frames["stream"] = tab

        # IP Kartı
        ip_card = ctk.CTkFrame(
            tab,
            corner_radius=20,
            fg_color=M3_SURFACE_CONTAINER,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        ip_card.pack(fill="x", pady=(0, 12))

        local_ips = get_local_ip_addresses()
        self.primary_ip = local_ips[0] if local_ips else "127.0.0.1"

        ip_content = ctk.CTkFrame(ip_card, fg_color="transparent")
        ip_content.pack(fill="x", padx=18, pady=12)

        ctk.CTkLabel(ip_content, text="📡", font=ctk.CTkFont(family=FONT_FAMILY, size=18)).pack(side="left", padx=(0, 8))
        self.lbl_ip_prompt = ctk.CTkLabel(
            ip_content,
            text=self.t("ip_label"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=M3_ON_SURFACE_VARIANT,
        )
        self.lbl_ip_prompt.pack(side="left")

        self.ip_badge = ctk.CTkLabel(
            ip_content,
            text=f" {self.primary_ip} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=M3_SURFACE_CONTAINER_HIGHEST,
            corner_radius=10,
            text_color=self.theme["primary"],
        )
        self.ip_badge.pack(side="left", padx=(0, 10))

        self.copy_btn = ctk.CTkButton(
            ip_content,
            text=self.t("copy"),
            width=76,
            height=30,
            corner_radius=15,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=self.theme["primary_container"],
            text_color=self.theme["on_primary_container"],
            command=self._copy_ip,
        )
        self.copy_btn.pack(side="right")

        # Hızlı Metrik Kartları
        metrics_container = ctk.CTkFrame(tab, fg_color="transparent")
        metrics_container.pack(fill="x", pady=(0, 12))
        metrics_container.columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")

        self.metric_latency, self.lbl_m_lat = self._create_metric_box(metrics_container, 0, self.t("metric_latency"), "0 ms", self.theme["primary"])
        self.metric_jitter, self.lbl_m_jit = self._create_metric_box(metrics_container, 1, self.t("metric_jitter"), "0.0 ms", self.theme["accent"])
        self.metric_loss, self.lbl_m_loss = self._create_metric_box(metrics_container, 2, self.t("metric_loss"), "%0.0", self.theme["accent"])
        self.metric_pps, self.lbl_m_pps = self._create_metric_box(metrics_container, 3, self.t("metric_pps"), "0 pps", M3_ON_SURFACE)

        # Canlı VU Meter Kartı
        vu_card = ctk.CTkFrame(
            tab,
            corner_radius=20,
            fg_color=M3_SURFACE_CONTAINER,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        vu_card.pack(fill="x", pady=(0, 14))

        vu_header = ctk.CTkFrame(vu_card, fg_color="transparent")
        vu_header.pack(fill="x", padx=18, pady=(12, 6))

        self.lbl_vu_title = ctk.CTkLabel(
            vu_header,
            text=self.t("vu_title"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        self.lbl_vu_title.pack(side="left")

        self.vu_percent_label = ctk.CTkLabel(
            vu_header,
            text="0%",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=M3_ON_SURFACE_VARIANT,
        )
        self.vu_percent_label.pack(side="right")

        self.vu_progress = ctk.CTkProgressBar(
            vu_card,
            height=14,
            corner_radius=7,
            fg_color=M3_SURFACE_CONTAINER_HIGHEST,
            progress_color=self.theme["accent"],
        )
        self.vu_progress.pack(fill="x", padx=18, pady=(0, 14))
        self.vu_progress.set(0.0)

        # Hızlı Ayar Seçici (Çıkış Aygıtı)
        quick_card = ctk.CTkFrame(
            tab,
            corner_radius=20,
            fg_color=M3_SURFACE_CONTAINER,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        quick_card.pack(fill="x", pady=(0, 16))

        self.lbl_output_dev = ctk.CTkLabel(
            quick_card,
            text=self.t("output_device_label"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        self.lbl_output_dev.pack(anchor="w", padx=18, pady=(12, 4))

        self.dev_combo = ctk.CTkComboBox(
            quick_card,
            height=36,
            corner_radius=12,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=M3_SURFACE_CONTAINER_HIGHEST,
            border_color=M3_OUTLINE,
            button_color=M3_SURFACE_CONTAINER_HIGH,
            values=["Loading..."],
            command=self._on_device_selected,
        )
        self.dev_combo.pack(fill="x", padx=18, pady=(0, 14))

        # Alt Büyük Başlat/Durdur Butonu
        self.toggle_button = ctk.CTkButton(
            tab,
            text=self.t("btn_start"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            height=54,
            corner_radius=27,
            fg_color=self.theme["primary"],
            text_color=self.theme["on_primary"],
            hover_color=self.theme["primary_container"],
            command=self._toggle_service,
        )
        self.toggle_button.pack(fill="x", pady=(4, 0))

    def _create_metric_box(self, parent, col, title, initial_val, accent_color):
        card = ctk.CTkFrame(
            parent,
            corner_radius=18,
            fg_color=M3_SURFACE_CONTAINER,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        card.grid(row=0, column=col, padx=4, sticky="nsew")

        lbl_title = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=M3_ON_SURFACE_VARIANT,
        )
        lbl_title.pack(pady=(10, 0))

        lbl_v = ctk.CTkLabel(
            card,
            text=initial_val,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=accent_color,
        )
        lbl_v.pack(pady=(2, 10))
        return lbl_v, lbl_title

    # ================= 2. İSTATİSTİKLER SEKMESİ (STATS) =================
    def _build_stats_tab(self):
        tab = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_frames["stats"] = tab

        self.lbl_stats_title = ctk.CTkLabel(
            tab,
            text=self.t("stats_title"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        self.lbl_stats_title.pack(anchor="w", pady=(0, 12))

        # Detaylar Kartı
        stats_card = ctk.CTkFrame(
            tab,
            corner_radius=20,
            fg_color=M3_SURFACE_CONTAINER,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        stats_card.pack(fill="both", expand=True, pady=(0, 12))

        content = ctk.CTkFrame(stats_card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=16)

        self.diag_labels: Dict[str, ctk.CTkLabel] = {}
        self.diag_title_labels: Dict[str, ctk.CTkLabel] = {}
        items = [
            ("client", "stat_client", self.t("stat_client_default")),
            ("latency", "stat_latency", "0 ms"),
            ("jitter", "stat_jitter", "0.0 ms"),
            ("loss", "stat_loss", "%0.0"),
            ("packets", "stat_packets", "0"),
            ("rate", "stat_rate", "0 pps (~0 kbps)"),
            ("buffer", "stat_buffer", self.t("stat_buffer_default")),
            ("gain", "stat_gain", self.t("stat_gain_default")),
        ]

        for i, (key, str_key, default_val) in enumerate(items):
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x", pady=6)

            t_lbl = ctk.CTkLabel(
                row,
                text=self.t(str_key),
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=M3_ON_SURFACE_VARIANT,
            )
            t_lbl.pack(side="left")
            self.diag_title_labels[key] = t_lbl

            val_lbl = ctk.CTkLabel(
                row,
                text=default_val,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=M3_ON_SURFACE,
            )
            val_lbl.pack(side="right")
            self.diag_labels[key] = val_lbl

    # ================= 3. AYARLAR SEKMESİ (SETTINGS) =================
    def _build_settings_tab(self):
        tab = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color="transparent",
            corner_radius=0,
        )
        self.tab_frames["settings"] = tab

        self.lbl_settings_head = ctk.CTkLabel(
            tab,
            text=self.t("settings_title"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        self.lbl_settings_head.pack(anchor="w", pady=(0, 14))

        # 0. DİL SEÇİMİ (LANGUAGE)
        self.card_lang, self.lbl_card_lang = self._create_settings_card(tab, self.t("lang_section"))

        lang_btn_row = ctk.CTkFrame(self.card_lang, fg_color="transparent")
        lang_btn_row.pack(fill="x", padx=18, pady=(4, 16))

        self.btn_lang_tr = ctk.CTkButton(
            lang_btn_row,
            text="Türkçe",
            width=90,
            height=34,
            corner_radius=17,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=lambda: self.set_language("tr"),
        )
        self.btn_lang_tr.pack(side="left", padx=(0, 8))

        self.btn_lang_en = ctk.CTkButton(
            lang_btn_row,
            text="English",
            width=90,
            height=34,
            corner_radius=17,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=lambda: self.set_language("en"),
        )
        self.btn_lang_en.pack(side="left")
        self._update_lang_buttons()

        # 1. TEMA VE RENK PALETİ
        self.card_theme, self.lbl_card_theme = self._create_settings_card(tab, self.t("theme_section"))

        theme_btn_row = ctk.CTkFrame(self.card_theme, fg_color="transparent")
        theme_btn_row.pack(fill="x", padx=18, pady=(4, 16))

        for tname, tcolors in THEMES.items():
            btn = ctk.CTkButton(
                theme_btn_row,
                text=tname,
                width=80,
                height=34,
                corner_radius=17,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                fg_color=tcolors["primary"],
                text_color=tcolors["on_primary"],
                hover_color=tcolors["primary_container"],
                command=lambda n=tname: self._apply_theme(n),
            )
            btn.pack(side="left", padx=4)

        # 2. MİKROFON KAZANCI (GAIN BOOSTER)
        self.card_gain, self.lbl_card_gain = self._create_settings_card(tab, self.t("gain_section"))

        self.gain_val_lbl = ctk.CTkLabel(
            self.card_gain,
            text=self.t("gain_desc", 1.0),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=M3_ON_SURFACE_VARIANT,
        )
        self.gain_val_lbl.pack(anchor="w", padx=18, pady=(4, 6))

        self.gain_slider = ctk.CTkSlider(
            self.card_gain,
            from_=0.5,
            to=3.0,
            number_of_steps=25,
            progress_color=self.theme["primary"],
            button_color=self.theme["primary"],
            command=self._on_gain_slider_change,
        )
        self.gain_slider.set(1.0)
        self.gain_slider.pack(fill="x", padx=18, pady=(0, 16))

        # 3. JITTER BUFFER VE UDP PORT
        self.card_net, self.lbl_card_net = self._create_settings_card(tab, self.t("net_section"))

        self.jitter_val_lbl = ctk.CTkLabel(
            self.card_net,
            text=self.t("jitter_desc", 25),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=M3_ON_SURFACE_VARIANT,
        )
        self.jitter_val_lbl.pack(anchor="w", padx=18, pady=(4, 6))

        self.jitter_slider = ctk.CTkSlider(
            self.card_net,
            from_=10,
            to=100,
            number_of_steps=18,
            progress_color=self.theme["primary"],
            button_color=self.theme["primary"],
            command=self._on_jitter_slider_change,
        )
        self.jitter_slider.set(25)
        self.jitter_slider.pack(fill="x", padx=18, pady=(0, 14))

        # UDP Port Alanı
        port_row = ctk.CTkFrame(self.card_net, fg_color="transparent")
        port_row.pack(fill="x", padx=18, pady=(0, 16))

        self.lbl_port = ctk.CTkLabel(
            port_row,
            text=self.t("port_label"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        self.lbl_port.pack(side="left", padx=(0, 12))

        self.port_entry = ctk.CTkEntry(
            port_row,
            width=100,
            height=32,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=M3_SURFACE_CONTAINER_HIGHEST,
            border_color=M3_OUTLINE,
        )
        self.port_entry.insert(0, "50005")
        self.port_entry.pack(side="left")

        # 4. GÜVENLİK DUVARI VE ARAÇLAR
        self.card_firewall, self.lbl_card_firewall = self._create_settings_card(tab, self.t("firewall_section"))

        self.lbl_firewall_desc = ctk.CTkLabel(
            self.card_firewall,
            text=self.t("firewall_desc"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=M3_ON_SURFACE_VARIANT,
        )
        self.lbl_firewall_desc.pack(anchor="w", padx=18, pady=(4, 10))

        self.firewall_btn = ctk.CTkButton(
            self.card_firewall,
            text=self.t("firewall_btn"),
            height=36,
            corner_radius=18,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=M3_SURFACE_CONTAINER_HIGHEST,
            hover_color=M3_SECONDARY_CONTAINER,
            text_color=M3_ON_SURFACE,
            border_width=1,
            border_color=M3_OUTLINE,
            command=self._run_firewall_fix,
        )
        self.firewall_btn.pack(anchor="w", padx=18, pady=(0, 16))

    def _create_settings_card(self, parent, title: str) -> Tuple[ctk.CTkFrame, ctk.CTkLabel]:
        card = ctk.CTkFrame(
            parent,
            corner_radius=20,
            fg_color=M3_SURFACE_CONTAINER,
            border_width=1,
            border_color=M3_OUTLINE,
        )
        card.pack(fill="x", pady=(0, 12))

        lbl = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=M3_ON_SURFACE,
        )
        lbl.pack(anchor="w", padx=18, pady=(14, 4))
        return card, lbl

    def set_language(self, lang_code: str):
        if lang_code not in STRINGS:
            return
        self.current_lang = lang_code
        self.title(self.t("title"))

        # Navigasyon
        self.nav_buttons["stream"].configure(text=self.t("nav_stream"))
        self.nav_buttons["stats"].configure(text=self.t("nav_stats"))
        self.nav_buttons["settings"].configure(text=self.t("nav_settings"))

        # Durum
        if not self.is_active:
            self.nav_status_lbl.configure(text=self.t("status_stopped"))
            self.toggle_button.configure(text=self.t("btn_start"))
        else:
            client = self.network_receiver.connected_client
            self.nav_status_lbl.configure(text=self.t("status_streaming") if client else self.t("status_waiting"))
            self.toggle_button.configure(text=self.t("btn_stop"))

        # Yayın Sekmesi
        self.lbl_ip_prompt.configure(text=self.t("ip_label"))
        self.copy_btn.configure(text=self.t("copy"))
        self.lbl_m_lat.configure(text=self.t("metric_latency"))
        self.lbl_m_jit.configure(text=self.t("metric_jitter"))
        self.lbl_m_loss.configure(text=self.t("metric_loss"))
        self.lbl_m_pps.configure(text=self.t("metric_pps"))
        self.lbl_vu_title.configure(text=self.t("vu_title"))
        self.lbl_output_dev.configure(text=self.t("output_device_label"))

        # İstatistikler Sekmesi
        self.lbl_stats_title.configure(text=self.t("stats_title"))
        str_keys = {
            "client": "stat_client",
            "latency": "stat_latency",
            "jitter": "stat_jitter",
            "loss": "stat_loss",
            "packets": "stat_packets",
            "rate": "stat_rate",
            "buffer": "stat_buffer",
            "gain": "stat_gain",
        }
        for k, sk in str_keys.items():
            if k in self.diag_title_labels:
                self.diag_title_labels[k].configure(text=self.t(sk))

        # Ayarlar Sekmesi
        self.lbl_settings_head.configure(text=self.t("settings_title"))
        self.lbl_card_lang.configure(text=self.t("lang_section"))
        self.lbl_card_theme.configure(text=self.t("theme_section"))
        self.lbl_card_gain.configure(text=self.t("gain_section"))
        self.lbl_card_net.configure(text=self.t("net_section"))
        self.lbl_port.configure(text=self.t("port_label"))
        self.lbl_card_firewall.configure(text=self.t("firewall_section"))
        self.lbl_firewall_desc.configure(text=self.t("firewall_desc"))
        self.firewall_btn.configure(text=self.t("firewall_btn"))

        gain_val = round(self.gain_slider.get(), 1)
        self.gain_val_lbl.configure(text=self.t("gain_desc", gain_val))
        buf_val = int(self.jitter_slider.get())
        self.jitter_val_lbl.configure(text=self.t("jitter_desc", buf_val))

        self._update_lang_buttons()

    def _update_lang_buttons(self):
        if self.current_lang == "tr":
            self.btn_lang_tr.configure(
                fg_color=self.theme["primary"],
                text_color=self.theme["on_primary"],
            )
            self.btn_lang_en.configure(
                fg_color=M3_SURFACE_CONTAINER_HIGHEST,
                text_color=M3_ON_SURFACE,
            )
        else:
            self.btn_lang_en.configure(
                fg_color=self.theme["primary"],
                text_color=self.theme["on_primary"],
            )
            self.btn_lang_tr.configure(
                fg_color=M3_SURFACE_CONTAINER_HIGHEST,
                text_color=M3_ON_SURFACE,
            )

    def _apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            return
        self.current_theme_name = theme_name
        self.theme = THEMES[theme_name]

        # Navigasyon butonunu güncelle
        for tid, btn in self.nav_buttons.items():
            icon_name = self.nav_icons.get(tid, "")
            if tid == self.active_tab:
                active_icon = get_material_icon(icon_name, self.theme["on_primary_container"], size=(22, 22))
                btn.configure(
                    fg_color=self.theme["primary_container"],
                    text_color=self.theme["on_primary_container"],
                    image=active_icon,
                )

        # Ana buton ve elemanları güncelle
        if not self.is_active:
            self.toggle_button.configure(
                fg_color=self.theme["primary"],
                text_color=self.theme["on_primary"],
                hover_color=self.theme["primary_container"],
            )

        self.ip_badge.configure(text_color=self.theme["primary"])
        self.copy_btn.configure(
            fg_color=self.theme["primary_container"],
            text_color=self.theme["on_primary_container"],
        )
        self.vu_progress.configure(progress_color=self.theme["accent"])
        self.gain_slider.configure(
            progress_color=self.theme["primary"],
            button_color=self.theme["primary"],
        )
        self.jitter_slider.configure(
            progress_color=self.theme["primary"],
            button_color=self.theme["primary"],
        )
        self.metric_latency.configure(text_color=self.theme["primary"])
        self._update_lang_buttons()

    def _on_gain_slider_change(self, val: float):
        rounded = round(val, 1)
        self.gain_val_lbl.configure(text=self.t("gain_desc", rounded))
        self.audio_engine.set_gain(rounded)
        if "gain" in self.diag_labels:
            self.diag_labels["gain"].configure(text=f"{rounded}x")

    def _on_jitter_slider_change(self, value):
        val_int = int(value)
        self.jitter_val_lbl.configure(text=self.t("jitter_desc", val_int))
        self.audio_engine.set_target_buffer_ms(val_int)
        if "buffer" in self.diag_labels:
            self.diag_labels["buffer"].configure(text=f"{val_int} ms")

    def _copy_ip(self):
        self.clipboard_clear()
        self.clipboard_append(self.primary_ip)
        self.copy_btn.configure(text=self.t("copied"), fg_color=self.theme["accent"], text_color="#003915")
        self.after(1500, lambda: self.copy_btn.configure(text=self.t("copy"), fg_color=self.theme["primary_container"], text_color=self.theme["on_primary_container"]))

    def _run_firewall_fix(self):
        bat_path = os.path.join(os.path.dirname(BASE_DIR), "fix_firewall.bat")
        if not os.path.exists(bat_path):
            bat_path = os.path.join(BASE_DIR, "fix_firewall.bat")

        if os.path.exists(bat_path):
            subprocess.Popen(["cmd.exe", "/c", bat_path], shell=True)
        else:
            cmd = 'Start-Process netsh -ArgumentList "advfirewall firewall add rule name=\\"mic2pc UDP 50005\\" dir=in action=allow protocol=UDP localport=50005 profile=any" -Verb RunAs'
            subprocess.Popen(["powershell.exe", "-Command", cmd], shell=True)

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

    def _on_vu_update(self, peak: float):
        display_val = min(1.0, peak * 1.5)
        self.after(0, lambda: self._update_vu_ui(display_val))

    def _update_vu_ui(self, val: float):
        self.vu_progress.set(val)
        percent = int(val * 100)
        self.vu_percent_label.configure(text=f"{percent}%")

        if val > 0.85:
            self.vu_progress.configure(progress_color=M3_ERROR)
        elif val > 0.65:
            self.vu_progress.configure(progress_color="#FFD700")
        else:
            self.vu_progress.configure(progress_color=self.theme["accent"])

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
            self.nav_status_dot.configure(text_color=self.theme["accent"])
            self.nav_status_lbl.configure(text=self.t("status_streaming"))
        else:
            self.nav_status_dot.configure(text_color="#FFD700")
            self.nav_status_lbl.configure(text=self.t("status_waiting"))

        # Hızlı Metrikler
        self.metric_latency.configure(text=f"{int(latency_ms)} ms")
        self.metric_jitter.configure(text=f"{jitter_ms:.1f} ms")
        self.metric_loss.configure(text=f"%{loss_pct:.1f}")
        self.metric_pps.configure(text=f"{pps} pps")

        # İstatistikler Sekmesi Güncellemesi
        if hasattr(self, "diag_labels"):
            if client and "client" in self.diag_labels:
                self.diag_labels["client"].configure(text=f"{client[0]}:{client[1]}")
            if "latency" in self.diag_labels:
                self.diag_labels["latency"].configure(text=f"{int(latency_ms)} ms")
            if "jitter" in self.diag_labels:
                self.diag_labels["jitter"].configure(text=f"{jitter_ms:.1f} ms")
            if "loss" in self.diag_labels:
                self.diag_labels["loss"].configure(text=f"%{loss_pct:.1f}")
            if "packets" in self.diag_labels:
                self.diag_labels["packets"].configure(text=str(self.network_receiver.total_packets_received))
            if "rate" in self.diag_labels:
                kbps = (pps * 974 * 8) // 1000
                self.diag_labels["rate"].configure(text=f"{pps} pps (~{kbps} kbps)")

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
                text=self.t("btn_stop"),
                fg_color=M3_ERROR,
                hover_color="#DC3545",
                text_color=M3_ON_ERROR,
            )
            self.nav_status_dot.configure(text_color="#FFD700")
            self.nav_status_lbl.configure(text=self.t("status_waiting"))
            self.port_entry.configure(state="disabled")
        else:
            self.network_receiver.stop()
            self.audio_engine.stop()

            self.is_active = False
            self.toggle_button.configure(
                text=self.t("btn_start"),
                fg_color=self.theme["primary"],
                hover_color=self.theme["primary_container"],
                text_color=self.theme["on_primary"],
            )
            self.nav_status_dot.configure(text_color=M3_ERROR)
            self.nav_status_lbl.configure(text=self.t("status_stopped"))
            self.port_entry.configure(state="normal")
            self.vu_progress.set(0.0)
            self.vu_percent_label.configure(text="0%")

    def _minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            if os.path.exists(ICON_PATH):
                image = Image.open(ICON_PATH).resize((64, 64))
            else:
                image = Image.new("RGBA", (64, 64), color=(208, 188, 255))

            menu = pystray.Menu(
                pystray.MenuItem(self.t("tray_open"), self._restore_from_tray, default=True),
                pystray.MenuItem(self.t("tray_exit"), self._exit_application),
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
