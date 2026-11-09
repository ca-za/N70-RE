import CoreBluetooth
import Foundation
let names: [String: String] = ["2A29": "Manufacturer", "2A24": "Model", "2A25": "Serial number", "2A26": "Firmware",
  "2A27": "Hardware", "2A28": "Software", "2A23": "System-ID", "2A50": "PnP-ID", "2A2A": "Certification"]
final class R: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
  var c: CBCentralManager!; var p: CBPeripheral?; var left = 0
  override init() { super.init(); c = CBCentralManager(delegate: self, queue: nil) }
  func centralManagerDidUpdateState(_ c: CBCentralManager) {
    guard c.state == .poweredOn, let x = c.retrieveConnectedPeripherals(withServices: [CBUUID(string: "A001")]).first else { return }
    p = x; x.delegate = self; c.connect(x)
  }
  func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) { p.discoverServices([CBUUID(string: "180A")]) }
  func peripheral(_ p: CBPeripheral, didDiscoverServices e: Error?) {
    guard let s = p.services?.first else { exit(0) }; p.discoverCharacteristics(nil, for: s)
  }
  func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error e: Error?) {
    let cs = s.characteristics ?? []; left = cs.count; cs.forEach { p.readValue(for: $0) }
  }
  func peripheral(_ p: CBPeripheral, didUpdateValueFor ch: CBCharacteristic, error e: Error?) {
    let v = ch.value ?? Data()
    let text = String(data: v, encoding: .utf8).flatMap { $0.allSatisfy { !$0.isASCII || $0.isLetter || $0.isNumber || $0.isPunctuation || $0 == " " } ? $0 : nil }
    print(names[ch.uuid.uuidString] ?? ch.uuid.uuidString, ":", text ?? v.map { String(format: "%02x", $0) }.joined())
    left -= 1; if left == 0 { exit(0) }
  }
}
let r = R(); DispatchQueue.main.asyncAfter(deadline: .now() + 6) { exit(0) }; RunLoop.main.run()
