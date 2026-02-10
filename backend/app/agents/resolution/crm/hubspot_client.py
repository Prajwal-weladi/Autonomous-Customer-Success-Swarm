import requests
import os
import dotenv
dotenv.load_dotenv()
HUBSPOT_TOKEN = os.getenv("HUBSPOT_TOKEN")
BASE_URL = "https://api.hubapi.com"

HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json"
}

def update_deal_stage(order_id: str, pipeline_id: str, stage_id: str):
    url = f"{BASE_URL}/crm/v3/objects/deals/{order_id}"

    payload = {
        "properties": {
            "pipeline": pipeline_id,
            "dealstage": stage_id
        }
    }

    response = requests.patch(url, json=payload, headers=HEADERS)
    response.raise_for_status()
