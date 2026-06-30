QPSK Modülatör Tasarımı — Araştırma ve Teori Raporu

Proje: TÜBİTAK Uzay — GPS Haberleşme Sistemi  
Tasarım Dili: Python (yazılımsal doğrulama) → Chisel HDL (FPGA)  
Tarih: 30 Haziran 2026  



İÇİNDEKİLER

1. Giriş ve Proje Bağlamı
2. Modülasyon Nedir?
3. BPSK'dan QPSK'ya Geçiş
4. QPSK
5. I ve Q Kanalları
6. Neden Kompleks Sayı Kullanıyoruz?
7. Bant Genişliği ve Veri Hızı İlişkisi
8. FIR Filtre — Matematiksel Temel
9. DAC ve ADC
10. Tam Sistem Zinciri
11. GNU Radio — Kurulum ve Kullanım
12. Tasarım Akışı



1. GİRİŞ VE PROJE BAĞLAMI

Bu rapor, TÜBİTAK Uzay stajı kapsamında GPS haberleşme sistemi için tasarlanan QPSK (Quadrature Phase Shift Keying) modülatörünün teorik temellerini kapsamaktadır.

Tasarım iki aşamada gerçekleştirilecektir:

Aşama 1: Python ile yazılımsal modülatör tasarımı ve GNU Radio ile test
Aşama 2: Doğrulanan tasarımın Chisel HDL ile FPGA'ya aktarılması

Bu rapor Aşama 1'e ait teorik altyapıyı oluşturmaktadır.



2. MODÜLASYON NEDİR?

Sayısal verinin (0 ve 1 dizisi) bir taşıyıcı dalga üzerine bindirilmesi işlemine modülasyon denir. Ham sayısal veri doğrudan fiziksel ortamda iletilemez. GPS uydusu ile yer istasyonu arasında veri göndermek için verinin radyo dalgasına dönüştürülmesi gerekir.

Ham veri: 0 1 1 0 0 1 ...
              ↓ modülasyon
Radyo dalgası: ~~~∿∿∿~~~∿∿∿ (anten üzerinden gönderilir)


Taşıyıcı dalgada üç parametre değiştirilebilir:

| Parametre | Adı | Kullanım |
| Genlik    | ASK (Amplitude Shift Keying) | Güçsüz, gürültüye hassas |
| Frekans   | FSK (Frequency Shift Keying) | Basit ama band verimsiz |
| Faz       | PSK (Phase Shift Keying)     | GPS ve uydu sistemlerinde tercih edilen |

GPS sistemleri PSK kullanır çünkü faz anahtarlamalı modülasyon gürültüye karşı en dayanıklı yöntemdir.



3. BPSK'DAN QPSK'YA GEÇİŞ

3.1 BPSK (Binary Phase Shift Keying)

En basit faz modülasyon yöntemi. 1 bit → 1 sembol, 2 faz:

bit = 0 →  0° faz → +sin(2πft)  (dalga aynen geçer)
bit = 1 → 180° faz → -sin(2πft)  (dalga tersine çevrilir)


| Giriş Biti | Faz  | Matematiksel Karşılık |
|      0     | 0°   | +taşıyıcı |
|      1     | 180° | -taşıyıcı |


3.2 Neden QPSK'ya Geçiyoruz?

BPSK'da her sembolde sadece 1 bit taşınıyor. Bant genişliğini artırmadan veri hızını artırmak için her sembole daha fazla bit sıkıştırmak gerekir. QPSK bunu 4 faz kullanarak yapıyor: 2 bit → 1 sembol.



4. QPSK

4.1 Temel Fikir

QPSK, taşıyıcı dalganın fazını 4 farklı değerden birine ayarlar. Her faz değeri 2 biti temsil eder:

Bit çifti │  Faz  │  I   │  Q
──────────┼───────┼──────┼──────
   00     │  45°  │  +1  │  +1
   01     │ 135°  │  -1  │  +1
   11     │ 225°  │  -1  │  -1
   10     │ 315°  │  +1  │  -1



4.2 Matematiksel Gösterim

QPSK sinyali:

s(t) = I · cos(2πft) + Q · sin(2πft) şeklinde yazılır.

Burada:
- `f` = taşıyıcı frekansı
- `I ∈ {+1, -1}` = gelen bit çiftinin ilk biti
- `Q ∈ {+1, -1}` = gelen bit çiftinin ikinci biti



4.3 Somut Sayısal Örnek

`01` bit çiftini gönderiyoruz → I = -1, Q = +1:

s(t) = (-1)·cos(2πft) + (+1)·sin(2πft)

Farklı zaman anlarında sinyalin aldığı değerler (f = 1 Hz):

t = 0.00s:  (-1)(+1.0) + (+1)(0.0)  = -1.0
t = 0.25s:  (-1)(0.0)  + (+1)(+1.0) = +1.0
t = 0.50s:  (-1)(-1.0) + (+1)(0.0)  = +1.0
t = 0.75s:  (-1)(0.0)  + (+1)(-1.0) = -1.0

Antenden giden voltaj dizisi: `[-1.0, +1.0, +1.0, -1.0, ...]` — tek bir sayı dizisi.



4.4 Takımyıldızı (Constellation) Diyagramı

Dört faz noktası bir düzlemde gösterildiğinde:


        Q
        │
 (-1+j)●    ●(+1+j)
  [01]  │    [00]
────────┼──────── I
        │
  (-1-j)●    ●(+1-j)
  [11]  │    [10]
        │

Her nokta bir sembol = 2 bit. Alıcı, gelen sinyalin bu dört noktadan hangisine en yakın olduğunu bularak bitleri geri kazanır.



5. I VE Q KANALLARI

5.1 Neden İki Kanal?

Elimizde birbirine 90° dik iki taşıyıcı dalga var:
I kanalı:  cos(2πft)  → yatay bileşen
Q kanalı:  sin(2πft)  → dikey bileşen (90° kaydırılmış)


Bu iki dalga birbirine diktir (ortogonal). Dikliğin matematiksel anlamı:
∫cos(2πft) · sin(2πft) dt = 0   (bir periyot boyunca)
İntegral sıfır olduğundan bu iki kanal birbirini etkilemiyor. Alıcı ikisini ayrı ayrı okuyabiliyor.



5.2 Bit Akışı Nasıl Bölünüyor?

Gelen bitler: 0  1  1  0  0  1  1  1
                  ↓
         ┌────────────────┐
         │     DEMUX      │
         └────────────────┘
          ↓               ↓
     I kanalı         Q kanalı
    0   1   0   1     1   0   1   1
  (1., 3., 5., 7.)  (2., 4., 6., 8.)

Tek sıradaki bitler I'ya, çift sıradaki bitler Q'ya gidiyor. Her çift birlikte tek bir sembol oluşturuyor.


5.3 Bit Akışının İki Kanala Bölünmesi Zorunlu mu?

Evet, bu bir kolaylık değil, zorunluluk. İki bağımsız ve dik kanal var. Eğer ikisini de kullanmazsan kapasitenin yarısını boş bırakmış olursun.


5.4 Alıcı I ve Q'yu Nasıl Ayırıyor?

Alıcı gelen tek dalgayı alır ve iki kez çarpar:

I'yı bulmak için:
gelen sinyal × cos(2πft) → filtrele → I değeri çıkar

Q'yu bulmak için:
gelen sinyal × sin(2πft) → filtrele → Q değeri çıkar

Diklik sayesinde cos ile çarpınca Q kanalı sıfıra gider, sadece I kalır. Tersi de aynı şekilde çalışır.

Somut doğrulama: `01` gönderilmiş, alıcıda I bulunuyor:

[-1.0, +1.0, +1.0, -1.0] × [+1.0, 0.0, -1.0, 0.0]  (cos değerleri) = [-1.0, 0.0, -1.0, 0.0]
Ortalama = -0.5 → negatif → I = -1 → bit = 0  ✓


Q bulunuyor:

[-1.0, +1.0, +1.0, -1.0] × [0.0, +1.0, 0.0, -1.0]  (sin değerleri) = [0.0, +1.0, 0.0, +1.0]
Ortalama = +0.5 → pozitif → Q = +1 → bit = 1  ✓



6. NEDEN KOMPLEKS SAYI KULLANIYORUZ?

6.1 Kompleks Sayı = I + jQ

Bir kompleks sayı doğal olarak iki boyutlu bir noktayı temsil eder:

  z = I + jQ
      ↑    ↑
  x koordinatı  y koordinatı

Bu tam olarak QPSK'nın ihtiyacı olan şeydir. I ve Q bir aradalar yani ayrı ayrı dalgalar ile gönderilmeden tek seferde gönderilirler.


6.2 Açı Zaten İçinde

Kompleks sayının açısı (fazı) I ve Q'dan çıkıyor:

faz = arctan(Q / I)

00 → arctan(+1/+1) =  45°  
01 → arctan(+1/-1) = 135°  
11 → arctan(-1/-1) = 225°  
10 → arctan(-1/+1) = 315°  

I ve Q'yu ayrı ayrı taşımak zorunda kalmıyoruz kompleks sayıda ikisi birlikte, açı zaten gömülü.


6.3 Modülasyon Tek Çarpmaya İndirgeniyor

Euler formülü:
e^(jθ) = cos(θ) + j·sin(θ)


Kompleks sayı kullanıldığında yapılan modülasyon işlemi şöyle olur:
s(t) = gerçel_kısım( sembol × e^(j2πft) ) = gerçel_kısım( (I + jQ)(cos(2πft) + j·sin(2πft)) ) = I·cos(2πft) - Q·sin(2πft)
Tek bir karmaşık çarpım işlemi, I ve Q'yu otomatik olarak doğru kanallara dağıtıyor. Python'da bu numpy ile tek satır ile halledilir.



7. BANT GENİŞLİĞİ VE VERİ HIZI İLİŞKİSİ

7.1 Normal Durum

Normalde veri hızını artırmak için bant genişliği artırılır. Ancak bu her zaman mümkün değildir çünkü:
- Radyo frekans spektrumu kısıtlı ve devlet tarafından lisanslanıyor
- GPS sistemlerinde kullanılabilir bant genişliği sabit
- Uzayda frekanslar paylaşılıyor


Bunun yerine QPSK'da, bant genişliğini artırmak yerine her sembole daha fazla bilgi sıkıştırılır:

| Yöntem | Sembol Hızı | Bit/Sembol | Veri Hızı | Bant Genişliği |
| BPSK   | 1 Msps      | 1          | 1 Mbps    | B |
| QPSK   | 1 Msps      | 2          | 2 Mbps    | B |
| 8-PSK  | 1 Msps      | 3          | 3 Mbps    | B |


7.2 Sembol Hızı Neden Bant Genişliğini Belirliyor?

Sembol ne kadar hızlı değişirse sinyal o kadar hızlı salınım yapıyor ve o kadar geniş bant gerektiriyor. QPSK'da sembol hızı değişmiyor, sadece her sembolün içine daha fazla bit konuyor. Bant genişliği aynı kalıyor.



8. FIR FİLTRE — MATEMATİKSEL TEMEL

8.1 FIR Nedir?

FIR (Finite Impulse Response — Sonlu Dürtü Yanıtı), geçmişteki örneklerin ağırlıklı toplamını alarak filtreleme yapan bir yapıdır. Matematiksel olarak şu şekilde yazılır:

y[n] = h[0]·x[n] + h[1]·x[n-1] + h[2]·x[n-2] + ... + h[N-1]·x[n-(N-1)]


| Sembol   | Anlamı |
| `x[n]`   | Şu anki giriş örneği (modülatör çıkışı) |
| `x[n-k]` | k clock önceki giriş |
| `h[k]`   | Katsayılar — o örneğe ne kadar ağırlık verilecek |
| `y[n]`   | Filtrelenmiş çıkış |
| `N`      | Tap sayısı |


8.2 Geçmiş Değerler Nerede Tutuluyor?

Geçmiş örnekler shift register'da (kaydırmalı yazmaç) tutulur, sinüs tablosunda tutulmaz. Her clock darbesiyle yeni değer gelir, eski değerler bir adım kaydırılır:

Clock 1:  gecmisVeri[0] = +28000
Clock 2:  gecmisVeri[0] = +31000,  gecmisVeri[1] = +28000
Clock 3:  gecmisVeri[0] = +18000,  gecmisVeri[1] = +31000,  gecmisVeri[2] = +28000

FPGA'da bu register'lara (flip-flop) dönüşür, sinüs tablosu ise BRAM'e (Block RAM) dönüşür. İkisi farklı bellek türleridir.



8.3 Katsayılar Frekansı Nasıl Etkiliyor?

Katsayı şekli filtrenin frekans davranışını belirler:

[1, 1, 1, 1]        → düz moving average → çok kaba LP filtre
[1, 2, 2, 1]        → merkeze ağırlık verir → orta kalite LP filtre
[1, 2, 5, 8, 8, 5, 2, 1] → güçlü merkez ağırlığı → iyi LP filtre
Merkezdeki katsayılar büyük olunca son örneklere daha fazla önem veriliyor. Ani değişimler (yüksek frekans) bu ortalamada yumuşuyor.

**Geçiş bandı ve tap sayısı:**
4 tap  → geniş geçiş bandı → filtre keskin değil → gürültü sızabilir
8 tap  → dar geçiş bandı  → filtre keskin → gürültü iyi bastırılır
16 tap → çok dar geçiş   → neredeyse ideal → daha fazla FPGA kaynağı gerektirir
Daha fazla tap = geçmişe daha uzun bak = frekansları daha iyi ayırt et.



8.4 Taşma Sorunu ve Çözümü

Problem: 16-bit SInt maksimum ±32767 tutabildiği için taşma olduğunda verinin tamamı alınamadan bir kısmı kaybediliyor.

Katsayılar [1, 2, 2, 1] iken, max giriş +32767:
Toplam = (1+2+2+1) × 32767 = 6 × 32767 = 196.602
16-bit maksimum = 32.767  → Taşma olur.
Taşma sayıyı bozar — 32768 gelince -32768'e döner, sinyal anlamsız hale gelir.

Çözüm — Normalizasyon:

Katsayıları 2'nin kuvvetine eşit toplamlı seçersek:
[1, 2, 5, 8, 8, 5, 2, 1]  → toplam = 32 = 2⁵
Toplamı 32'ye bölmek yerine 5 bit sağa kaydır (aritmetik). Donanımda bölme yüzlerce LUT harcar.

Max toplam = 32 × 32767 = 1.048.544  → 21 bit'e sığar
21 bit >> 5  → 16 bit'e düşer        → 16-bit çıkışa sığar 



8.5 Sistem İçindeki Yeri

FIR filtreler GPS sisteminin farklı noktalarında kullanılır:
TX tarafı:  [QPSK Modülatör] → [RRC Filtre] → DAC
RX tarafı:  ADC → [RRC Filtre] → [LP Filtre] → [QPSK Demodülatör]



9. DAC VE ADC

9.1 Sistemin Fiziksel Dünya İle İlişkisi

Sistemde iki ayrı dünya vardır:
Dijital dünya:   sayılar, bitler, Chisel kodu, Python kodu
Fiziksel dünya:  voltaj, radyo dalgaları, anten, uzay
DAC ve ADC bu iki dünya arasındaki köprüdür.


9.2 DAC (Digital to Analog Converter)

Modülatör çıkışındaki sayıları fiziksel voltaja çevirir:
+32767  →  +1.0 V
     0  →   0.0 V
-32767  →  -1.0 V
Bu voltaj yükseltilir ve antenden radyo dalgası olarak yayılır. DAC olmadan sayılar fiziksel dünyaya çıkamaz.
16-bit DAC: 2¹⁶ = 65536 farklı voltaj seviyesi üretebilir. Çözünürlük yüksek → dalga pürüzsüz.


9.3 ADC (Analog to Digital Converter)

Alıcı anten gelen radyo dalgasını yakalar. (Bu sürekli bir voltaj sinyalidir). Demodülatör sayılarla çalışır bu yüzden ADC voltajı sayıya dönüştürür:
+0.87 V  →  +28507
-0.43 V  →  -14090
Chisel kodu tamamen dijital tarafta çalışır. DAC ve ADC ayrı fiziksel devrelerdir.



10. TAM SİSTEM ZİNCİRİ

GÖNDERİCİ (Yer İstasyonu):

[Binary Veri]
      ↓
[FEC Encoder]     hata düzeltme kodu ekler
      ↓
[QPSK Modülatör]  2 bit → kompleks sembol → taşıyıcıya bindir
      ↓
[RRC Filtre]      pulse shaping, bant sınırlama
      ↓
    [DAC]         sayı → voltaja çevrilir
      ↓
[Güç Yükselteci]
      ↓
[Anten] ~~~~~ radyo dalgası ~~~~~ [Anten]

ALICI (Uydu / Yer İstasyonu):

      ↓
   [ADC]             voltaj → sayıya geri çevrilir
      ↓
[RRC Filtre]         eşleşik filtre (matched filter)
      ↓
[LP Filtre]          gürültü bastırma
      ↓
[QPSK Demodülatör]   faz kararı → I, Q → bit
      ↓
[FEC Decoder]        hataları düzelt
      ↓
[Binary Veri]




11. GNU RADIO — KURULUM VE KULLANIM

11.1 GNU Radio Nedir?

GNU Radio, sinyal işleme bloklarını birbirine bağlayarak RF (Radyo Frekans) sistemleri tasarlamayı ve test etmeyi sağlayan açık kaynaklı bir araçtır.
İki kullanım modu vardır:
GNU Radio Companion (GRC) → Görsel sürükle-bırak arayüzü 
Python API → Kod yazarak aynı blokları kullan 

11.2 Bu Projede Ne İşe Yarayacak?

Bu projenin akışında sırasıyla şunları yapacağız:
Python'da QPSK modülatör yaz → GNU Radio ile test et → görselleştir → kodu doğrula ve onayla, çalıştığından emin ol → Chisel'e çevir

GNU Radio ile yapabileceklerimiz:
- QPSK constellation diyagramı görselleştirme
- Frekans spektrumu (FFT) analizi
- Gürültü ekleyip sistem davranışını test etme
- Python bloğu yazıp GNU Radio akışına dahil etme


11.3 Kurulum (Windows)

Adım 1: Miniconda kurulumu

powershell'i aç a

winget install -e --id Anaconda.Miniconda3
yaz

Adım 2: Conda PATH sorunu çözümü (gerekirse)

C:\Users\durue\miniconda3\Scripts\conda.exe init powershell
# PowerShell'i kapat ve yeniden aç


Adım 3: GNU Radio ortamı oluştur**

conda create -n gnuradio python=3.10
conda activate gnuradio
conda install -c conda-forge gnuradio


Adım 4: Kurulumu doğrula

conda activate gnuradio
python -c "import numpy; import matplotlib; print('numpy/matplotlib hazır')"
python -c "import gnuradio; print('GNU Radio hazır')"


11.4 GNU Radio Companion'ı Başlatma

conda activate gnuradio
gnuradio-companion


11.5 Neden GTKWave Değil de GNU Radio?

GTKWave dijital donanım simülasyonu için kullanılır (VCD dosyaları, clock sinyalleri). GNU Radio ise RF sinyal işleme için; frekans spektrumu, constellation diyagramı, gürültülü kanal simülasyonu gibi iletişim sistemine özgü görselleştirmeler sunar.

 GTKWave -> FPGA/Chisel simülasyonu, dijital sinyaller 
 GNU Radio -> RF sistemi testi, modülasyon/demodülasyon analizi 



12. TASARIM AKIŞI

AŞAMA 1 — Yazılımsal Tasarım (Şu An)
─────────────────────────────────────
1. Python'da QPSK modülatör yaz
   - Bit akışı oluştur
   - Sembol haritalama (2 bit → kompleks sayı)
   - NCO (taşıyıcı üretimi)
   - I ve Q kanallarını taşıyıcıya bindir
   - Toplam sinyal üret

2. GNU Radio ile test
   - Constellation diyagramı çiz
   - Frekans spektrumu kontrol et
   - Gürültülü kanal testi

3. Kodu doğrula ve düzgün çalıştığına, isterleri karşıladığına emin ol

AŞAMA 2 — Donanım Tasarımı (Sonra)
────────────────────────────────────
4. Python kodunu Chisel HDL'e çevir
   - Sinüs LUT (I ve Q için ayrı NCO)
   - QPSK sembol haritalayıcı
   - Çıkış birleştirici

5. ChiselTest ile simülasyon
6. VCD Dosyası'na dönüştürme
7. GTKWave ile görselleştirme (dijital sinyalleri görme)
8. Chisel → FIRRTL
9. SystemVerilog üretimi
10. Vivado kullanımı
11. FPGA sentezi
