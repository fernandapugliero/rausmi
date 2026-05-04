import requests
import os
import json

AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
BASE_ID = os.environ.get("BASE_ID")
TABLE_NAME = os.environ.get("TABLE_NAME")

url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

headers = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}"
}

events = []
offset = None

while True:
    params = {}
    if offset:
        params["offset"] = offset

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Airtable error {response.status_code}: {response.text}")

    data = response.json()

    for record in data["records"]:
        f = record["fields"]

        events.append({
            "id": record["id"],
            "title": f.get("title"),
            "venue_name": f.get("venue_name"),
            "address": f.get("address"),
            "district": f.get("district"),
            "latitude": f.get("latitude"),
            "longitude": f.get("longitude"),
            "day_of_week": f.get("day_of_week"),
            "recurrence_type": f.get("recurrence_type"),
            "week_of_month": f.get("week_of_month"),
            "event_date": f.get("event_date"),
            "start_time": f.get("start_time"),
            "end_time": f.get("end_time"),
            "age_min": f.get("age_min"),
            "age_max": f.get("age_max"),
            "age_label": f.get("age_label"),
            "price_type": f.get("price_type"),
            "price": f.get("price"),
            "registration_required": f.get("registration_required"),
            "status": f.get("status"),
            "is_active": f.get("is_active"),
        })

    offset = data.get("offset")
    if not offset:
        break

with open("data.json", "w") as f:
    json.dump({"events": events}, f, indent=2)
