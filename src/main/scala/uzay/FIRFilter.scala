package uzay

import chisel3._
import chisel3.util._

// Sabit katsayılı FIR filtre - yıldız izleyici sensör verisi işleme için
class FIRFilter(bitWidth: Int, katsayilar: Seq[Int]) extends Module {
  val io = IO(new Bundle {
    val giris  = Input(SInt(bitWidth.W))
    val cikis  = Output(SInt(bitWidth.W))
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

object FIRFilter extends App {
  // Örnek: 4 katsayılı alçak geçiren filtre
  val katsayilar = Seq(1, 2, 2, 1)
  emitVerilog(new FIRFilter(16, katsayilar), Array("--target-dir", "generated"))
}
