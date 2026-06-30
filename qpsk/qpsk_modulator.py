import numpy as np
import matplotlib.pyplot as plt

# ─── PARAMETRELER ───────────────────────────────
fs  = 1e6    # ornekleme frekansi: 1 MHz
fc  = 100e3  # tasiyici frekansi:  100 kHz
sps = 10     # sembol basina ornek sayisi

# ─── 1. BIT AKISI ───────────────────────────────
np.random.seed(42)
bitler = np.random.randint(0, 2, size=64)
print("Gonderilen bitler:", bitler)

# ─── 2. QPSK SEMBOL HARITALAMA ──────────────────
def qpsk_haritalama(bitler):
    semboller = []
    for i in range(0, len(bitler), 2):
        b1, b2 = bitler[i], bitler[i+1]
        if   b1==0 and b2==0: semboller.append(+1+1j)
        elif b1==0 and b2==1: semboller.append(-1+1j)
        elif b1==1 and b2==1: semboller.append(-1-1j)
        else:                  semboller.append(+1-1j)
    return np.array(semboller) / np.sqrt(2)

semboller = qpsk_haritalama(bitler)

# ─── 3. UPSAMPLE ────────────────────────────────
semboller_up = np.repeat(semboller, sps)

# ─── 4. FIR FILTRE (Pulse Shaping) ──────────────
# Katsayilar toplami 32 = 2^5 → normalize icin 32'ye bol
katsayilar = np.array([1, 2, 5, 8, 8, 5, 2, 1], dtype=float)
katsayilar = katsayilar / np.sum(katsayilar)   # / 32

# Kompleks sinyale filtre uygula (I ve Q ayri ayri filtrelenir)
semboller_filtered = np.convolve(semboller_up, katsayilar, mode='same')

I_ham      = np.real(semboller_up)        # filtresiz
Q_ham      = np.imag(semboller_up)
I_filtered = np.real(semboller_filtered)  # filtreli
Q_filtered = np.imag(semboller_filtered)

print("FIR filtre uygulandi — katsayilar:", katsayilar * 32)

# ─── 5. NCO — TASIYICI ──────────────────────────
N = len(semboller_up)
t = np.arange(N) / fs

tasiyici_cos = np.cos(2 * np.pi * fc * t)
tasiyici_sin = np.sin(2 * np.pi * fc * t)

# ─── 6. MODULASYON ──────────────────────────────
sinyal_ham      = I_ham      * tasiyici_cos + Q_ham      * tasiyici_sin
sinyal_filtered = I_filtered * tasiyici_cos + Q_filtered * tasiyici_sin

# ─── 7. GORSELLESTIRME ──────────────────────────
goster = slice(0, sps * 8)   # ilk 8 sembol

fig, ax = plt.subplots(2, 3, figsize=(15, 8))
fig.suptitle('QPSK Modulatör — FIR Filtreli vs Filtresiz')

# Constellation
ax[0,0].scatter(np.real(semboller), np.imag(semboller), s=60, color='red')
ax[0,0].axhline(0, color='gray', lw=0.5)
ax[0,0].axvline(0, color='gray', lw=0.5)
ax[0,0].set_title('Constellation')
ax[0,0].set_xlabel('I')
ax[0,0].set_ylabel('Q')
ax[0,0].grid(True)

# I kanali karsilastirma
ax[0,1].plot(t[goster]*1e6, I_ham[goster],      label='Filtresiz', alpha=0.6)
ax[0,1].plot(t[goster]*1e6, I_filtered[goster], label='Filtreli',  linewidth=2)
ax[0,1].set_title('I Kanali')
ax[0,1].set_xlabel('Zaman (us)')
ax[0,1].legend()
ax[0,1].grid(True)

# Q kanali karsilastirma
ax[0,2].plot(t[goster]*1e6, Q_ham[goster],      label='Filtresiz', alpha=0.6)
ax[0,2].plot(t[goster]*1e6, Q_filtered[goster], label='Filtreli',  linewidth=2)
ax[0,2].set_title('Q Kanali')
ax[0,2].set_xlabel('Zaman (us)')
ax[0,2].legend()
ax[0,2].grid(True)

# Filtresiz modulasyon
ax[1,0].plot(t[goster]*1e6, sinyal_ham[goster])
ax[1,0].set_title('Modulasyon — Filtresiz')
ax[1,0].set_xlabel('Zaman (us)')
ax[1,0].grid(True)

# Filtreli modulasyon
ax[1,1].plot(t[goster]*1e6, sinyal_filtered[goster], color='green')
ax[1,1].set_title('Modulasyon — Filtreli')
ax[1,1].set_xlabel('Zaman (us)')
ax[1,1].grid(True)

# Spektrum karsilastirma
fft_ham      = np.abs(np.fft.fftshift(np.fft.fft(sinyal_ham)))
fft_filtered = np.abs(np.fft.fftshift(np.fft.fft(sinyal_filtered)))
freqs = np.fft.fftshift(np.fft.fftfreq(N, 1/fs)) / 1e3  # kHz

ax[1,2].plot(freqs, 20*np.log10(fft_ham + 1e-10),      label='Filtresiz', alpha=0.6)
ax[1,2].plot(freqs, 20*np.log10(fft_filtered + 1e-10), label='Filtreli',  linewidth=2)
ax[1,2].set_title('Frekans Spektrumu')
ax[1,2].set_xlabel('Frekans (kHz)')
ax[1,2].set_ylabel('Guc (dB)')
ax[1,2].set_xlim([0, 300])
ax[1,2].legend()
ax[1,2].grid(True)

plt.tight_layout()
plt.show()
