import requests
from django.conf import settings


class NuvemshopAPI:
    BASE_URL = "https://api.nuvemshop.com.br/v1"

    def __init__(self):
        self.store_id = settings.NUVEMSHOP_STORE_ID
        self.access_token = settings.NUVEMSHOP_ACCESS_TOKEN
        self.user_agent = settings.NUVEMSHOP_USER_AGENT

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }

    def listar_pedidos(
        self,
        page=1,
        per_page=30,
        status=None,
    ):
        url = f"{self.BASE_URL}/{self.store_id}/orders"

        params = {
            "page": page,
            "per_page": per_page,
        }

        if status:
            params["status"] = status

        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()
