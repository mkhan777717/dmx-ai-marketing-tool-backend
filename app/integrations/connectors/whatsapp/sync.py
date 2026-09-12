import logging
from typing import Any, Dict, List

import httpx

from app.integrations.connectors.whatsapp.exceptions import WhatsAppApiError
from app.integrations.connectors.whatsapp.schemas import (
    WhatsAppPhoneNumbersResponse,
)
from app.integrations.constants import META_GRAPH_API_VERSION
from app.integrations.exceptions import OAuthTokenError

logger = logging.getLogger(__name__)


class WhatsAppSyncEngine:
    GRAPH_API_VERSION = META_GRAPH_API_VERSION
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.params = {"access_token": self.access_token}

    def _parse_and_raise_error(
        self, response: httpx.Response, action_description: str
    ) -> None:
        """
        Parses Meta Graph API error response and raises OAuthTokenError if and only if
        the error code explicitly indicates an invalid or expired access token (e.g. code 190).
        For non-token errors (e.g. code 100 missing field/permissions), raises WhatsAppApiError
        preserving the exact Meta error message and code.
        """
        err_code = None
        err_message = None

        try:
            err_data = response.json().get("error", {})
            err_code = err_data.get("code")
            err_message = err_data.get("message")
        except Exception:
            pass

        # Meta Graph API error code 190 explicitly indicates invalid or expired access token.
        if response.status_code in (400, 401) and err_code == 190:
            raise OAuthTokenError("WhatsApp/Meta access token is invalid or expired.")

        # For non-token errors (such as code 100 'Tried accessing nonexisting field'),
        # raise WhatsAppApiError preserving original Meta error message details.
        detail_msg = err_message or f"Status: {response.status_code}"
        full_msg = f"{action_description}: {detail_msg}"
        if err_code is not None:
            full_msg = f"{action_description} (Code {err_code}): {detail_msg}"

        raise WhatsAppApiError(
            full_msg,
            status_code=response.status_code,
        )

    async def fetch_wabas(self) -> List[Dict[str, Any]]:
        """
        Fetches the WhatsApp Business Accounts (WABAs) associated with the authorized Meta identity.
        Uses a resilient multi-strategy discovery flow compatible with Meta Cloud API & Embedded Signup:
        1. Discovers target WABA IDs via GET /debug_token (extracting granular_scopes for whatsapp_business_management).
        2. Discovers owned/client WABAs via Business Manager endpoints (GET /me/businesses).
        3. Queries direct details for each discovered WABA ID (GET /{waba_id}).
        """
        discovered_waba_ids: set[str] = set()
        wabas_map: dict[str, dict[str, Any]] = {}

        async with httpx.AsyncClient() as client:
            # 1. Discover target WABA IDs via debug_token
            debug_url = f"{self.BASE_URL}/debug_token"
            debug_params = {
                "input_token": self.access_token,
                "access_token": self.access_token,
            }
            debug_res = await client.get(debug_url, params=debug_params)
            if debug_res.status_code == 200:
                try:
                    debug_data = debug_res.json().get("data", {})
                    granular_scopes = debug_data.get("granular_scopes", [])
                    for scope_item in granular_scopes:
                        if scope_item.get("scope") in (
                            "whatsapp_business_management",
                            "whatsapp_business_messaging",
                        ):
                            target_ids = scope_item.get("target_ids", [])
                            for tid in target_ids:
                                if tid:
                                    discovered_waba_ids.add(str(tid))
                except Exception as e:
                    logger.warning(f"Error parsing debug_token granular_scopes: {e}")
            elif debug_res.status_code in (400, 401):
                self._parse_and_raise_error(debug_res, "Failed to validate debug_token")

            # 2. Discover WABA IDs via Business Manager (/me/businesses)
            businesses_url = f"{self.BASE_URL}/me/businesses"
            businesses_params = {**self.params, "fields": "id,name"}
            b_res = await client.get(businesses_url, params=businesses_params)
            if b_res.status_code == 200:
                try:
                    b_data = b_res.json().get("data", [])
                    for b in b_data:
                        b_id = b.get("id")
                        if not b_id:
                            continue
                        owned_url = (
                            f"{self.BASE_URL}/{b_id}/owned_whatsapp_business_accounts"
                        )
                        owned_params = {
                            **self.params,
                            "fields": "id,name,currency,timezone_id",
                        }
                        owned_res = await client.get(owned_url, params=owned_params)
                        if owned_res.status_code == 200:
                            for w in owned_res.json().get("data", []):
                                w_id = str(w.get("id", ""))
                                if w_id:
                                    discovered_waba_ids.add(w_id)
                                    wabas_map[w_id] = w
                except Exception as e:
                    logger.warning(f"Error discovering WABAs via Business Manager: {e}")
            elif b_res.status_code in (400, 401):
                try:
                    err_code = b_res.json().get("error", {}).get("code")
                    if err_code == 190:
                        self._parse_and_raise_error(
                            b_res, "Failed to validate Meta access token"
                        )
                except Exception:
                    pass

            # 3. For any WABA IDs discovered via debug_token not yet in wabas_map, fetch direct details
            for waba_id in discovered_waba_ids:
                if waba_id not in wabas_map:
                    waba_url = f"{self.BASE_URL}/{waba_id}"
                    waba_params = {
                        **self.params,
                        "fields": "id,name,currency,timezone_id",
                    }
                    w_res = await client.get(waba_url, params=waba_params)
                    if w_res.status_code == 200:
                        try:
                            w_data = w_res.json()
                            wabas_map[waba_id] = w_data
                        except Exception as e:
                            logger.warning(
                                f"Error fetching WABA details for {waba_id}: {e}"
                            )
                    elif w_res.status_code in (400, 401):
                        try:
                            err_code = w_res.json().get("error", {}).get("code")
                            if err_code == 190:
                                self._parse_and_raise_error(
                                    w_res, f"Failed to fetch WABA {waba_id}"
                                )
                        except Exception:
                            pass

            if not wabas_map and not discovered_waba_ids:
                # Validate token via /me if no WABAs discovered
                me_url = f"{self.BASE_URL}/me"
                me_res = await client.get(me_url, params=self.params)
                if me_res.status_code != 200:
                    self._parse_and_raise_error(
                        me_res, "Failed to validate Meta access token via /me"
                    )

            return list(wabas_map.values())

    async def fetch_phone_numbers(self, waba_id: str) -> List[Dict[str, Any]]:
        """
        Fetches the registered Phone Numbers for a specific WABA ID.
        Query: GET /{waba_id}/phone_numbers
        """
        url = f"{self.BASE_URL}/{waba_id}/phone_numbers"
        params = {
            **self.params,
            "fields": "id,display_phone_number,verified_name,code_verification_status,quality_rating",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                self._parse_and_raise_error(
                    response, f"Failed to fetch phone numbers for WABA {waba_id}"
                )

            data = response.json()
            validated_response = WhatsAppPhoneNumbersResponse(**data)
            return [pn.model_dump() for pn in validated_response.data]

    async def fetch_wabas_with_phone_numbers(self) -> List[Dict[str, Any]]:
        """
        Discovers all WABAs and fetches their associated phone numbers.
        Returns a list of phone number dictionaries enriched with WABA details and access_token.
        """
        wabas = await self.fetch_wabas()
        results: List[Dict[str, Any]] = []

        for waba in wabas:
            waba_id = waba["id"]
            phone_numbers = await self.fetch_phone_numbers(waba_id)
            for pn in phone_numbers:
                results.append(
                    {
                        "phone_number_id": pn["id"],
                        "waba_id": waba_id,
                        "display_phone_number": pn.get("display_phone_number", ""),
                        "verified_name": pn.get("verified_name")
                        or pn.get("display_phone_number")
                        or "WhatsApp Account",
                        "quality_rating": pn.get("quality_rating"),
                        "access_token": self.access_token,
                    }
                )

        return results

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process for WhatsApp WABAs & Phone Numbers."""
        if sync_type == "full":
            discovered = await self.fetch_wabas_with_phone_numbers()
            return {
                "whatsapp_phone_numbers": discovered,
                "records_synced": len(discovered),
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
