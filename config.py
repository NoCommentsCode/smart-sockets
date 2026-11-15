# Конфигурация устройства (заводские значения).
# Пользовательские изменения хранятся в device_config.json и имеют приоритет.
WIFI_SSID = "111"
WIFI_PASSWORD = "guga777gugi1"

# --- WiFi: привязка к конкретной точке доступа (опционально) ---
# ESP32/C3 работают только на 2.4 ГГц. При одинаковом SSID для 2.4/5 ГГц
# можно зафиксировать BSSID (MAC радио 2.4 ГГц), чтобы устройство не
# переключалось между точками mesh / не попадало под band steering.
# None = подключаться к любой точке с этим SSID (поведение по умолчанию).
WIFI_BSSID = None            # например: "a4:2b:b0:11:22:33"
WIFI_BSSID_STRICT = False    # True = не подключаться к другим точкам, если указанная недоступна
WIFI_CONNECT_TIMEOUT = 30    # секунд на попытку подключения

# Конфигурация реле (GPIO пины ESP32)
RELAY_PINS = [
    {"id": 1, "pin": 0, "name": "Чайник", "default_state": False},
    {"id": 2, "pin": 1, "name": "Торшер", "default_state": True},
    {"id": 3, "pin": 2, "name": "Фонарь", "default_state": True},
]

# API ключ для авторизации (измените на свой секретный ключ)
API_KEY = "api__HiGeHNTfboIizRfeJa0BQYcAhfbF8bis"

# Настройки сервера
HTTP_PORT = 80
DEVICE_NAME = "Smart Sockets ESP32 Wroom"
DEVICE_VERSION = "1.1.0"

# Конфигурация OLED дисплея (I2C)
DISPLAY_CONFIG = {
    "enabled": True,              # False — дисплей полностью отключён
    "i2c_id": 0,
    "sda_pin": 5,                 # ESP32-C3 + 0.42" OLED: обычно GPIO5
    "scl_pin": 6,                 # ESP32-C3 + 0.42" OLED: обычно GPIO6
    "freq": 400000,
    "address": 0x3C,
    "width": 72,
    "height": 40,
    "col_offset": 28,             # для 72x40; для обычных 128x64 поставьте 0
    "rotate_interval_ms": 2000,   # смена розетки каждые 2 секунды
    "request_display_ms": 2500,   # сколько показывать HTTP-запрос
}