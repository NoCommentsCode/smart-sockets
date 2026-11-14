# Smart Sockets ESP32

Система умных розеток на базе ESP32 с REST API управлением.

## Возможности

- Управление до 10 реле (розеток)
- WiFi подключение к домашней сети
- REST API для управления
- Авторизация через API ключ
- Модульная архитектура

## Аппаратные требования

- ESP32 development board
- Реле модули (5V или 3.3V)
- Блок питания 5V

## Подключение

Подключите реле к следующим GPIO пинам ESP32:
- Реле 1: GPIO 25
- Реле 2: GPIO 26
- Реле 3: GPIO 27

Вы можете изменить пины в файле `config.py`.

## Установка

1. Установите MicroPython на ESP32: https://micropython.org/download/ESP32_GENERIC/

2. Скопируйте все файлы проекта на ESP32:
```bash
# Используя mpremote или Thonny IDE
mpremote cp config.py :
mpremote cp wifi_manager.py :
mpremote cp relay_controller.py :
mpremote cp auth.py :
mpremote cp api_server.py :
mpremote cp main.py :