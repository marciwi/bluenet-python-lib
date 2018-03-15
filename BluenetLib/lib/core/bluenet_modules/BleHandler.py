from bluepy.btle import Scanner, Peripheral, ADDR_TYPE_RANDOM, BTLEException

from BluenetLib import BluenetBleException
from BluenetLib.lib.core.bluetooth_delegates.SingleNotificationDelegate import PeripheralDelegate
from BluenetLib.lib.core.bluetooth_delegates.ScanDelegate import ScanDelegate
from BluenetLib.lib.core.modules.Validator import Validator
from BluenetLib.lib.util.EncryptionHandler import EncryptionHandler

CCCD_UUID = 0x2902

class BleHandler:
    scanner = None
    settings = None

    connectedPeripherals = {}
    connectedPeripheral = None
    
    notificationLoopActive = False
    notificationResult = None
    
    
    def __init__(self, settings):
        self.scanner = Scanner().withDelegate(ScanDelegate())
        self.validator = Validator()
        self.settings = settings
    
    
    def connect(self, address):
        if address not in self.connectedPeripherals:
            self.connectedPeripherals[address] = Peripheral()
            print("Connecting")
            self.connectedPeripheral = address
            self.connectedPeripherals[address].connect(address, ADDR_TYPE_RANDOM)
            self.connectedPeripherals[address].getServices()
            print("Connected")
            
    
    def disconnect(self):
        print("Disconnecting... Cleaning up")
        if self.connectedPeripheral:
            self.connectedPeripherals[self.connectedPeripheral].disconnect()
            del self.connectedPeripherals[self.connectedPeripheral]
            self.connectedPeripheral = None
            print("Cleaned up")
    
    
    def startScanning(self):
        self.scanner.start()
        self.scanner.process(3)
        self.scanner.stop()

    
    def stopScanning(self):
        self.scanner.stop()
    
    
    def enableNotifications(self):
        print("ENABLE NOTIFICATIONS IS NOT IMPLEMENTED YET")
    
    def disableNotifications(self):
        print("DISABLE NOTIFICATIONS IS NOT IMPLEMENTED YET")

    def writeToCharacteristic(self, serviceUUID, characteristicUUID, content):
        targetCharacteristic = self._getCharacteristic(serviceUUID, characteristicUUID)
        encryptedContent = EncryptionHandler.encrypt(content, self.settings)
        targetCharacteristic.write(encryptedContent, withResponse=True)


    def readCharacteristic(self, serviceUUID, characteristicUUID):
        data = self.readCharacteristicWithoutEncryption(serviceUUID, characteristicUUID)
        


    def readCharacteristicWithoutEncryption(self, serviceUUID, characteristicUUID):
        targetCharacteristic = self._getCharacteristic(serviceUUID, characteristicUUID)
        data = targetCharacteristic.read()
        return data

    
    def _getCharacteristic(self, serviceUUID, characteristicUUID):
        if self.connectedPeripheral:
            peripheral = self.connectedPeripherals[self.connectedPeripheral]
        
            try:
                service = peripheral.getServiceByUUID(serviceUUID)
            except BTLEException:
                raise BluenetBleException("Can not find service", serviceUUID)
        
            characteristics = service.getCharacteristics(characteristicUUID)
            if len(characteristics) == 0:
                raise BluenetBleException("Can not find characteristic", characteristicUUID)

            return characteristics[0]
        
        else:
            raise BluenetBleException("Can't get characteristic: Not connected.")
        
        
    def setupSingleNotification(self, serviceUUID, characteristicUUID, writeCommand):
        characteristic = self._getCharacteristic(serviceUUID, characteristicUUID)
        peripheral = self.connectedPeripherals[self.connectedPeripheral]
        
        peripheral.withDelegate(PeripheralDelegate(lambda x: self._killNotificationLoop(x), self.settings))
        
        characteristicCCCDList = characteristic.getDescriptors(forUUID=CCCD_UUID)
        if len(characteristicCCCDList) == 0:
            raise BluenetBleException("Can not find CCCD handle to use notifications for characteristic: ", characteristicUUID)
        
        characteristicCCCD = characteristicCCCDList[0]
        
        # enable notifications
        characteristicCCCD.write(b"\x01\x00", True)
        
        # execute something that will trigger the notifications
        writeCommand()
        
        self.notificationLoopActive = True

        loopCount = 0
        while self.notificationLoopActive and loopCount < 10:
            peripheral.waitForNotifications(0.5)
            loopCount += 1


        if self.notificationResult is None:
            raise BluenetBleException("No notification data received.")
        
        result = self.notificationResult
        self.notificationResult = None
        
        return result
        
        
    def _killNotificationLoop(self, result):
        self.notificationLoopActive = False
        self.notificationResult = result