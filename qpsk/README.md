#QPSK Modülatör — Python Implementasyonu

GPS haberleşme sistemi için QPSK modülatörünün Python ile yazılımsal tasarımı.

#Dosyalar

| Dosya | Açıklama |
|-------|---------|
| `qpsk_modulator.py` | Ana modülatör — sembol haritalama, FIR filtre, NCO, modülasyon, görselleştirme içerir. |
| `test_semboller.py` | Bit akışı ve sembol çıktısını terminalde kontrol etmek için küçük test için kullanılmıştır. |

#Çalıştırma

```bash
conda activate gnuradio
cd qpsk
python qpsk_modulator.py
```

#Modülatör Adımları

```
1. Bit akışı          → rastgele 0/1 dizisi (gerçekte FEC'ten gelecek)
2. Sembol haritalama  → 2 bit → kompleks sayı (I + jQ)
3. Upsample           → her sembol sps=10 örneğe uzatılır
4. FIR filtre         → katsayılar [1,2,5,8,8,5,2,1], geçişleri yumuşatır
5. NCO                → cos ve sin taşıyıcı üretimi
6. Modülasyon         → s(t) = I·cos(2πft) + Q·sin(2πft)
```

#Parametreler

| Parametre | Değer   | Açıklama            |
| `fs`      | 1 MHz   | Örnekleme frekansı  |
| `fc`      | 100 kHz | Taşıyıcı frekansı   |
| `sps`     | 10      | Sembol başına örnek |
| FIR katsayılar      | [1,2,5,8,8,5,2,1]   | Toplam=32=2⁵, normalize için >>5 |

#Çıktı Grafikleri

- Constellation — 4 QPSK sembol noktası
- I / Q Kanalı — filtresiz (kare) vs filtreli (yumuşak) karşılaştırması
- Modüle Edilmiş Sinyal — filtresiz vs filtreli
- Frekans Spektrumu — FIR filtrenin bant daralmasına etkisi

#Sonraki Adımlar

- [ ] QPSK demodülatör ekle (round-trip testi)
- [ ] RRC filtre entegrasyonu (Ece'den gelecek)
- [ ] Gürültü simülasyonu (AWGN kanalı)
- [ ] Doğrulama sonrası Chisel HDL'e çevir
