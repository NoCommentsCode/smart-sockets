# Конфигурация устройства
WIFI_SSID = "111"
WIFI_PASSWORD = "guga777gugi1"

# Конфигурация реле (GPIO пины ESP32)
RELAY_PINS = [
    {"id": 1, "pin": 0, "name": "Розетка 1"},
    {"id": 2, "pin": 1, "name": "Розетка 2"},
    {"id": 3, "pin": 2, "name": "Розетка 3"},
]

# API ключ для авторизации (измените на свой секретный ключ)
API_KEY = "your-secret-api-key-change-this"

# Настройки сервера
HTTP_PORT = 80
DEVICE_NAME = "Smart Sockets ESP32"
DEVICE_VERSION = "1.0.0"

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