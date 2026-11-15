from machine import Pin


class RelayController:
    def __init__(self, relay_pins, device_config=None):
        self.relays = {}
        for relay_config in relay_pins:
            relay_id = relay_config["id"]
            stored = device_config.get_relay(relay_id) if device_config else None

            name = stored["name"] if stored else relay_config["name"]
            if stored:
                default_state = bool(stored["default_state"])
            else:
                default_state = bool(relay_config.get("default_state", False))

            pin = Pin(relay_config["pin"], Pin.OUT)
            self.relays[relay_id] = {
                "pin": pin,
                "name": name,
                "state": False,
                "default_state": default_state,
            }
            # Состояние по умолчанию применяется один раз при загрузке
            self._apply(relay_id, default_state)

    def _apply(self, relay_id, state):
        relay = self.relays[relay_id]
        relay["pin"].value(1 if state else 0)
        relay["state"] = state

    def apply_config(self, device_config):
        """Обновить имена и default_state из конфига. Текущее состояние НЕ трогаем."""
        for relay_id, relay in self.relays.items():
            stored = device_config.get_relay(relay_id)
            if stored:
                relay["name"] = stored["name"]
                relay["default_state"] = bool(stored["default_state"])

    def turn_on(self, relay_id):
        if relay_id in self.relays:
            self._apply(relay_id, True)
            return True
        return False

    def turn_off(self, relay_id):
        if relay_id in self.relays:
            self._apply(relay_id, False)
            return True
        return False

    def get_status(self, relay_id=None):
        if relay_id is not None:
            if relay_id not in self.relays:
                return None
            relay = self.relays[relay_id]
            return {
                "id": relay_id,
                "name": relay["name"],
                "state": relay["state"],
                "state_text": "включено" if relay["state"] else "выключено",
                "default_state": relay["default_state"],
            }

        return [
            {
                "id": rid,
                "name": self.relays[rid]["name"],
                "state": self.relays[rid]["state"],
                "state_text": "включено" if self.relays[rid]["state"] else "выключено",
                "default_state": self.relays[rid]["default_state"],
            }
            for rid in sorted(self.relays)
        ]

    def turn_all_on(self):
        for relay_id in self.relays:
            self.turn_on(relay_id)

    def turn_all_off(self):
        for relay_id in self.relays:
            self.turn_off(relay_id)