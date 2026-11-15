import time

from config import (WIFI_SSID, WIFI_PASSWORD, RELAY_PINS, API_KEY,
                    HTTP_PORT, DEVICE_VERSION, DISPLAY_CONFIG)
from config_store import DeviceConfig
from wifi_manager import WiFiManager
from relay_controller import RelayController
from auth import AuthManager
from api_server import APIServer
from display_manager import DisplayManager


def main():
    print("=" * 50)
    device_config = DeviceConfig()
    print(f"{device_config.device_name} v{DEVICE_VERSION}")
    print("=" * 50)

    wifi = WiFiManager(WIFI_SSID, WIFI_PASSWORD)
    if not wifi.connect():
        print("Не удалось подключиться к WiFi. Перезапуск через 5 секунд...")
        time.sleep(5)
        import machine
        machine.reset()

    relay_controller = RelayController(RELAY_PINS, device_config)
    auth_manager = AuthManager(API_KEY)

    device_info = {
        "name": device_config.device_name,
        "version": DEVICE_VERSION,
        "ip": wifi.get_ip(),
        "relays_count": len(RELAY_PINS),
        "uptime": 0,
    }

    display = DisplayManager(DISPLAY_CONFIG, relay_controller, device_info)
    display.show_message(["WiFi OK", wifi.get_ip()], 2000)

    api_server = APIServer(HTTP_PORT, relay_controller, auth_manager, device_info,
                           device_config=device_config, display=display)

    print("\nДоступные endpoints:")
    print("  GET   /api/device/info        - Информация об устройстве")
    print("  GET   /api/device/config      - Редактируемый конфиг")
    print("  PATCH /api/device/config      - Изменить имя/имена розеток/default_state")
    print("  GET   /api/relays/status      - Статус всех розеток")
    print("  GET   /api/relay/<id>/status  - Статус конкретной розетки")
    print("  POST  /api/relay/<id>/on      - Включить розетку")
    print("  POST  /api/relay/<id>/off     - Выключить розетку")
    print("  POST  /api/relays/all/on      - Включить все розетки")
    print("  POST  /api/relays/all/off     - Выключить все розетки")
    print("=" * 50)

    api_server.start()


if __name__ == "__main__":
    main()