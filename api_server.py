import json
import socket
import time

from config_store import ConfigError

MAX_REQUEST = 8192


class APIServer:
    def __init__(self, port, relay_controller, auth_manager, device_info,
                 device_config=None, display=None):
        self.port = port
        self.relay_controller = relay_controller
        self.auth_manager = auth_manager
        self.device_info = device_info
        self.device_config = device_config
        self.display = display
        self._start = time.ticks_ms()

    # ---------- HTTP ----------

    def read_request(self, client):
        """Читаем заголовки целиком, затем тело по Content-Length."""
        data = b""
        while True:
            idx = data.find(b"\r\n\r\n")
            if idx >= 0:
                break
            if len(data) > MAX_REQUEST:
                return None
            chunk = client.recv(1024)
            if not chunk:
                return None
            data += chunk

        head = data[:idx]
        body = data[idx + 4:]

        length = 0
        for line in head.split(b"\r\n")[1:]:
            if b":" in line:
                key, value = line.split(b":", 1)
                if key.strip().lower() == b"content-length":
                    try:
                        length = int(value.strip().decode())
                    except ValueError:
                        length = 0
        if length > MAX_REQUEST:
            return None
        while len(body) < length:
            chunk = client.recv(min(1024, length - len(body)))
            if not chunk:
                break
            body += chunk

        return head + b"\r\n\r\n" + body

    def parse_request(self, raw):
        idx = raw.find(b"\r\n\r\n")
        head = raw[:idx].decode()
        body = raw[idx + 4:].decode()

        lines = head.split("\r\n")
        request_line = lines[0].split(" ")
        method = request_line[0]
        path = request_line[1] if len(request_line) > 1 else "/"

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        return method, path, headers, body

    def send_response(self, client, status_code, status_text, data=None,
                      content_type="application/json"):
        body = json.dumps(data) if data is not None else ""
        body_bytes = body.encode("utf-8")
        head = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8")
        client.send(head + body_bytes)

    # ---------- Роутинг ----------

    def handle_request(self, client, raw, client_ip=""):
        method, path, headers, body = self.parse_request(raw)
        print(f"{method} {path} from {client_ip}")

        if self.display is not None:
            self.display.show_request(method, path, client_ip)

        if path.startswith("/api/") and not self.auth_manager.verify_request(headers):
            self.send_response(client, 401, "Unauthorized",
                               self.auth_manager.get_auth_error_response())
            return

        if "?" in path:
            path = path.split("?", 1)[0]

        if path == "/api/device/info" and method == "GET":
            info = dict(self.device_info)
            info["name"] = self.device_config.device_name if self.device_config else info["name"]
            info["uptime"] = time.ticks_diff(time.ticks_ms(), self._start) // 1000
            self.send_response(client, 200, "OK", info)

        elif path == "/api/device/config" and method == "GET":
            if self.device_config is None:
                self.send_response(client, 501, "Not Implemented",
                                   {"error": "Config storage is not available"})
                return
            self.send_response(client, 200, "OK", self.device_config.public())

        elif path == "/api/device/config" and method == "PATCH":
            self._handle_config_update(client, body)

        elif path == "/api/relays/status" and method == "GET":
            self.send_response(client, 200, "OK",
                               {"relays": self.relay_controller.get_status()})

        elif path.startswith("/api/relay/"):
            self._handle_relay(client, method, path)

        elif path == "/api/relays/all/on" and method == "POST":
            self.relay_controller.turn_all_on()
            self.send_response(client, 200, "OK",
                               {"success": True, "message": "Все реле включены"})

        elif path == "/api/relays/all/off" and method == "POST":
            self.relay_controller.turn_all_off()
            self.send_response(client, 200, "OK",
                               {"success": True, "message": "Все реле выключены"})

        else:
            self.send_response(client, 404, "Not Found", {"error": "Endpoint not found"})

    def _handle_relay(self, client, method, path):
        parts = path.split("/")
        if len(parts) != 5:
            self.send_response(client, 404, "Not Found", {"error": "Endpoint not found"})
            return
        try:
            relay_id = int(parts[3])
        except ValueError:
            self.send_response(client, 400, "Bad Request", {"error": "Invalid relay ID"})
            return

        action = parts[4]
        if action == "status" and method == "GET":
            status = self.relay_controller.get_status(relay_id)
            if status:
                self.send_response(client, 200, "OK", status)
            else:
                self.send_response(client, 404, "Not Found", {"error": "Relay not found"})
        elif action in ("on", "off") and method == "POST":
            ok = (self.relay_controller.turn_on(relay_id) if action == "on"
                  else self.relay_controller.turn_off(relay_id))
            if ok:
                text = "включено" if action == "on" else "выключено"
                self.send_response(client, 200, "OK",
                                   {"success": True, "message": f"Реле {relay_id} {text}"})
            else:
                self.send_response(client, 404, "Not Found", {"error": "Relay not found"})
        else:
            self.send_response(client, 404, "Not Found", {"error": "Endpoint not found"})

    def _handle_config_update(self, client, body):
        if self.device_config is None:
            self.send_response(client, 501, "Not Implemented",
                               {"error": "Config storage is not available"})
            return
        try:
            payload = json.loads(body) if body else {}
        except ValueError:
            self.send_response(client, 400, "Bad Request", {"error": "Invalid JSON"})
            return

        try:
            updated = self.device_config.update(payload)
        except ConfigError as e:
            self.send_response(client, 400, "Bad Request", {"error": str(e)})
            return
        except Exception as e:
            self.send_response(client, 500, "Internal Server Error",
                               {"error": "Config save failed: %s" % e})
            return

        # Применяем имена сразу; default_state — только при следующей загрузке
        self.device_info["name"] = updated["device_name"]
        self.relay_controller.apply_config(self.device_config)
        self.send_response(client, 200, "OK", updated)

    # ---------- Цикл ----------

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", self.port))
        server_socket.listen(5)

        if self.display is not None:
            server_socket.settimeout(0.2)

        print(f"HTTP сервер запущен на порту {self.port}")

        while True:
            client = None
            try:
                client, addr = server_socket.accept()
            except OSError:
                pass

            if client is not None:
                try:
                    client.settimeout(2.0)
                    raw = self.read_request(client)
                    if raw:
                        self.handle_request(client, raw, addr[0])
                    else:
                        self.send_response(client, 400, "Bad Request",
                                           {"error": "Malformed request"})
                except Exception as e:
                    print(f"Ошибка обработки запроса: {e}")
                    try:
                        self.send_response(client, 400, "Bad Request",
                                           {"error": "Bad request"})
                    except Exception:
                        pass
                finally:
                    try:
                        client.close()
                    except Exception:
                        pass

            if self.display is not None:
                self.display.update()