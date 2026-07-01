#!/usr/bin/env python3
"""
QPSK Modulatör — GNU Radio Blok Implementasyonu
TÜBİTAK Uzay Stajı | Duru Evcim | 01 Temmuz 2026

Orijinal qpsk_modulator.py ile karşılaştırma:
  - Aynı parametreler (fs, fc, sps, seed, bit sayısı)
  - Aynı sembol haritalama (00→+1+j, 01→-1+j, 10→+1-j, 11→-1-j)
  - Aynı FIR katsayıları [1,2,5,8,8,5,2,1] / 32
  - NumPy işlemleri yerine GNU Radio blokları kullanılıyor

Blok zinciri:
  vector_source_b
      → pack_k_bits_bb(2)        [2 bit → 1 sembol indeksi]
      → chunks_to_symbols_bc     [indeks → I+jQ]
      → repeat(sps)              [upsample]
      → fir_filter_ccf           [pulse shaping]
      ┌────────────────────────────┤
      ↓ (baseband sink)     ↓ (passband yolu)
  vector_sink_c         multiply_cc ← sig_source_c(-fc)
                              ↓
                        complex_to_real
                              ↓
                        vector_sink_f
"""

import numpy as np
import matplotlib.pyplot as plt
from gnuradio import gr, blocks, digital, analog
from gnuradio import filter as gr_filter

# ─── PARAMETRELER (orijinal modülatörle aynı) ────────────────────────────────
FS  = 1_000_000   # Örnekleme frekansı: 1 MHz
FC  = 100_000     # Taşıyıcı frekansı:  100 kHz
SPS = 10          # Sembol başına örnek sayısı

np.random.seed(42)
BITLER = np.random.randint(0, 2, 64).astype(np.uint8)


# ─── GNU RADIO FLOWGRAPH ─────────────────────────────────────────────────────
class QPSK_Modulatör_GR(gr.top_block):
    """GNU Radio blokları ile QPSK modülatör flowgraph'ı."""

    def __init__(self, bitler, fs=FS, fc=FC, sps=SPS):
        gr.top_block.__init__(self, "QPSK Modulatör")

        # ── 1. BİT KAYNAĞI ────────────────────────────────────────────────
        self.kaynak = blocks.vector_source_b(bitler.tolist(), repeat=False)

        # ── 2. BİT PAKETLEME: 2 bit → 1 sembol indeksi ───────────────────
        # [b1, b2] → b1*2 + b2
        # [0,0]→0  [0,1]→1  [1,0]→2  [1,1]→3
        self.paket = blocks.pack_k_bits_bb(2)

        # ── 3. SEMBOL HARITALAMA: indeks → I+jQ ──────────────────────────
        # Orijinal qpsk_modulator.py ile birebir aynı haritalama:
        #   0(00) → +1+j   1(01) → -1+j   2(10) → +1-j   3(11) → -1-j
        d = 1.0 / np.sqrt(2)
        const = [
             d + d*1j,   # 0 → 00
            -d + d*1j,   # 1 → 01
             d - d*1j,   # 2 → 10
            -d - d*1j,   # 3 → 11
        ]
        self.haritalayici = digital.chunks_to_symbols_bc(const, 1)

        # ── 4. UPSAMPLE ───────────────────────────────────────────────────
        self.tekrarla = blocks.repeat(gr.sizeof_gr_complex, sps)

        # ── 5. FIR PULSE SHAPING FİLTRESİ ────────────────────────────────
        # Katsayılar orijinalle aynı; toplam 32 = 2^5 → /32 ile normalize
        taps = np.array([1, 2, 5, 8, 8, 5, 2, 1], dtype=float) / 32.0
        self.fir = gr_filter.fir_filter_ccf(1, taps.tolist())

        # ── 6. TAŞIYICI × BASEBAND → PASSBAND ────────────────────────────
        # sig_source_c(freq=-fc) → e^{-j2πft} = cos(2πft) - j·sin(2πft)
        # (I+jQ) · e^{-j2πft} → Re{·} = I·cos(2πft) + Q·sin(2πft)
        # Bu sayede orijinal modülatörle aynı convention korunuyor.
        self.tasiyici = analog.sig_source_c(fs, analog.GR_SIN_WAVE, -fc, 1.0, 0.0)
        self.carpici  = blocks.multiply_cc()

        # ── 7. GERÇEL KISIM AL ────────────────────────────────────────────
        self.gercele = blocks.complex_to_real()

        # ── 8. VERİ TOPLAMA SİNKLERİ ─────────────────────────────────────
        self.sink_baseband = blocks.vector_sink_c()   # FIR çıkışı (I+jQ baseband)
        self.sink_passband = blocks.vector_sink_f()   # Passband sinyal (gerçel)

        # ── BAĞLANTILAR ───────────────────────────────────────────────────
        self.connect(self.kaynak,       self.paket)
        self.connect(self.paket,        self.haritalayici)
        self.connect(self.haritalayici, self.tekrarla)
        self.connect(self.tekrarla,     self.fir)
        # Fan-out: FIR çıkışı → hem baseband sink hem de taşıyıcı çarpımı
        self.connect(self.fir,          self.sink_baseband)
        self.connect(self.fir,          (self.carpici, 0))
        self.connect(self.tasiyici,     (self.carpici, 1))
        self.connect(self.carpici,      self.gercele)
        self.connect(self.gercele,      self.sink_passband)

    def calistir(self):
        """Flowgraph'ı çalıştır; (baseband_c, passband_f) döndür."""
        self.start()
        self.wait()
        return (
            np.array(self.sink_baseband.data()),
            np.array(self.sink_passband.data()),
        )


# ─── GÖRSELLEŞTİRME ─────────────────────────────────────────────────────────
def gorsellestir(baseband, passband, fs=FS, fc=FC, sps=SPS):
    """Orijinal 6 grafik düzeni; GNU Radio blok çıkışlarıyla."""

    N   = len(passband)
    t   = np.arange(N) / fs
    win = slice(0, sps * 8)   # ilk 8 sembol

    # 8-tap FIR grup gecikmesi = (8-1)/2 = 3.5 örnek → 4 örnekten başla
    offset = 4
    semboller = baseband[offset::sps]

    fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle("QPSK Modulatör — GNU Radio Blok İmplementasyonu", fontsize=14)

    # ── 1. Constellation ──────────────────────────────────────────────────
    ax[0, 0].scatter(np.real(semboller), np.imag(semboller),
                     s=40, color='red', alpha=0.7, zorder=3)
    for lbl, (xi, yi) in zip(
        ['00', '01', '10', '11'],
        [(0.78, 0.78), (-0.78, 0.78), (0.78, -0.78), (-0.78, -0.78)]
    ):
        ax[0, 0].annotate(lbl, (xi, yi), fontsize=9, ha='center', color='navy')
    ax[0, 0].axhline(0, color='gray', lw=0.5)
    ax[0, 0].axvline(0, color='gray', lw=0.5)
    ax[0, 0].set_title("Constellation (GNU Radio)")
    ax[0, 0].set_xlabel("I")
    ax[0, 0].set_ylabel("Q")
    ax[0, 0].set_xlim(-1.5, 1.5)
    ax[0, 0].set_ylim(-1.5, 1.5)
    ax[0, 0].grid(True)

    # ── 2. I Kanalı ───────────────────────────────────────────────────────
    ax[0, 1].plot(t[win] * 1e6, np.real(baseband)[win], color='steelblue', lw=2)
    ax[0, 1].set_title("I Kanalı — GNU Radio fir_filter_ccf")
    ax[0, 1].set_xlabel("Zaman (µs)")
    ax[0, 1].grid(True)

    # ── 3. Q Kanalı ───────────────────────────────────────────────────────
    ax[0, 2].plot(t[win] * 1e6, np.imag(baseband)[win], color='darkorange', lw=2)
    ax[0, 2].set_title("Q Kanalı — GNU Radio fir_filter_ccf")
    ax[0, 2].set_xlabel("Zaman (µs)")
    ax[0, 2].grid(True)

    # ── 4. Passband Sinyal ────────────────────────────────────────────────
    ax[1, 0].plot(t[win] * 1e6, passband[win], color='seagreen')
    ax[1, 0].set_title(f"Passband Sinyal — fc = {fc // 1000} kHz")
    ax[1, 0].set_xlabel("Zaman (µs)")
    ax[1, 0].grid(True)

    # ── 5. Passband Frekans Spektrumu ─────────────────────────────────────
    fft_p = np.abs(np.fft.fftshift(np.fft.fft(passband)))
    freq  = np.fft.fftshift(np.fft.fftfreq(N, 1 / fs)) / 1e3
    ax[1, 1].plot(freq, 20 * np.log10(fft_p + 1e-10), color='purple', lw=1.5)
    ax[1, 1].set_title("Passband Frekans Spektrumu")
    ax[1, 1].set_xlabel("Frekans (kHz)")
    ax[1, 1].set_ylabel("Güç (dB)")
    ax[1, 1].set_xlim([0, 300])
    ax[1, 1].grid(True)

    # ── 6. Baseband Spektrumu (I+jQ) ─────────────────────────────────────
    fft_b  = np.abs(np.fft.fftshift(np.fft.fft(baseband)))
    freq_b = np.fft.fftshift(np.fft.fftfreq(N, 1 / fs)) / 1e3
    ax[1, 2].plot(freq_b, 20 * np.log10(fft_b + 1e-10), color='teal', lw=1.5)
    ax[1, 2].set_title("Baseband Spektrumu (I+jQ)")
    ax[1, 2].set_xlabel("Frekans (kHz)")
    ax[1, 2].set_ylabel("Güç (dB)")
    ax[1, 2].set_xlim([-200, 200])
    ax[1, 2].grid(True)

    plt.tight_layout()
    plt.show()


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("QPSK Modulatör — GNU Radio Blok İmplementasyonu")
    print("=" * 60)
    print(f"Parametreler: fs={FS/1e6:.0f} MHz | fc={FC/1e3:.0f} kHz | sps={SPS}")
    print(f"Bit sayısı  : {len(BITLER)}")
    print(f"Gönderilen  : {BITLER}")

    print("\nGNU Radio flowgraph başlatılıyor...")
    tb = QPSK_Modulatör_GR(BITLER)
    baseband, passband = tb.calistir()

    print(f"Tamamlandı  : {len(passband)} passband örneği üretildi")
    print(f"              {len(baseband)} baseband (I+jQ) örneği üretildi")

    gorsellestir(baseband, passband)
