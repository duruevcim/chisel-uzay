# BPSK Modülatör Tasarımı — Chisel HDL ile FPGA Uygulaması

**Proje:** Uzay Haberleşmesi için BPSK Modülatör  
**Dil:** Chisel HDL (Scala tabanlı)  
**Hedef Platform:** FPGA  
**Bağlam:** Uydu haberleşme sistemi — TÜBİTAK Chisel GPS Projesi

---

## 1. Giriş

Bu rapor, uydu haberleşme sistemlerinde kullanılmak üzere Chisel HDL ile tasarlanan BPSK (Binary Phase Shift Keying) modülatörünü ve yardımcı bir FIR (Sonlu Dürtü Yanıtı) filtresini kapsamaktadır. Tasarımlar FPGA hedefli olup Verilog RTL çıktısı üretilebilir durumdadır.

---

## 2. Kullanılan Teknolojiler

| Araç | Sürüm | Amaç |
|------|-------|-------|
| Chisel HDL | 6.6.0 | Donanım tanımlama dili |
| Scala | 2.13.15 | Chisel'in üzerinde çalıştığı dil |
| Java JDK | 21 (Temurin) | Çalışma ortamı |
| sbt | 1.10.7 | Derleme aracı |
| ChiselTest | 6.0.0 | Donanım simülasyon ve test çerçevesi |

---

## 3. Modülasyon Teorisi

### 3.1 Modülasyon Nedir?

Sayısal verinin (0 ve 1 dizisi) bir taşıyıcı dalga üzerine bindirilmesi işlemidir. Uydu haberleşmesinde ham sayısal veri doğrudan iletilemez; bir radyo frekansı taşıyıcısına ihtiyaç duyulur.

### 3.2 BPSK (Binary Phase Shift Keying)

BPSK, en basit faz anahtarlamalı modülasyon yöntemidir. Veri bitleri, taşıyıcı dalganın fazı değiştirilerek iletilir:

| Giriş Biti | Faz Kayması | Çıkış |
|------------|-------------|-------|
| 0 | 0° | +sin(2πf·t) |
| 1 | 180° | −sin(2πf·t) |

BPSK'nın uydu sistemlerinde tercih edilme nedenleri:
- Gürültüye karşı yüksek dayanıklılık
- Düşük bit hata oranı (BER)
- Basit alıcı devresi gereksinimleri
- Uzay ortamındaki radyasyon koşullarında güvenilir çalışma

### 3.3 Tam Haberleşme Zinciri

```
YER İSTASYONU
[Binary Veri] → [BPSK Modülatör] → [DAC] → [Güç Yükselteci] → [Anten]
                                                                     |
                                                                  Radyo dalgası
                                                                  (uzayda yayılım)
                                                                     |
                                                                  [Anten]
UYDU                                                                 |
[Binary Veri] ← [BPSK Demodülatör] ← [ADC] ←────────────────────────
```

---

## 4. Sistem Bileşenleri

### 4.1 Sinüs Arama Tablosu (LUT — Lookup Table)

FPGA'da trigonometrik hesaplama doğrudan gerçekleştirilemez. Bu nedenle bir tam sinüs dalgası önceden hesaplanarak ROM belleğe yazılır.

**Parametreler:**
- Tablo boyutu: 256 nokta (bir tam tur)
- Çözünürlük: 16 bit (−32767 ile +32767 arası)
- Adres genişliği: 8 bit

256 nokta seçiminin gerekçesi:
- **2⁸ = 256** → 8-bit faz akümülatörüyle doğal örtüşme
- Mod işlemi gerektirmez, taşma otomatik gerçekleşir
- Uydu haberleşmesi için yeterli sinyal kalitesi

Örnekler:

| İndeks (i) | Açı | Sinüs Değeri |
|------------|-----|-------------|
| 0 | 0° | 0 |
| 64 | 90° | +32767 |
| 128 | 180° | 0 |
| 192 | 270° | −32767 |
| 255 | ~360° | ~0 |

### 4.2 NCO (Numerically Controlled Oscillator — Sayısal Kontrollü Osilatör)

NCO, taşıyıcı frekansını üretmekten sorumlu bileşendir. 8-bit bir faz akümülatöründen oluşur:

```
fazAkumulatoru(t+1) = fazAkumulatoru(t) + fazAdim
```

Üretilen taşıyıcı frekansı:

```
f_taşıyıcı = (f_clock × fazAdim) / 256
```

| fazAdim | 50 MHz clock ile taşıyıcı frekansı |
|---------|-------------------------------------|
| 1 | ~195 kHz |
| 2 | ~390 kHz |
| 32 | ~6.25 MHz |

`fazAdim` artıkça LUT'ta daha fazla nokta atlanır, dalga daha hızlı tamamlanır ve frekans yükselir.

### 4.3 BPSK Haritalayıcı

Taşıyıcı sinyal ile giriş bitini birleştiren son aşamadır:

```
Çıkış = veri ? −taşıyıcı : +taşıyıcı
```

Chisel'de `Mux` (çoklayıcı) primitifi ile uygulanır.

---

## 5. Chisel Implementasyonu

### 5.1 BPSK Modülatör — `BPSKModulator.scala`

```scala
class BPSKModulator(lutBoyut: Int = 256, bitGenislik: Int = 16) extends Module {
  val io = IO(new Bundle {
    val veri      = Input(Bool())
    val gecerli   = Input(Bool())
    val fazAdim   = Input(UInt(8.W))
    val cikis     = Output(SInt(bitGenislik.W))
    val hazir     = Output(Bool())
  })

  // Sinüs LUT (donanımda ROM olarak üretilir)
  val sinusLUT = VecInit(Seq.tabulate(lutBoyut) { i =>
    val aci   = 2.0 * math.Pi * i / lutBoyut
    val deger = (math.sin(aci) * ((1 << (bitGenislik - 1)) - 1)).toInt
    deger.S(bitGenislik.W)
  })

  // NCO: faz akümülatörü
  val fazAkumulatoru = RegInit(0.U(8.W))
  fazAkumulatoru := fazAkumulatoru + io.fazAdim

  // Taşıyıcı
  val tasiyici = sinusLUT(fazAkumulatoru)

  // BPSK haritalama
  io.cikis := Mux(io.veri && io.gecerli, -tasiyici, tasiyici)
  io.hazir := true.B
}
```

**Port Açıklamaları:**

| Port | Yön | Açıklama |
|------|-----|----------|
| `veri` | Giriş | İletilecek bit (0 veya 1) |
| `gecerli` | Giriş | Veri geçerlilik sinyali |
| `fazAdim` | Giriş | Taşıyıcı frekans kontrolü |
| `cikis` | Çıkış | Modüle edilmiş 16-bit sinyal |
| `hazir` | Çıkış | Modülatör hazır göstergesi |

### 5.2 FIR Filtre — `FIRFilter.scala`

Sensörden gelen ham verinin gürültüden arındırılması için alçak geçiren FIR filtre tasarlanmıştır:

```scala
class FIRFilter(bitWidth: Int, katsayilar: Seq[Int]) extends Module {
  val io = IO(new Bundle {
    val giris = Input(SInt(bitWidth.W))
    val cikis = Output(SInt(bitWidth.W))
  })

  val gecmisVeri = RegInit(VecInit(Seq.fill(katsayilar.length)(0.S(bitWidth.W))))
  gecmisVeri(0) := io.giris
  for (i <- 1 until katsayilar.length) {
    gecmisVeri(i) := gecmisVeri(i - 1)
  }

  val carpimlar = katsayilar.zipWithIndex.map { case (k, i) =>
    gecmisVeri(i) * k.S
  }

  io.cikis := carpimlar.reduce(_ + _)
}
```

Kullanılan katsayılar `[1, 2, 2, 1]` alçak geçiren bir pencere filtresi oluşturur.

---

## 6. Test Sonuçları

Her iki modül ChiselTest çerçevesiyle simüle edilmiştir.

### 6.1 FIR Filtre Testi
- Giriş: 4 değeri uygulandı, beklenilen toplama yanıtı gözlemlendi.
- Sonuç: **BAŞARILI**

### 6.2 BPSK Modülatör Testi
Test prosedürü:
1. NCO 90°'ye (`fazAdim=64`) konumlandırıldı
2. NCO donduruldu (`fazAdim=0`)
3. Bit=0 için çıkış ölçüldü: **+32767**
4. Bit=1 için çıkış ölçüldü: **−32767**
5. `+32767 == −(−32767)` doğrulandı

Sonuç: **BAŞARILI** ✓

---

## 7. Verilog Çıktısı Üretimi

Aşağıdaki komut ile FPGA sentezine hazır Verilog dosyası üretilir:

```bash
sbt "runMain uzay.BPSKModulator"
```

Çıktı `generated/` klasöründe oluşur.

---

## 8. Sonuç

Bu çalışmada Chisel HDL kullanılarak uydu haberleşmesi için temel bir BPSK modülatör ve FIR filtre donanım bloğu tasarlanmıştır. Tasarımların tümü simülasyon testlerinden geçirilmiş ve Verilog RTL üretimine hazır hale getirilmiştir.
