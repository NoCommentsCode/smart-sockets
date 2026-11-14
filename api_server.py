import socket
import json
import time

class APIServer:
    def __init__(self, port, relay_controller, auth_manager, device_info, display=None):
        self.port = port
        self.relay_controller = relay_controller
        self.auth_manager = auth_manager
        self.device_info = device_info
        self.display = display  # DisplayManager или None
    
    def parse_request(self, request):
        """Парсинг HTTP запроса"""
        lines = request.split('\r\n')
        
        # Первая строка: METHOD /path HTTP/1.1
        request_line = lines[0].split(' ')
        method = request_line[0]
        path = request_line[1] if len(request_line) > 1 else '/'
        
        # Парсинг заголовков
        headers = {}
        body = ""
        header_section = True
        
        for i in range(1, len(lines)):
            line = lines[i]
            if line == '':
                header_section = False
                continue
            
            if header_section:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            else:
                body += line
        
        return method, path, headers, body
    
    def send_response(self, client, status_code, status_text, data=None, content_type="application/json"):
        """Отправка HTTP ответа"""
        body = json.dumps(data) if data is not None else ""
        body_bytes = body.encode("utf-8")

        head = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"   # ← длина в БАЙТАХ
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8")

        client.send(head + body_bytes)
    
    def handle_request(self, client, request, client_ip=""):
        method, path, headers, body = self.parse_request(request)
        print(f"{method} {path} from {client_ip}")

        # Показываем запрос ДО проверки авторизации —
        # на дисплее видны даже неавторизованные попытки доступа.
        if self.display is not None:
            self.display.show_request(method, path, client_ip)
        
        # Проверка авторизации для всех API endpoints
        if path.startswith('/api/'):
            if not self.auth_manager.verify_request(headers):
                self.send_response(client, 401, "Unauthorized", 
                                 self.auth_manager.get_auth_error_response())
                return
        
        # Маршрутизация
        if path == '/api/device/info' and method == 'GET':
            self.send_response(client, 200, "OK", self.device_info)
        
        elif path == '/api/relays/status' and method == 'GET':
            statuses = self.relay_controller.get_status()
            self.send_response(client, 200, "OK", {"relays": statuses})
        
        elif path.startswith('/api/relay/') and path.endswith('/status') and method == 'GET':
            # GET /api/relay/<id>/status
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    relay_id = int(parts[3])
                    status = self.relay_controller.get_status(relay_id)
                    if status:
                        self.send_response(client, 200, "OK", status)
                    else:
                        self.send_response(client, 404, "Not Found", 
                                         {"error": "Relay not found"})
                except ValueError:
                    self.send_response(client, 400, "Bad Request", 
                                     {"error": "Invalid relay ID"})
        
        elif path.startswith('/api/relay/') and path.endswith('/on') and method == 'POST':
            # POST /api/relay/<id>/on
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    relay_id = int(parts[3])
                    if self.relay_controller.turn_on(relay_id):
                        self.send_response(client, 200, "OK", 
                                         {"success": True, "message": f"Реле {relay_id} включено"})
                    else:
                        self.send_response(client, 404, "Not Found", 
                                         {"error": "Relay not found"})
                except ValueError:
                    self.send_response(client, 400, "Bad Request", 
                                     {"error": "Invalid relay ID"})
        
        elif path.startswith('/api/relay/') and path.endswith('/off') and method == 'POST':
            # POST /api/relay/<id>/off
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    relay_id = int(parts[3])
                    if self.relay_controller.turn_off(relay_id):
                        self.send_response(client, 200, "OK", 
                                         {"success": True, "message": f"Реле {relay_id} выключено"})
                    else:
                        self.send_response(client, 404, "Not Found", 
                                         {"error": "Relay not found"})
                except ValueError:
                    self.send_response(client, 400, "Bad Request", 
                                     {"error": "Invalid relay ID"})
        
        elif path == '/api/relays/all/on' and method == 'POST':
            self.relay_controller.turn_all_on()
            self.send_response(client, 200, "OK", 
                             {"success": True, "message": "Все реле включены"})
        
        elif path == '/api/relays/all/off' and method == 'POST':
            self.relay_controller.turn_all_off()
            self.send_response(client, 200, "OK", 
                             {"success": True, "message": "Все реле выключены"})
        
        else:
            self.send_response(client, 404, "Not Found", 
                             {"error": "Endpoint not found"})
    
    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.port))
        server_socket.listen(5)

        if self.display is not None:
            server_socket.settimeout(0.2)  # тик для обновления дисплея

        print(f"HTTP сервер запущен на порту {self.port}")

        while True:
            client = None
            try:
                client, addr = server_socket.accept()
            except OSError:
                pass  # таймаут accept — идём обновлять дисплей

            if client is not None:
                try:
                    client.settimeout(2.0)  # защита от зависших клиентов
                    request = client.recv(4096).decode()
                    if request:
                        self.handle_request(client, request, addr[0])
                except Exception as e:
                    print(f"Ошибка обработки запроса: {e}")
                finally:
                    try:
                        client.close()
                    except Exception:
                        pass

            if self.display is not None:
                self.display.update()