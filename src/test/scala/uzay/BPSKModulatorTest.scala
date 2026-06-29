package uzay

import chisel3._
import chiseltest._
import chiseltest.simulator.WriteVcdAnnotation
import org.scalatest.flatspec.AnyFlatSpec

class BPSKModulatorTest extends AnyFlatSpec with ChiselScalatestTester {

  "BPSKModulator" should "bit=0 icin pozitif, bit=1 icin negatif cikis uretmeli" in {
    test(new BPSKModulator()).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      dut.io.gecerli.poke(true.B)

      // --- BÖLÜM 1: NCO'nun sinüs dalgasını dolaştığını gözlemle ---
      println("=== Sinüs dalgası (fazAdim=1, 512 tik = 2 tam tur) ===")
      dut.io.fazAdim.poke(1.U)
      dut.io.veri.poke(false.B)
      for (_ <- 0 until 512) {
        dut.clock.step()
      }

      // --- Donanımı sıfırla: akümülatörü 0'a döndür ---
      dut.reset.poke(true.B)
      dut.clock.step()
      dut.reset.poke(false.B)
      dut.io.gecerli.poke(true.B)

      // --- BÖLÜM 2: BPSK doğrulama ---
      println("=== BPSK testi ===")

      // Fazı 90°'ye getir (LUT index 64 = +32767)
      dut.io.fazAdim.poke(64.U)
      dut.clock.step()

      // Fazı dondur
      dut.io.fazAdim.poke(0.U)

      // Bit = 0 → taşıyıcı olduğu gibi (+)
      dut.io.veri.poke(false.B)
      dut.clock.step()
      val cikis0 = dut.io.cikis.peek().litValue
      println(s"Bit=0 cikis: $cikis0")

      // Bit = 1 → taşıyıcı ters (-)
      dut.io.veri.poke(true.B)
      dut.clock.step()
      val cikis1 = dut.io.cikis.peek().litValue
      println(s"Bit=1 cikis: $cikis1")

      assert(cikis0 == -cikis1, s"BPSK hatasi: $cikis0 == -($cikis1) olmali")
      assert(cikis0 > 0, "Bit=0 cikisi pozitif olmali")
      assert(cikis1 < 0, "Bit=1 cikisi negatif olmali")

      println("BPSK testi basarili!")
    }
  }
}
