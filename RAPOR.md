# BPSK Modülatör Tasarımı — Chisel HDL ile FPGA Uygulaması

**Proje:** Uzay Haberleşmesi için BPSK Modülatör  
**Dil:** Chisel HDL (Scala tabanlı)  
**Hedef Platform:** FPGA  
**Bağlam:** Uydu haberleşme sistemi — TÜBİTAK Chisel GPS Projesi

---

## 1. Giriş

Bu rapor, uydu haberleşme sistemlerinde kullanılmak üzere Chisel HDL ile tasarlanan BPSK (Binary Phase Shift Keying) modülatörünü ve yardımcı bir FIR (Sonlu Dürtü Yanıtı) filtresini kapsamaktadır. Tasarımlar FPGA hedefli olup Verilog RTL çıktısı üretilebilir durumdadır.

Rapor; konuya önceden aşina olmayan okuyucuların da sistemi kavrayabilmesi amacıyla temel kavramlardan başlayarak tasarım kararlarını ve uygulama detaylarını gerekçeleriyle birlikte ele almaktadır.

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

## 3. Temel Kavramlar

### 3.1 Modülasyon Nedir?

Sayısal verinin (0 ve 1 dizisi) bir taşıyıcı dalga üzerine bindirilmesi işlemine **modülasyon** denir. Uydu haberleşmesinde ham sayısal veri doğrudan iletilemez; atmosferde ve uzayda yayılabilmesi için belirli bir radyo frekansı taşıyıcısına ihtiyaç duyulur.

Basit bir benzetmeyle açıklamak gerekirse: konuşma sesini (veri) radyo dalgasına (taşıyıcı) yüklemek bir modülasyon işlemidir. Uydu sistemlerinde ise taşınan şey ses değil, ikili (binary) sayısal veridir.

### 3.2 BPSK (Binary Phase Shift Keying)

BPSK, en temel faz anahtarlamalı modülasyon yöntemidir. Veri bitleri, taşıyıcı dalganın faz açısı değiştirilerek iletilir. Dalganın frekansı veya genliği sabit kalır; yalnızca fazı iki olası konumdan birinde tutulur:

| Giriş Biti | Faz Kayması | Matematiksel Karşılık |
|------------|-------------|----------------------|
| 0 | 0° | +sin(2πf·t) |
| 1 | 180° | −sin(2πf·t) |

Bit=0 geldiğinde taşıyıcı olduğu gibi iletilir. Bit=1 geldiğinde dalga 180° döndürülür; matematiksel olarak bu, dalganın işaretinin tersine çevrilmesiyle eşdeğerdir.

BPSK'nın uydu sistemlerinde tercih edilme nedenleri:
- Gürültüye karşı yüksek dayanıklılık (en düşük Bit Hata Oranı — BER)
- Alıcı devresinin basit olması
- Uzay ortamındaki radyasyon ve termal gürültü koşullarında güvenilir çalışma

### 3.3 Alıcı Tarafında Demodülasyon

Alıcı (uydu veya yer istasyonu) gelen dalgayı kendi yerel referans dalgasıyla çarpar:

```
Gelen dalga × Referans dalga → Sonuç pozitifse → Bit=0
Gelen dalga × Referans dalga → Sonuç negatifse → Bit=1
```

Çıkış mantığı:
- Faz = 0° → +1 → Bit=0
- Faz = 180° → −1 → Bit=1

Bu sayede uydu, gelen dalgada "bu pozitif mi, negatif mi?" sorusunu sorarak orijinal 0 ve 1'leri geri kazanır. 256-noktalı LUT yalnızca gönderme tarafında sinyal kalitesi için gereklidir; alıcı taraf yalnızca faza bakar.

### 3.4 Tam Haberleşme Zinciri

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

Bu zincirde tasarlanan modülatör, yer istasyonu tarafında görev yapar: binary veriyi alır, BPSK modülasyonunu uygular ve DAC'a (Dijital-Analog Çevirici) hazır sinyal üretir.

---

## 4. Sistem Bileşenleri

Modülatör üç temel bileşenden oluşur: Sinüs Arama Tablosu (LUT), Sayısal Kontrollü Osilatör (NCO) ve BPSK Haritalayıcı.

### 4.1 Sinüs Arama Tablosu (LUT — Lookup Table)

FPGA üzerinde trigonometrik fonksiyonlar gerçek zamanlı olarak hesaplanamaz; `sin()` hesaplamak yüzlerce saat çevrimi gerektirir. Bu sorunu çözmek için bir tam sinüs dalgası önceden hesaplanarak ROM olarak depolanır. Her clock döngüsünde hesaplama yapmak yerine, doğrudan tabloya bakılır.

**256 Nokta Ne Demektir?**

Bir sinüs dalgası sürekli ve pürüzsüz bir eğridir; FPGA'da bunu üretmek için dalga örneklere bölünür. 256 nokta seçmek, sinüs dalgasının bir tam turunu (0°'den 360°'ye) **256 eşit parçaya bölmek** demektir.

Her parça için o açıdaki sinüs değeri hesaplanır ve bir tabloya yazılır. Çalışma zamanında bu tablo ROM gibi davranır: "64. indekste ne var?" diye sorulunca, 90° açısına karşılık gelen +32767 değeri anında döner. Trigonometri hesabı yoktur, yalnızca tablo okuma vardır.

**Neden tam olarak 256 nokta?**

Dijital devreler ikinin kuvvetlerini (2, 4, 8, 16, 32, ...) tercih eder; çünkü ikinin kuvvetleri bit dizileriyle doğal olarak örtüşür:

| Tablo Boyutu | Adres İçin Gereken Bit | Sonuç |
|-------------|----------------------|-------|
| 128 (2⁷) | 7 bit | Daha az bellek, ancak dalga kaba ve pürüzlü |
| **256 (2⁸)** | **8 bit** | **Standart seçim — optimal denge** |
| 512 (2⁹) | 9 bit | Daha pürüzsüz dalga, 2 kat fazla FPGA belleği |

256 seçiminin en kritik avantajı, **mod işlemi gerektirmemesidir.** Eğer tablo 250 elemanlı olsaydı, faz sayacının 250'yi aşmaması için her clock döngüsünde `% 250` işlemi yapılması gerekirdi; bu hem donanım kaynağı harcar hem de gecikme ekler. 256 ile 8-bit sayaç doğal olarak 0'dan 255'e sayar, 255'ten sonra otomatik olarak 0'a döner. Bu **ücretsiz taşma** (free overflow) özelliği, ekstra donanım maliyeti sıfır olan bir döngü oluşturur.

**Parametreler:**
- Tablo boyutu: 256 nokta (bir tam sinüs turu)
- Çözünürlük: 16 bit (−32767 ile +32767 arasında tam sayı değerleri)
- Adres genişliği: 8 bit

Örnek tablo değerleri:

| İndeks (i) | Açı | Sinüs Değeri |
|------------|-----|-------------|
| 0 | 0° | 0 |
| 64 | 90° | +32767 |
| 128 | 180° | 0 |
| 192 | 270° | −32767 |
| 255 | ≈360° | ≈0 |

### 4.2 NCO (Numerically Controlled Oscillator — Sayısal Kontrollü Osilatör)

NCO, taşıyıcı frekansını dijital olarak üretmekten sorumlu bileşendir.

**Akümülatör Nedir?**

Akümülatör, her clock döngüsünde **kendi üzerine sabit bir değer ekleyen** bir kayıt (register) devresidir. Bir araba kilometre sayacına benzetilebilir: her kilometre geçtiğinde sayaç bir artar ve hiçbir zaman sıfırlanmaz, taşarak döner. Burada fark şudur: her clock darbesi geçtiğinde sayaç `fazAdim` kadar artar; bu adım ne kadar büyükse, tablo o kadar hızlı dolaşılır.

**Neden 8 Bit?**

LUT'un 256 girişi vardır. Bu 256 girişi adreslemek için kaç bite ihtiyaç vardır sorusunun cevabı doğrudan 8 bittir; çünkü 2⁸ = 256. Adres sayacı 8 bit olduğu için 0'dan 255'e kadar sayar ve 255'ten sonra kendiliğinden 0'a döner — tablo boyutuyla mükemmel örtüşür, ek mantık gerekmez.

```
val fazAkumulatoru = RegInit(0.U(8.W))   // 8-bit: 0–255 arası, kendiliğinden döner
```

Her clock döngüsünde `fazAdim` değeri eklenir:

Her clock döngüsünde faz akümülatörüne sabit bir `fazAdim` değeri eklenir:

```
fazAkumulatoru(t+1) = fazAkumulatoru(t) + fazAdim
```

Akümülatör değeri her an LUT'un adresi olarak kullanılır; bu adresteki sinüs değeri taşıyıcı sinyali oluşturur.

**Frekans Kontrolü — fazAdim Nasıl Çalışır?**

256 noktalı tabloyu bir yarış pistine benzetmek faydalı olacaktır. Bir tam tur = bir tam sinüs dalgası.

- `fazAdim=1` → Her clock'ta 1 adım ileri → 256 adımda tam tur (en yavaş, en düşük frekans)
- `fazAdim=2` → Her clock'ta 2 adım ileri → 128 adımda tam tur (2× hızlı)
- `fazAdim=4` → Her clock'ta 4 adım ileri → 64 adımda tam tur (4× hızlı)

Üretilen taşıyıcı frekansı formülü:

```
f_taşıyıcı = (f_clock × fazAdim) / 256
```

50 MHz saat frekansı ile örnekler:

| fazAdim | Hesaplama | Üretilen Frekans |
|---------|-----------|-----------------|
| 1 | 50.000.000 × 1 / 256 | ≈ 195 kHz |
| 2 | 50.000.000 × 2 / 256 | ≈ 390 kHz |
| 32 | 50.000.000 × 32 / 256 | ≈ 6.25 MHz |

**Önemli Not — NCO Hangi Değeri Okur?**

Chisel'de register'lar bir pipeline gecikmesiyle çalışır. Kod şu şekilde yazılmıştır:

```scala
// Bu satır "bir sonraki clock'ta ne olacağını" tanımlar
fazAkumulatoru := fazAkumulatoru + io.fazAdim

// Bu satır "şu an ne okunuyor" dur (henüz güncellenmemiş değer)
val tasiyici = sinusLUT(fazAkumulatoru)
```

NCO her zaman **güncel (mevcut) konumu** okur. Her clock'ta `fazAdim` kadar ilerler ve güncellenen mevcut konumu okur:

| | Clock 1 | Clock 2 | Clock 3 | Clock 4 |
|---|---------|---------|---------|---------|
| Okunan LUT indeksi | LUT(0) | LUT(1) | LUT(2) | LUT(3) |

0'dan başlaması doğru ve normaldir — her dalga sıfırdan başlar.

### 4.3 BPSK Haritalayıcı

Taşıyıcı sinyal ile giriş bitini birleştiren son aşamadır. Mantığı son derece basittir:

```
Çıkış = veri ? −taşıyıcı : +taşıyıcı
```

Bit=0 geldiğinde taşıyıcı olduğu gibi çıkar. Bit=1 geldiğinde taşıyıcının işareti tersine çevrilir. Bu, Chisel'de `Mux` (çoklayıcı) primitifi ile tek satırda uygulanır ve FPGA'da yalnızca bir adet çoklayıcı kapısına dönüşür.

**Gönderen ve Alan Tarafının Karşılaştırması:**

| | Gönderen (Bu Tasarım) | Alan (Demodülatör) |
|--|----------------------|-------------------|
| 256 noktalı LUT | Pürüzsüz sinüs üretmek için kullanılır | 256 ile ilgilenmez |
| Amaç | Kaliteli sinyal üretimi | Sadece "bu dalga pozitif mi, negatif mi?" sorusunu sorar |

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

| Port | Yön | Bit Genişliği | Açıklama |
|------|-----|--------------|----------|
| `veri` | Giriş | 1 bit | İletilecek bit (0 veya 1) |
| `gecerli` | Giriş | 1 bit | Veri geçerlilik sinyali — 0 olduğunda modülatör taşıyıcıyı değiştirmeden iletir |
| `fazAdim` | Giriş | 8 bit | Taşıyıcı frekans kontrolü |
| `cikis` | Çıkış | 16 bit (işaretli) | Modüle edilmiş sinyal — DAC'a bağlanır |
| `hazir` | Çıkış | 1 bit | Modülatörün çalışır durumda olduğunu belirtir |

### 5.2 FIR Filtre — `FIRFilter.scala`

Sensörden veya ADC'den gelen ham verinin yüksek frekanslı gürültüden arındırılması için alçak geçiren bir FIR (Finite Impulse Response — Sonlu Dürtü Yanıtı) filtre tasarlanmıştır. FIR filtreler, geçmişteki birkaç örnekle ağırlıklı ortalama alarak gürültüyü bastırır.

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

Kullanılan `[1, 2, 2, 1]` katsayıları, merkez örneklere daha fazla ağırlık veren simetrik bir pencere filtresi oluşturur. Bu yapı donanımda kaydırmalı bir register zinciri (shift register) ve sabit çarpıcılar olarak sentezlenir.

---

## 6. Simülasyon ve GTKWave ile Görselleştirme

### 6.1 Gereksinimler

Testleri çalıştırmak ve sinyal dalgalarını görselleştirmek için GTKWave gereklidir.

**GTKWave Kurulumu (Windows — Chocolatey ile):**
```
choco install gtkwave -y
```
Not: Chocolatey kurulumu yönetici yetkisi gerektirir. PowerShell veya cmd'yi "Yönetici olarak çalıştır" ile açın.

### 6.2 Testleri Çalıştırma

```
cd C:\Users\durue\chisel-uzay
sbt test
```

İlk çalıştırmada bağımlılıklar indirilir, 2-3 dakika sürer. Başarılı çıktı:
```
[info] Tests: succeeded 2, failed 0
[info] All tests passed.
```

### 6.3 VCD Dosyasını GTKWave'de Açma

Test tamamlandığında `test_run_dir/` klasöründe bir `.vcd` dosyası oluşur. Yol uzun olduğu için önce kopyalanır:

```
copy "C:\Users\durue\chisel-uzay\test_run_dir\BPSKModulator_should_bit0_icin_pozitif_bit1_icin_negatif_cikis_uretmeli\BPSKModulator.vcd" C:\Users\durue\bpsk.vcd
```

GTKWave ile aç:
```
gtkwave C:\Users\durue\bpsk.vcd
```

### 6.4 Sinüs Dalgasını Görme

1. Sol panelde `BPSKModulator` → `io` → `cikis` üzerine **çift tıkla**
2. Alt panelde sinyale **sağ tıkla** → Data Format → **Signed Decimal**
3. Tekrar sağ tıkla → Data Format → Analog → **Interpolated**
4. Tüm dalgayı ekrana sığdır: **Ctrl + Alt + F**

**Test neden 512 clock tiki çalıştırıyor?**
`fazAdim=1` ile bir tam sinüs turu 256 clock tiki sürer. 512 tik = 2 tam tur demektir. Görselleştirmede dalgayı daha belirgin görmek için 256 yerine 512 tercih edildi; bu modülatörün temel davranışını değiştirmez.

---

## 7. Verilog Çıktısı Üretimi

Aşağıdaki komut ile FPGA sentezine hazır Verilog dosyası üretilir:

```bash
sbt "runMain uzay.BPSKModulator"
```

Çıktı `generated/` klasöründe oluşur. Bu Verilog dosyası herhangi bir FPGA sentez aracına (Vivado, Quartus vb.) doğrudan aktarılabilir.
