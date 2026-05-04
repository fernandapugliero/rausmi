import requests
import json
import os
import re

AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
BASE_ID = os.environ.get("BASE_ID")
EVENTS_TABLE = os.environ.get("EVENTS_TABLE", "events")
VENUES_TABLE = os.environ.get("VENUES_TABLE", "Venues")
VIEW_NAME = os.environ.get("VIEW_NAME", "approved")

if not AIRTABLE_TOKEN:
    raise ValueError("AIRTABLE_TOKEN not found")
if not BASE_ID:
    raise ValueError("BASE_ID not found")

HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}


def normalize_key(key):
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def get_field(fields, *names):
    normalized = {normalize_key(k): v for k, v in fields.items()}
    for name in names:
        key = normalize_key(name)
        if key in normalized:
            return normalized[key]
    return None


def first_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def clean_text(value):
    value = first_value(value)
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalize_coord(value):
    value = first_value(value)
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    if isinstance(value, (int, float)):
        value = float(value)

        # Coordenada já normal: 52.49 ou 13.42
        if abs(value) < 1000:
            return value

        # Caso Airtable/lookup venha como número sem ponto:
        # 52492058930667896 -> 52.492058930667896
        s = str(int(value))
        if s.startswith("52") and len(s) > 2:
            return float(s[:2] + "." + s[2:])
        if s.startswith("13") and len(s) > 2:
            return float(s[:2] + "." + s[2:])

    return None


def normalize_week_of_month(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return str(value).strip()


def fetch_all(table_name, view_name=None):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
    records = []
    offset = None

    while True:
        params = {"pageSize": 100}
        if view_name:
            params["view"] = view_name
        if offset:
            params["offset"] = offset

        response = requests.get(url, headers=HEADERS, params=params)

        if not response.ok:
            raise Exception(
                f"Airtable error {response.status_code} on {table_name}: {response.text}"
            )

        data = response.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")

        if not offset:
            break

    return records


# 1) Carrega venues
venues_raw = fetch_all(VENUES_TABLE)
venue_map = {}

for record in venues_raw:
    fields = record.get("fields", {})

    venue_map[record["id"]] = {
        "venue_name": clean_text(get_field(fields, "name", "venue_name", "title")),
        "address": clean_text(get_field(fields, "address")),
        "district": clean_text(get_field(fields, "district")),
        "latitude": normalize_coord(get_field(fields, "lat", "latitude")),
        "longitude": normalize_coord(get_field(fields, "long", "longitude", "lng")),
    }


# 2) Carrega events
events_raw = fetch_all(EVENTS_TABLE, VIEW_NAME)
events = []

for record in events_raw:
    fields = record.get("fields", {})

    venue_ref = first_value(get_field(fields, "venue"))
    venue_data = venue_map.get(venue_ref, {}) if venue_ref else {}

    event = {
        "id": record.get("id"),
        "title": clean_text(get_field(fields, "title", "name", "event_title")),
        "description": clean_text(get_field(fields, "description")),
        "venue_name": venue_data.get("venue_name"),
        "address": venue_data.get("address"),
        "district": venue_data.get("district"),
        "latitude": venue_data.get("latitude"),
        "longitude": venue_data.get("longitude"),
        "photo": first_value(get_field(fields, "photo")),
        "day_of_week": clean_text(get_field(fields, "day_of_week")),
        "recurrence_type": clean_text(get_field(fields, "recurrence_type")),
        "week_of_month": normalize_week_of_month(get_field(fields, "week_of_month")),
        "event_date": clean_text(get_field(fields, "event_date", "date")),
        "start_time": clean_text(get_field(fields, "start_time")),
        "end_time": clean_text(get_field(fields, "end_time")),
        "age_min": first_value(get_field(fields, "age_min")),
        "age_max": first_value(get_field(fields, "age_max")),
        "age_label": clean_text(get_field(fields, "age_label")),
        "price_type": clean_text(get_field(fields, "price_type")),
        "price": clean_text(get_field(fields, "price")),
        "registration_required": clean_text(get_field(fields, "registration_required")),
        "source": clean_text(get_field(fields, "source")),
        "status": clean_text(get_field(fields, "status")),
        "verified_at": clean_text(get_field(fields, "verified_at")),
        "is_active": clean_text(get_field(fields, "is_active")),
    }

    # Só exporta eventos realmente utilizáveis
    if event["status"] != "approved":
        continue
    if event["is_active"] != "active":
        continue
    if not event["title"]:
        continue
    if not event["start_time"] or not event["end_time"]:
        continue
    if not event["venue_name"]:
        continue
    if event["latitude"] is None or event["longitude"] is None:
        continue

    events.append(event)


with open("data.json", "w", encoding="utf-8") as f:
    json.dump({"events": events}, f, ensure_ascii=False, indent=2)

print(f"Saved {len(events)} events to data.json")
