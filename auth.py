class AuthManager:
    def __init__(self, api_key):
        self.api_key = api_key

    def verify_request(self, headers):
        """headers — словарь с ключами в нижнем регистре."""
        api_key = headers.get("x-api-key")
        if api_key is not None:
            return api_key == self.api_key

        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:] == self.api_key

        return False

    def get_auth_error_response(self):
        return {
            "error": "Unauthorized",
            "message": "Неверный или отсутствующий API ключ",
        }