from src.config import get_settings
from src.county_resolver import CountyResolution, normalize_county, resolve_county


class FakeGeocoder:
    def resolve_county(self, address, city, state, zip_code):
        return CountyResolution(county="Houston", state="GA", method="address_geocode", confidence=95)


async def test_explicit_county_wins(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()

    resolution = await resolve_county(
        explicit_county="Houston County",
        address="204 Carroll Dr, Warner Robins, GA 31093",
        city="Warner Robins",
        state="Georgia",
        zip_code="31093",
    )

    assert resolution.county == "Houston"
    assert resolution.state == "GA"
    assert resolution.method == "provider"
    assert resolution.confidence == 100


async def test_zip_fallback_resolves_provider_address_when_geocoding_is_disabled(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()

    resolution = await resolve_county(
        explicit_county=None,
        address="204 Carroll Dr, Warner Robins, GA 31093",
        city="Warner Robins",
        state="Georgia",
        zip_code=None,
    )

    assert resolution.county == "Houston"
    assert resolution.state == "GA"
    assert resolution.method == "zip_crosswalk"
    assert resolution.confidence == 70


async def test_address_geocoder_can_resolve_county_before_zip_fallback(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()

    resolution = await resolve_county(
        explicit_county=None,
        address="204 Carroll Dr, Warner Robins, GA 31093",
        city="Warner Robins",
        state="Georgia",
        zip_code="31093",
        geocoder=FakeGeocoder(),
    )

    assert resolution.county == "Houston"
    assert resolution.method == "address_geocode"
    assert resolution.confidence == 95


def test_normalize_county_strips_county_suffix():
    assert normalize_county("gwinnett county") == "Gwinnett"
