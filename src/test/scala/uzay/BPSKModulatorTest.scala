package uzay

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

class BPSKModulatorTest extends AnyFlatSpec with ChiselScalatestTester {

  "BPSKModulator" should "bit=0 icin pozitif, bit=1 icin negatif cikis uretmeli" in {
    test(new BPSKModulator()) { dut =>
      dut.io.gecerli.poke(true.B)

      // Fazı 90°'ye getir (LUT index 64 = maksimum sinüs = 32767)
      dut.io.fazAdim.poke(64.U)
      dut.clock.step()

      // Fazı dondur: artık NCO ilerlemeyecek, ikisi de aynı sinüs noktasında
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

      // Zıt işaretli olmalı
      assert(cikis0 == -cikis1, s"BPSK hatasi: $cikis0 == -($cikis1) olmali")
      assert(cikis0 > 0, "Bit=0 cikisi pozitif olmali")
      assert(cikis1 < 0, "Bit=1 cikisi negatif olmali")

      println("BPSK testi basarili!")
    }
  }
}
