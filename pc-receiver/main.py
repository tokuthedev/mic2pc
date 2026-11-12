"""
mic2pc - PC Virtual Microphone Receiver
Telefonunuzdan gelen UDP ses akışını yakalar, jitter buffer ile düzeltir
ve VB-CABLE / Virtual Audio Driver gibi sanal mikrofon girişine yönlendirir.
"""

import sys
import os

# Ana dizini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import run_app

if __name__ == "__main__":
    run_app()
