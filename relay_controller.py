from machine import Pin
import json

class RelayController:
    def __init__(self, relay_pins):
        self.relays = {}
        for relay_config in relay_pins:
            relay_id = relay_config["id"]
            pin_num = relay_config["pin"]
            name = relay_config["name"]
            
            # Инициализация пина
            pin = Pin(pin_num, Pin.OUT)
            pin.value(0)  # Изначально выключено
            
            self.relays[relay_id] = {
                "pin": pin,
                "name": name,
                "state": False
            }
    
    def turn_on(self, relay_id):
        """Включить реле по ID"""
        if relay_id in self.relays:
            self.relays[relay_id]["pin"].value(1)
            self.relays[relay_id]["state"] = True
            return True
        return False
    
    def turn_off(self, relay_id):
        """Выключить реле по ID"""
        if relay_id in self.relays:
            self.relays[relay_id]["pin"].value(0)
            self.relays[relay_id]["state"] = False
            return True
        return False
    
    def get_status(self, relay_id=None):
        """Получить статус реле"""
        if relay_id is not None:
            if relay_id in self.relays:
                relay = self.relays[relay_id]
                return {
                    "id": relay_id,
                    "name": relay["name"],
                    "state": relay["state"],
                    "state_text": "включено" if relay["state"] else "выключено"
                }
            return None
        
        # Статус всех реле
        statuses = []
        for rid, relay in self.relays.items():
            statuses.append({
                "id": rid,
                "name": relay["name"],
                "state": relay["state"],
                "state_text": "включено" if relay["state"] else "выключено"
            })
        return statuses
    
    def turn_all_on(self):
        """Включить все реле"""
        for relay_id in self.relays:
            self.turn_on(relay_id)
    
    def turn_all_off(self):
        """Выключить все реле"""
        for relay_id in self.relays:
            self.turn_off(relay_id)