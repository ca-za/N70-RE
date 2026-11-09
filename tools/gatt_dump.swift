import Foundation
import IOBluetooth
import CoreBluetooth
for name in CommandLine.arguments.dropFirst() {
    guard let c: AnyClass = NSClassFromString(name) else { print("no class \(name)"); continue }
    print("== \(name) super=\(class_getSuperclass(c).map{NSStringFromClass($0)} ?? "-")")
    var n: UInt32 = 0
    if let ms = class_copyMethodList(c, &n) { for i in 0..<Int(n) { print("  -", NSStringFromSelector(method_getName(ms[i]))) } }
    if let iv = class_copyIvarList(c, &n) { for i in 0..<Int(n) { print("  ivar", String(cString: ivar_getName(iv[i])!)) } }
}
