import network
import time

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        
    def connect(self):
        """Подключение к WiFi сети"""
        if not self.wlan.isconnected():
            print(f"Подключение к WiFi: {self.ssid}...")
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            
            # Ожидание подключения
            timeout = 30
            while not self.wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
                print(".", end="")
            
            if self.wlan.isconnected():
                print("\nWiFi подключен!")
                print(f"IP адрес: {self.wlan.ifconfig()[0]}")
                return True
            else:
                print("\nОшибка подключения к WiFi")
                return False
        else:
            print("WiFi уже подключен")
            return True
    
    def get_ip(self):
        """Получить IP адрес устройства"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None
    
    def is_connected(self):
        """Проверить статус подключения"""
        return self.wlan.isconnected()
    
    def disconnect(self):
        """Отключиться от WiFi"""
        self.wlan.disconnect()
        self.wlan.active(False)