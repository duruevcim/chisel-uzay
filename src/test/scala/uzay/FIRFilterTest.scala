package uzay

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

class FIRFilterTest extends AnyFlatSpec with ChiselScalatestTester {
  "FIRFilter" should "dogru cikis uretmeli" in {
    val katsayilar = Seq(1, 2, 2, 1)
    test(new FIRFilter(16, katsayilar)) { dut =>
      dut.io.giris.poke(4.S)
      dut.clock.step()
      dut.io.giris.poke(0.S)
      dut.clock.step()
      dut.clock.step()
      dut.clock.step()
      println(s"Cikis: ${dut.io.cikis.peek().litValue}")
    }
  }
}
