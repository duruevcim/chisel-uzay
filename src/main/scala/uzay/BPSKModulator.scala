package uzay

import chisel3._
import chisel3.util._

// BPSK Modülatör
// Bit 0 → taşıyıcı aynen çıkar (+1 * carrier)
// Bit 1 → taşıyıcı ters çıkar (-1 * carrier)
class BPSKModulator(
  lutBoyut:  Int = 256,   // sinüs tablosu kaç nokta
  bitGenislik: Int = 16   // sinyal kaç bit
) extends Module {

  val io = IO(new Bundle {
    val veri      = Input(Bool())               // gelen bit (0 veya 1)
    val gecerli   = Input(Bool())               // veri geçerli mi
    val fazAdim   = Input(UInt(8.W))            // taşıyıcı frekans kontrolü
    val cikis     = Output(SInt(bitGenislik.W)) // modüle edilmiş çıkış
    val hazir     = Output(Bool())              // modülatör hazır mı
  })

  // Sinüs lookup tablosu (donanımda ROM olarak üretilir)
  val sinusLUT = VecInit(Seq.tabulate(lutBoyut) { i =>
    val aci   = 2.0 * math.Pi * i / lutBoyut
    val deger = (math.sin(aci) * ((1 << (bitGenislik - 1)) - 1)).toInt
    deger.S(bitGenislik.W)
  })

  // NCO: Sayısal Kontrollü Osilatör (faz akümülatörü)
  val fazAkumulatoru = RegInit(0.U(8.W))
  fazAkumulatoru := fazAkumulatoru + io.fazAdim

  // Taşıyıcı sinyali LUT'tan oku
  val tasiyici = sinusLUT(fazAkumulatoru)

  // BPSK haritalama: veri=0 → +taşıyıcı, veri=1 → -taşıyıcı
  io.cikis := Mux(io.veri && io.gecerli, -tasiyici, tasiyici)
  io.hazir := true.B
}

object BPSKModulator extends App {
  emitVerilog(
    new BPSKModulator(lutBoyut = 256, bitGenislik = 16),
    Array("--target-dir", "generated")
  )
}
