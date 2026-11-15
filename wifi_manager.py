import binascii
import network
import time


def parse_bssid(value):
    """Принимает 'aa:bb:cc:dd:ee:ff', 'aabbccddeeff' или bytes(6)."""
    if not value:
        return None
    if isinstance(value, (bytes, bytearray)):
        if len(value) != 6:
            raise ValueError("BSSID must be 6 bytes")
        return bytes(value)
    text = value.replace(":", "").replace("-", "").replace(" ", "").lower()
    if len(text) != 12:
        raise ValueError("BSSID must look like aa:bb:cc:dd:ee:ff")
    return binascii.unhexlify(text)


class WiFiManager:
    def __init__(self, ssid, password, bssid=None, strict_bssid=False, timeout=30):
        self.ssid = ssid
        self.password = password
        self.bssid = bssid
        self.strict_bssid = strict_bssid
        self.timeout = timeout
        self.wlan = network.WLAN(network.STA_IF)

    def connect(self):
        self.wlan.active(True)
        if self.wlan.isconnected():
            print("WiFi уже подключен:", self.wlan.ifconfig()[0])
            return True

        target = parse_bssid(self.bssid)
        if target is not None:
            if self._connect(target):
                return True
            if self.strict_bssid:
                print("WiFi: указанная точка недоступна, STRICT — отказ от подключения")
                return False
            print("WiFi: указанная точка недоступна, пробую любую с этим SSID")

        return self._connect(None)

    def _connect(self, bssid):
        try:
            self.wlan.disconnect()
        except Exception:
            pass

        if bssid is not None:
            print("Подключение к WiFi: %s (BSSID %s)..." % (
                self.ssid, ":".join("%02x" % b for b in bssid)))
        else:
            print("Подключение к WiFi: %s..." % self.ssid)

        try:
            if bssid is not None:
                self.wlan.connect(self.ssid, self.password, bssid=bssid)
            else:
                self.wlan.connect(self.ssid, self.password)
        except TypeError:
            # Некоторые сборки MicroPython не принимают bssid — мягкий откат
            if bssid is None:
                raise
            print("WiFi: прошивка не поддерживает bssid, подключаюсь по SSID")
            self.wlan.connect(self.ssid, self.password)
        except OSError as e:
            print("WiFi: ошибка запуска подключения:", e)
            return False

        left = self.timeout
        while not self.wlan.isconnected() and left > 0:
            time.sleep(1)
            left -= 1
            print(".", end="")
        print()

        if self.wlan.isconnected():
            print("WiFi подключен! IP:", self.wlan.ifconfig()[0])
            return True
        print("WiFi: не удалось подключиться")
        return False

    def get_ip(self):
        return self.wlan.ifconfig()[0] if self.wlan.isconnected() else None

    def is_connected(self):
        return self.wlan.isconnected()

    def disconnect(self):
        self.wlan.disconnect()
        self.wlan.active(False)