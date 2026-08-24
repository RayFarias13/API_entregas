import requests

from django.conf import settings


class NuvemshopAPI:
    BASE_URL = "https://api.nuvemshop.com.br/2025-03"

    def __init__(self):
        self.store_id = getattr(settings, "NUVEMSHOP_STORE_ID", "")
        self.access_token = getattr(settings,"NUVEMSHOP_ACCESS_TOKEN","",)        
        self.access_agent = getattr(settings,"NUVEMSHOP_USER_AGENT","",)

        if not self.store_id:
            raise ValueError(
                "NUVEMSHOP_STORE_ID não configurado."
            )

        if not self.access_token:
            raise ValueError(
                "NUVEMSHOP_ACCESS_TOKEN não configurado."
            )

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": f"{self.access_agent}",
            "Content-Type": "application/json",
        }

    def listar_pedidos(self, status=None):
        url = (
            f"{self.BASE_URL}/"
            f"{self.store_id}/orders"
        )

        params = {
            "per_page": 100,
            
        }

        if status:
            params["shipping_status"] = status

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        pedidos = response.json()

        if not isinstance(pedidos, list):
            return []

        return pedidos

    def buscar_pedido(self, pedido_id):
        url = (
            f"{self.BASE_URL}/"
            f"{self.store_id}/orders/"
            f"{pedido_id}"
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def atualizar_fulfillment(
        self,
        pedido_id,
        fulfillment_id,
        status,
        tracking_code=None,
        tracking_url=None,
    ):
        """
        Atualiza o status de um Fulfillment Order.
        """

        url = (
            f"{self.BASE_URL}/"
            f"{self.store_id}/orders/"
            f"{pedido_id}/fulfillment-orders/"
            f"{fulfillment_id}"
        )

        payload = {
            "status": status,
        }

        if tracking_code or tracking_url:

            payload["tracking_info"] = {
                "code": tracking_code or "",
                "url": tracking_url or "",
            }

        response = requests.patch(
            url,
            headers=self.headers,
            json=payload,
            timeout=30,
        )


    def listar_fulfillments(self, pedido_id):

        url = (
            f"{self.BASE_URL}/"
            f"{self.store_id}/orders/"
            f"{pedido_id}/fulfillment-orders"
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        dados = response.json()

        if not isinstance(dados, list):
            return []

        return dados