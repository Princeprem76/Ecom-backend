# core/services/bing_visual_search.py
import requests
from typing import Optional, Tuple

class ImageProductSearch:
    """
    Thin wrapper around Bing Visual Search to extract a single best product name
    from an image (bytes upload) or image URL.
    """

    def __init__(self, endpoint: str, subscription_key: str, market: str = "en-US", timeout: int = 8):
        self.endpoint = endpoint.rstrip("/")
        self.key = subscription_key
        self.market = market
        self.timeout = timeout

    def extract_product_name(
        self,
        image_file=None,          # Django InMemoryUploadedFile/File
    ) -> Optional[str]:
        """
        Returns a single product name (string) or None if not found.
        Prefers product-style actions; falls back to tags when needed.
        """
        headers = {"Ocp-Apim-Subscription-Key": self.key}
        params = {"mkt": self.market}

        files = None
        data = None

        if image_file is not None:
            # Binary upload
            files = {"image": (getattr(image_file, "name", "upload.jpg"), image_file, "application/octet-stream")}
        else:
            raise ValueError("Provide either image_file or image_url")

        try:
            if files:
                resp = requests.post(self.endpoint, headers=headers, params=params, files=files, timeout=self.timeout)
            else:
                resp = requests.post(self.endpoint, headers=headers, params=params, json=data, timeout=self.timeout)

            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException:
            return None
        except ValueError:
            return None

        # Heuristic parsing:
        # 1) Look for product-like actions first (e.g., ProductVisualSearch or similar)
        name = self._parse_product_name(payload)
        if name:
            return name

        # 2) Fallback to ImageTags (displayName)
        return self._parse_tag_name(payload)

    # ----- helpers -----

    def _parse_product_name(self, payload) -> Optional[str]:
        # Typical structure: payload["tags"][i]["actions"][j]
        # Product actions often contain a 'data'->'value' list with 'name' (or 'displayName')
        try:
            tags = payload.get("tags", []) or []
            for tag in tags:
                actions = tag.get("actions", []) or []
                for act in actions:
                    action_type = act.get("actionType", "")
                    if "Product" in action_type or "Shopping" in action_type or "VisualSearch" in action_type:
                        data = act.get("data") or {}
                        values = data.get("value") or []
                        # Prefer the first plausible item with a name/brand-like field
                        for v in values:
                            # Common keys observed: 'name', 'displayName'
                            candidate = v.get("name") or v.get("displayName")
                            if candidate and isinstance(candidate, str) and len(candidate) <= 120:
                                return candidate
        except Exception:
            pass
        return None

    def _parse_tag_name(self, payload) -> Optional[str]:
        # Fallback: use non-product visual tags
        try:
            tags = payload.get("tags", []) or []
            # Usually the first tag has 'displayName' that's the best guess (e.g., "Nike Air Max 90")
            for tag in tags:
                dn = tag.get("displayName")
                if dn and isinstance(dn, str) and len(dn) <= 120:
                    return dn
                # Or actions → ImageTags
                actions = tag.get("actions", []) or []
                for act in actions:
                    if act.get("actionType") in ("ImageTags", "VisualSearch"):
                        data = act.get("data") or {}
                        values = data.get("value") or []
                        for v in values:
                            candidate = v.get("displayName")
                            if candidate and isinstance(candidate, str) and len(candidate) <= 120:
                                return candidate
        except Exception:
            pass
        return None
