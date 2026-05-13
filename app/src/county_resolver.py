from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from src.config import get_settings


STATE_ABBREVIATIONS = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

STATE_FIPS_TO_ABBR = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}

ZIP_COUNTY_FALLBACK = {
    ("GA", "30043"): "Gwinnett",
    ("GA", "30046"): "Gwinnett",
    ("GA", "30071"): "Gwinnett",
    ("GA", "30093"): "Gwinnett",
    ("GA", "30060"): "Cobb",
    ("GA", "30064"): "Cobb",
    ("GA", "30310"): "Fulton",
    ("GA", "31088"): "Houston",
    ("GA", "31093"): "Houston",
}

SPECIAL_COUNTY_NAMES = {
    "dekalb": "DeKalb",
    "mcduffie": "McDuffie",
    "mcdonough": "McDonough",
}


@dataclass(frozen=True)
class CountyResolution:
    county: str | None
    state: str | None
    method: str
    confidence: int


class CountyGeocoder(Protocol):
    def resolve_county(self, address: str, city: str | None, state: str | None, zip_code: str | None) -> CountyResolution | None:
        ...


def normalize_state(value: str | None) -> str:
    state = (value or "GA").strip()
    if len(state) == 2:
        return state.upper()
    return STATE_ABBREVIATIONS.get(state.lower(), state[:2].upper())


def normalize_county(value: str | None) -> str | None:
    if not value:
        return None
    county = re.sub(r"\s+", " ", value.strip())
    county = re.sub(r"\s+county$", "", county, flags=re.IGNORECASE).strip()
    if not county:
        return None
    return SPECIAL_COUNTY_NAMES.get(county.lower(), county.title())


def normalize_zip(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", value)
    return match.group(1) if match else None


def _build_address(address: str, city: str | None, state: str | None, zip_code: str | None) -> str:
    normalized = address.strip()
    lower = normalized.lower()
    parts = [normalized]
    if city and city.lower() not in lower:
        parts.append(city)
    if state and normalize_state(state).lower() not in lower:
        parts.append(normalize_state(state))
    if zip_code and zip_code not in normalized:
        parts.append(zip_code)
    return ", ".join(parts)


class CensusCountyGeocoder:
    endpoint = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"

    def __init__(self, timeout_seconds: float = 2.0):
        self.timeout_seconds = timeout_seconds

    def resolve_county(self, address: str, city: str | None, state: str | None, zip_code: str | None) -> CountyResolution | None:
        query_address = _build_address(address, city, state, zip_code)
        params = urllib.parse.urlencode(
            {
                "address": query_address,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "layers": "all",
                "format": "json",
            }
        )
        request = urllib.request.Request(f"{self.endpoint}?{params}", headers={"User-Agent": "clearpath-api/0.1"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        matches = payload.get("result", {}).get("addressMatches", [])
        if not matches:
            return None

        counties = matches[0].get("geographies", {}).get("Counties", [])
        if not counties:
            return None

        county_data = counties[0]
        county = normalize_county(county_data.get("BASENAME") or county_data.get("NAME"))
        resolved_state = STATE_FIPS_TO_ABBR.get(str(county_data.get("STATE", "")).zfill(2), normalize_state(state))
        if not county:
            return None
        return CountyResolution(county=county, state=resolved_state, method="address_geocode", confidence=95)


async def resolve_county(
    *,
    explicit_county: str | None,
    address: str | None,
    city: str | None,
    state: str | None,
    zip_code: str | None,
    geocoder: CountyGeocoder | None = None,
) -> CountyResolution:
    normalized_state = normalize_state(state)
    normalized_county = normalize_county(explicit_county)
    if normalized_county:
        return CountyResolution(county=normalized_county, state=normalized_state, method="provider", confidence=100)

    settings = get_settings()
    normalized_zip = normalize_zip(zip_code or address)
    use_geocoder = (
        settings.county_geocoding_enabled
        and settings.environment.lower() != "test"
        and bool(address)
    )

    if use_geocoder or geocoder is not None:
        county_geocoder = geocoder or CensusCountyGeocoder(settings.county_geocoding_timeout_seconds)
        try:
            geocoded = await asyncio.to_thread(
                county_geocoder.resolve_county,
                address or "",
                city,
                normalized_state,
                normalized_zip,
            )
        except Exception:
            geocoded = None
        if geocoded and geocoded.county:
            return geocoded

    fallback_county = ZIP_COUNTY_FALLBACK.get((normalized_state, normalized_zip or ""))
    if fallback_county:
        return CountyResolution(county=fallback_county, state=normalized_state, method="zip_crosswalk", confidence=70)

    return CountyResolution(county=None, state=normalized_state, method="unresolved", confidence=0)
