import CoreBluetooth
import Foundation
// LE Audio services: ASCS 184E, BASS 184F, PACS 1850, CAS 1853, TMAS 1855, HAS 1854, VCS 1844, MICS 184D
let le = ["184E","184F","1850","1853","1855","1854","1844","184D","A001"].map { CBUUID(string: $0) }
final class R: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
  var c: CBCentralManager!; var p: CBPeripheral?
  override init() { super.init(); c = CBCentralManager(delegate: self, queue: nil) }
  func centralManagerDidUpdateState(_ c: CBCentralManager) {
    guard c.state == .poweredOn else { return }
    for s in le { for x in c.retrieveConnectedPeripherals(withServices: [s]) { print("connected w/ \(s.uuidString):", x.name ?? "?") } }
    guard let x = c.retrieveConnectedPeripherals(withServices: [CBUUID(string: "A001")]).first else { print("no QCY BLE link"); exit(0) }
    p = x; x.delegate = self; c.connect(x)
  }
  func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) { p.discoverServices(nil) }
  func peripheral(_ p: CBPeripheral, didDiscoverServices e: Error?) {
    print("all GATT services of \(p.name ?? "?"):", p.services?.map { $0.uuid.uuidString } ?? []); exit(0)
  }
}
let r = R(); DispatchQueue.main.asyncAfter(deadline: .now() + 6) { exit(0) }; RunLoop.main.run()
