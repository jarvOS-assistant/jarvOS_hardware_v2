import dbus
import time
import threading
import speech_recognition as sr
from advertisement import Advertisement
from service import Application, Service, Characteristic, Descriptor

GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"

class JarvOSAdvertisement(Advertisement):
    def __init__(self, index):
        Advertisement.__init__(self, index, "peripheral")
        self.add_local_name("JarvOS")
        self.include_tx_power = True

class JarvOSService(Service):
    THERMOMETER_SVC_UUID = "00000001-710e-4a5b-8d75-3e5b444bc3cf"

    def __init__(self, index):
        Service.__init__(self, index, self.THERMOMETER_SVC_UUID, True)
        self.add_characteristic(JarvOSCharacteristic(self))

class JarvOSCharacteristic(Characteristic):
    TEXT_CHARACTERISTIC_UUID = "00000002-710e-4a5b-8d75-3e5b444bc3cf"

    def __init__(self, service):
        self.notifying = False

        Characteristic.__init__(
                self, self.TEXT_CHARACTERISTIC_UUID,
                ["notify", "read"], service)
        self.add_descriptor(JarvOSDescriptor(self))

        self.speech_recognizer = sr.Recognizer()
        self.speech_thread = threading.Thread(target=self.listen_for_speech)
        self.speech_thread.daemon = True  # Allow the program to exit even if thread is running
        self.speech_thread.start()

        self.last_recognized_text = ""

    def listen_for_speech(self):
        with sr.Microphone(device_index=1) as source:
            while True:
                try:
                    audio = self.speech_recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    print("adjusting for ambient noise")
                    self.speech_recognizer.adjust_for_ambient_noise(audio, duration = 1)
                    print("listening")
                    text = self.speech_recognizer.recognize_whisper(audio_data=audio, model="small.en", language="english")
                    print(text)
                    self.last_recognized_text = text
                    self.set_text_callback()
                except sr.UnknownValueError:
                    pass  # Ignore if speech is not recognized
                except Exception as e:
                    print(f"Speech Recognition error: {e}")
                time.sleep(1)  # Adjust sleep duration as needed

    def get_text(self):
        print("get_text")
        value = []

        for i in self.last_recognized_text:
            value.append(dbus.Byte(i.encode()))

        return value

    def set_text_callback(self):
        print("set_text_callback")
        if self.notifying:
            value = self.get_text()
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

        return self.notifying

    def StartNotify(self):
        print("StartNotify")
        if self.notifying:
            return

        self.notifying = True

        value = self.get_text()
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        # self.add_timeout(5000, self.set_text_callback)

    def StopNotify(self):
        print("StopNotify")
        self.notifying = False

    def ReadValue(self, options):
        print("ReadValue")
        value = self.get_text()

        return value
    
class JarvOSDescriptor(Descriptor):
    TEXT_DESCRIPTOR_UUID = "2901"
    TEXT_DESCRIPTOR_VALUE = "Text"

    def __init__(self, characteristic):
        Descriptor.__init__(
                self, self.TEXT_DESCRIPTOR_UUID,
                ["read"],
                characteristic)

    def ReadValue(self, options):
        value = []
        desc = self.TEXT_DESCRIPTOR_VALUE

        for c in desc:
            value.append(dbus.Byte(c.encode()))

        return value
    
if __name__ == "__main__":
    app = Application()
    app.add_service(JarvOSService(0))
    app.register()

    adv = JarvOSAdvertisement(0)
    adv.register()

    try:
        app.run()
    except KeyboardInterrupt:
        app.quit()