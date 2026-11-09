import CoreBluetooth
import Foundation
final class S: NSObject, CBCentralManagerDelegate {
  var c: CBCentralManager!
  var seen: [UUID: String] = [:]
  override init() { super.init(); c = CBCentralManager(delegate: self, queue: nil) }
  func centralManagerDidUpdateState(_ c: CBCentralManager) {
    guard c.state == .poweredOn else { return }
    c.scanForPeripherals(withServices: nil, options: [CBCentralManagerScanOptionAllowDuplicatesKey: true])
  }
  func centralManager(_ c: CBCentralManager, didDiscover p: CBPeripheral, advertisementData ad: [String: Any], rssi: NSNumber) {
    let name = (ad[CBAdvertisementDataLocalNameKey] as? String) ?? p.name ?? "-"
    let mfg = (ad[CBAdvertisementDataManufacturerDataKey] as? Data).map { $0.map { String(format: "%02x", $0) }.joined() } ?? ""
    let svc = (ad[CBAdvertisementDataServiceDataKey] as? [CBUUID: Data])?.map { "\($0.key)=\($0.value.map { String(format: "%02x", $0) }.joined())" }.joined(separator: ",") ?? ""
    let uuids = (ad[CBAdvertisementDataServiceUUIDsKey] as? [CBUUID])?.map { $0.uuidString }.joined(separator: ",") ?? ""
    let line = "\(name) rssi=\(rssi) mfg=\(mfg) svcdata=\(svc) uuids=\(uuids)"
    if seen[p.identifier] != line { seen[p.identifier] = line; print(p.identifier.uuidString.prefix(8), line) }
  }
}
let s = S(); DispatchQueue.main.asyncAfter(deadline: .now() + 12) { exit(0) }; RunLoop.main.run()
