"""Управление I2C OLED дисплеем.

В обычном режиме по кругу показывает розетки (по одной, каждые 2 сек).
При HTTP-запросе временно выводит метод, эндпоинт и IP клиента,
затем возвращается к ротации.

Если дисплей выключен в конфиге, не найден на шине или нет драйвера —
модуль молча отключается, остальное устройство работает как обычно.
"""

import time
from machine import Pin, I2C

# ssd1306.py не входит в стандартную прошивку MicroPython.
# Импорт защищён: без файла устройство должно работать (без дисплея).
try:
    from ssd1306 import SSD1306_I2C
    _HAS_DRIVER = True
except ImportError:
    _HAS_DRIVER = False


if _HAS_DRIVER:
    class _SSD1306WithOffset(SSD1306_I2C):
        """SSD1306 с настраиваемым смещением окна колонок.

        Панели 72x40 (0.42") показывают колонки 28..99 памяти
        контроллера, поэтому окно вывода сдвигается на col_offset.
        """

        def __init__(self, width, height, i2c, addr, col_offset=0):
            self.col_offset = col_offset
            super().__init__(width, height, i2c, addr)

        def show(self):
            self.write_cmd(0x21)  # SET_COL_ADDR
            self.write_cmd(self.col_offset)
            self.write_cmd(self.col_offset + self.width - 1)
            self.write_cmd(0x22)  # SET_PAGE_ADDR
            self.write_cmd(0)
            self.write_cmd(self.pages - 1)
            self.write_data(self.buffer)


# Шрифт framebuf — ASCII 8x8, кириллицу транслитерируем.
# Многобуквенные заглавные (Ж, Ц, Ч, Ш, Щ, Ю, Я) даём в виде "Zh", "Ts"...
# чтобы "Жук" превращалось в "Zhuk", а не "ZHuk".
_TRANSLIT = {
    # строчные
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
    # заглавные
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E",
    "Ё": "E", "Ж": "Zh", "З": "Z", "И": "I", "Й": "Y", "К": "K",
    "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R",
    "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "H", "Ц": "Ts",
    "Ч": "Ch", "Ш": "Sh", "Щ": "Sch", "Ъ": "", "Ы": "Y", "Ь": "",
    "Э": "E", "Ю": "Yu", "Я": "Ya",
}

def _to_ascii(text):
    # Регистр сохраняем: латиница и цифры проходят как есть,
    # кириллица заменяется по таблице (строчные и заглавные).
    return "".join(_TRANSLIT.get(ch, ch) for ch in text)


class DisplayManager:
    def __init__(self, config, relay_controller, device_info=None):
        self.enabled = bool(config.get("enabled", False))
        self.relays = relay_controller
        self.rotate_ms = config.get("rotate_interval_ms", 2000)
        self.request_ms = config.get("request_display_ms", 2500)

        self.oled = None
        self.chars = 0          # символов в строке (width // 8)
        self.rows = 0           # строк (height // 8)
        self._index = 0
        self._last_rotate = 0
        self._overlay_lines = None
        self._overlay_until = 0

        device_ip = (device_info or {}).get("ip") or ""
        self._ip_line = ("IP " + ".".join(device_ip.split(".")[-2:])) if device_ip else ""

        if self.enabled:
            self._init_display(config)

    # ---------- инициализация ----------

    def _init_display(self, cfg):
        if not _HAS_DRIVER:
            print("Display: ssd1306.py не найден на плате, дисплей отключён")
            self.enabled = False
            return
        try:
            i2c = I2C(
                cfg.get("i2c_id", 0),
                scl=Pin(cfg["scl_pin"]),
                sda=Pin(cfg["sda_pin"]),
                freq=cfg.get("freq", 400000),
            )
            addr = cfg.get("address", 0x3C)
            if addr not in i2c.scan():
                print("Display: 0x%02X не найден на шине, дисплей отключён" % addr)
                self.enabled = False
                return

            self.oled = _SSD1306WithOffset(
                cfg.get("width", 72), cfg.get("height", 40),
                i2c, addr, cfg.get("col_offset", 28),
            )
            self.chars = self.oled.width // 8
            self.rows = self.oled.height // 8
            self.oled.fill(0)
            self.oled.show()
            self._last_rotate = time.ticks_ms()
            self._render_relay()
            print("Display: OK (%dx%d)" % (self.oled.width, self.oled.height))
        except Exception as e:
            # Отказ дисплея не должен ронять управление розетками
            print("Display: ошибка инициализации:", e)
            self.enabled = False

    # ---------- публичные методы ----------

    def update(self):
        """Тик из главного цикла сервера. Не блокирует."""
        if not self.enabled:
            return
        now = time.ticks_ms()

        if self._overlay_lines is not None:
            if time.ticks_diff(self._overlay_until, now) > 0:
                return  # оверлей ещё активен
            self._overlay_lines = None
            self._last_rotate = now
            self._render_relay()
            return

        if time.ticks_diff(now, self._last_rotate) >= self.rotate_ms:
            self._last_rotate = now
            self._index += 1
            self._render_relay()

    def show_request(self, method, path, client_ip):
        """Показать HTTP-запрос на request_ms мс, затем вернуть ротацию."""
        if not self.enabled:
            return
        lines = [method[:self.chars]]
        lines += self._wrap(path, 2)
        lines += self._wrap(client_ip, 2)
        self._show_overlay(lines, self.request_ms)

    def show_message(self, lines, duration_ms=2000):
        """Произвольное сообщение (например, при загрузке)."""
        if not self.enabled:
            return
        out = []
        for line in lines:
            out += self._wrap(line, self.rows - len(out))
            if len(out) >= self.rows:
                break
        self._show_overlay(out, duration_ms)

    # ---------- внутреннее ----------

    def _show_overlay(self, lines, duration_ms):
        self._overlay_lines = lines[:self.rows]
        self._overlay_until = time.ticks_add(time.ticks_ms(), duration_ms)
        self._render_lines(self._overlay_lines)

    def _wrap(self, text, max_lines):
        """Разбить текст на строки по chars символов, не более max_lines."""
        if max_lines <= 0:
            return []
        text = _to_ascii(text)
        chunks = [text[i:i + self.chars] for i in range(0, len(text), self.chars)] or [""]
        if len(chunks) > max_lines:
            chunks = chunks[:max_lines]
            chunks[-1] = chunks[-1][:self.chars - 2] + ".."
        return chunks

    def _render_lines(self, lines):
        self.oled.fill(0)
        for i, line in enumerate(lines):
            self.oled.text(line, 0, i * 8, 1)
        self.oled.show()

    def _render_relay(self):
        statuses = self.relays.get_status()
        if not statuses:
            self._render_lines(["No relays"])
            return
        self._index %= len(statuses)
        r = statuses[self._index]

        header = "{}/{} ID:{}".format(self._index + 1, len(statuses), r["id"])
        name = _to_ascii(r["name"])[:self.chars]
        state = "ON" if r["state"] else "OFF"

        o = self.oled
        o.fill(0)
        o.text(header[:self.chars], 0, 0, 1)          # "1/3 ID:1"
        o.text(name, 0, 8, 1)                          # "rozetka 1"
        o.fill_rect(0, 16, o.width, 8, 1)              # инверсная плашка
        o.text(state, (o.width - len(state) * 8) // 2, 16, 0)
        if self._ip_line and self.rows > 3:
            o.text(self._ip_line[:self.chars], 0, 24, 1)  # "IP 1.100"
        o.show()