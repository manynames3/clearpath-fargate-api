import hmac

from fastapi import Header, HTTPException, status

from src.config import fetch_secret_string, get_settings


async def require_leads_api_key(x_clearpath_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.clearpath_api_key_secret:
        return

    expected = fetch_secret_string(settings.clearpath_api_key_secret, settings.aws_region)
    if x_clearpath_api_key and hmac.compare_digest(expected, x_clearpath_api_key):
        return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
