class AuthManager:
    def __init__(self, api_key):
        self.api_key = api_key
    
    def verify_request(self, headers):
        """Проверка API ключа в заголовках запроса"""
        # Проверка заголовка X-API-Key
        if "X-API-Key" in headers:
            return headers["X-API-Key"] == self.api_key
        
        # Проверка Authorization: Bearer <token>
        if "Authorization" in headers:
            auth_header = headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Убираем "Bearer "
                return token == self.api_key
        
        return False
    
    def get_auth_error_response(self):
        """Ответ при ошибке авторизации"""
        return {
            "error": "Unauthorized",
            "message": "Неверный или отсутствующий API ключ"
        }