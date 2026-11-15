"""Персистентный конфиг устройства.

config.py — заводские значения (код, обновляется с прошивкой).
device_config.json — пользовательские изменения (имена, default_state).

Файл пишется атомарно (tmp + rename) и только если данные реально изменились,
чтобы беречь флеш. Повреждённый файл не роняет устройство — берём заводские值.
"""

import json
import os

import config as defaults

CONFIG_FILE = "device_config.json"
MAX_NAME_LEN = 32


class ConfigError(Exception):
    """Ошибка валидации пользовательского ввода."""


def _clean_name(value, field):
    if not isinstance(value, str):
        raise ConfigError("%s must be a string" % field)
    value = value.strip()
    if not value:
        raise ConfigError("%s must not be empty" % field)
    if len(value) > MAX_NAME_LEN:
        raise ConfigError("%s must be at most %d characters" % (field, MAX_NAME_LEN))
    return value


class DeviceConfig:
    def __init__(self):
        self._data = self._factory()
        self._load()

    # ---------- заводские значения ----------

    def _factory(self):
        return {
            "device_name": defaults.DEVICE_NAME,
            "relays": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "default_state": bool(r.get("default_state", False)),
                }
                for r in defaults.RELAY_PINS
            ],
        }

    # ---------- чтение/запись ----------

    def _load(self):
        try:
            with open(CONFIG_FILE) as f:
                stored = json.loads(f.read())
        except OSError:
            return  # файла нет — первый запуск
        except ValueError:
            print("Config: повреждённый %s, использую заводские значения" % CONFIG_FILE)
            return

        if not isinstance(stored, dict):
            return

        if isinstance(stored.get("device_name"), str):
            self._data["device_name"] = stored["device_name"][:MAX_NAME_LEN]

        stored_relays = {}
        for item in stored.get("relays", []):
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                stored_relays[item["id"]] = item

        for relay in self._data["relays"]:
            item = stored_relays.get(relay["id"])
            if not item:
                continue
            if isinstance(item.get("name"), str):
                relay["name"] = item["name"][:MAX_NAME_LEN]
            if isinstance(item.get("default_state"), bool):
                relay["default_state"] = item["default_state"]

    def _save(self):
        payload = json.dumps(self._data)
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write(payload)
        try:
            os.remove(CONFIG_FILE)
        except OSError:
            pass
        os.rename(tmp, CONFIG_FILE)

    # ---------- публичный API ----------

    @property
    def device_name(self):
        return self._data["device_name"]

    def get_relay(self, relay_id):
        for relay in self._data["relays"]:
            if relay["id"] == relay_id:
                return dict(relay)
        return None

    def public(self):
        """То, что отдаём наружу (пины GPIO не светим)."""
        return {
            "device_name": self._data["device_name"],
            "relays": [dict(r) for r in self._data["relays"]],
        }

    def update(self, payload):
        """Частичное обновление: device_name и/или любые поля любых розеток."""
        if not isinstance(payload, dict):
            raise ConfigError("Body must be a JSON object")
        if "device_name" not in payload and "relays" not in payload:
            raise ConfigError("Nothing to update: expected device_name or relays")

        device_name = self._data["device_name"]
        relays = {r["id"]: dict(r) for r in self._data["relays"]}

        if "device_name" in payload:
            device_name = _clean_name(payload["device_name"], "device_name")

        if "relays" in payload:
            items = payload["relays"]
            if not isinstance(items, list):
                raise ConfigError("relays must be a list")
            seen = set()
            for item in items:
                if not isinstance(item, dict):
                    raise ConfigError("Each relay update must be an object")
                rid = item.get("id")
                if not isinstance(rid, int) or isinstance(rid, bool):
                    raise ConfigError("Relay id must be an integer")
                if rid not in relays:
                    raise ConfigError("Unknown relay id: %s" % rid)
                if rid in seen:
                    raise ConfigError("Duplicate relay id: %s" % rid)
                seen.add(rid)
                if "name" not in item and "default_state" not in item:
                    raise ConfigError("Relay %s: nothing to update" % rid)
                if "name" in item:
                    relays[rid]["name"] = _clean_name(item["name"], "name")
                if "default_state" in item:
                    if not isinstance(item["default_state"], bool):
                        raise ConfigError("default_state must be a boolean")
                    relays[rid]["default_state"] = item["default_state"]

        new_data = {
            "device_name": device_name,
            "relays": [relays[r["id"]] for r in self._data["relays"]],
        }

        if json.dumps(new_data) == json.dumps(self._data):
            return self.public()  # ничего не изменилось — флеш не трогаем

        self._data = new_data
        self._save()
        return self.public()

    def reset(self):
        """Сброс к заводским значениям (на будущее, для кнопки в админке)."""
        self._data = self._factory()
        try:
            os.remove(CONFIG_FILE)
        except OSError:
            pass
        return self.public()