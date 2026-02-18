import logging
import httpx

class GeoService:
    """
    Async Geolocation service using httpx (async HTTP client).
    Determines user timezone from their IP address.
    """

    DEFAULT_TIMEZONE = "Asia/Karachi"

    async def get_region_from_ip(self, ip_address: str) -> str:
        """
        Async version of IP-to-timezone lookup using ipwhois.app.
        Falls back to default timezone for local/private IPs.
        """
        try:
            # Handle localhost or private IPs
            private_prefixes = ("127.", "192.168.", "10.", "172.16.", "::1", "0.0.0.0")
            if any(ip_address.startswith(p) for p in private_prefixes):
                logging.warning(f"Local/private IP {ip_address}, using default timezone.")
                return self.DEFAULT_TIMEZONE

            url = f"https://ipwhois.app/json/{ip_address}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()

            data = response.json()
            timezone = data.get("timezone")

            if not timezone:
                logging.warning(f"No timezone found for {ip_address}")
                return self.DEFAULT_TIMEZONE

            logging.info(f"🌍 Timezone for IP {ip_address}: {timezone}")
            return timezone

        except httpx.HTTPError as e:
            logging.error(f"HTTP error fetching region for IP {ip_address}: {e}")
            return self.DEFAULT_TIMEZONE
        except Exception as e:
            logging.error(f"Unexpected error in GeoService for IP {ip_address}: {e}")
            return self.DEFAULT_TIMEZONE
