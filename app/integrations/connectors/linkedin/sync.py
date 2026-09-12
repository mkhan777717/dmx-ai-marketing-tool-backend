import logging
import os
from typing import Any, Dict, List

import httpx

from app.integrations.connectors.linkedin.exceptions import (
    LinkedInApiError,
    LinkedInAuthError,
)

logger = logging.getLogger(__name__)


class LinkedInSyncEngine:
    USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
    ORGS_ACL_URL = "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee"
    ORG_DETAILS_URL = "https://api.linkedin.com/v2/organizations"

    def __init__(self, access_token: str):
        self.access_token = access_token
        api_version = os.getenv("LINKEDIN_API_VERSION", "202601")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": api_version,
        }

    async def fetch_profile(self) -> Dict[str, Any]:
        """Fetches the authenticated user's OpenID Connect / v2 profile."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.USERINFO_URL, headers=self.headers)

            if response.status_code == 401:
                raise LinkedInAuthError("LinkedIn access token is invalid or expired.")

            if response.status_code != 200:
                raise LinkedInApiError(
                    f"Failed to fetch LinkedIn profile (Status {response.status_code}): {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            sub = data.get("sub") or data.get("id")
            if not sub:
                raise LinkedInApiError(
                    "LinkedIn profile response missing required 'sub' identifier."
                )

            name = (
                data.get("name")
                or f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}".strip()
                or f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
                or "LinkedIn Member"
            )

            return {
                "sub": sub,
                "name": name,
                "localizedFirstName": data.get(
                    "localizedFirstName", data.get("given_name")
                ),
                "localizedLastName": data.get(
                    "localizedLastName", data.get("family_name")
                ),
                "email": data.get("email"),
                "picture": data.get("picture"),
                "raw": data,
            }

    async def fetch_organizations(self) -> List[Dict[str, Any]]:
        """
        Fetches LinkedIn Organizations/Company Pages that the authenticated member administers.
        Returns a list of organization dictionaries containing URN, ID, and name.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(self.ORGS_ACL_URL, headers=self.headers)

            if response.status_code != 200:
                logger.info(
                    f"LinkedIn organization ACL fetch returned status {response.status_code}, skipping org discovery."
                )
                return []

            try:
                data = response.json()
            except Exception:
                return []

            elements = data.get("elements", [])
            orgs: List[Dict[str, Any]] = []

            for elem in elements:
                state = elem.get("state", "APPROVED")
                role = elem.get("role", "")
                if state != "APPROVED":
                    continue

                org_urn = elem.get("organizationalTarget") or elem.get("organization")
                if not org_urn or not str(org_urn).startswith("urn:li:organization:"):
                    continue

                org_id = org_urn.split(":")[-1]
                org_name = f"Company Page ({org_id})"

                try:
                    org_resp = await client.get(
                        f"{self.ORG_DETAILS_URL}/{org_id}", headers=self.headers
                    )
                    if org_resp.status_code == 200:
                        org_data = org_resp.json()
                        org_name = (
                            org_data.get("localizedName")
                            or org_data.get("name")
                            or org_data.get("vanityName")
                            or org_name
                        )
                except Exception as exc:
                    logger.debug(
                        f"Failed to fetch name for organization {org_id}: {exc}"
                    )

                orgs.append(
                    {
                        "organization_urn": org_urn,
                        "org_id": org_id,
                        "name": org_name,
                        "role": role,
                    }
                )

            return orgs

    async def perform_sync(self, sync_type: str = "full") -> Dict[str, Any]:
        """Orchestrates synchronization of profile and administered organizations."""
        if sync_type == "full":
            profile = await self.fetch_profile()
            orgs = await self.fetch_organizations()
            return {
                "profile": profile,
                "organizations": orgs,
                "records_synced": 1 + len(orgs),
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
