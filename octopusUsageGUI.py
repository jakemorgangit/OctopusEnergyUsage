import os
import requests
import tkinter as tk
from datetime import datetime, timezone
import dateutil.parser  # pip install python-dateutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ------------------------------------------------------------------------
# CONFIG: read from environment variables
# ------------------------------------------------------------------------
API_KEY = os.getenv("OCTOPUS_API_KEY")
ACCOUNT_NUMBER = os.getenv("OCTOPUS_ACCOUNT_NUMBER")
MPAN = os.getenv("OCTOPUS_MPAN")
METER_SERIAL = os.getenv("OCTOPUS_METER_SERIAL")
PRODUCT_CODE = os.getenv("OCTOPUS_PRODUCT_CODE")
TARIFF_CODE  = os.getenv("OCTOPUS_TARIFF_CODE")

# Validate that we have all the required environment variables
required_env_vars = [
    ("OCTOPUS_API_KEY", API_KEY),
    ("OCTOPUS_ACCOUNT_NUMBER", ACCOUNT_NUMBER),
    ("OCTOPUS_MPAN", MPAN),
    ("OCTOPUS_METER_SERIAL", METER_SERIAL),
    ("OCTOPUS_PRODUCT_CODE", PRODUCT_CODE),
    ("OCTOPUS_TARIFF_CODE", TARIFF_CODE),
]
missing_vars = [name for name, value in required_env_vars if not value]
if missing_vars:
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

# GraphQL endpoint
GRAPHQL_URL = "https://api.octopus.energy/v1/graphql/"

# ------------------------------------------------------------------------
# 1. AUTHENTICATION (GraphQL)
# ------------------------------------------------------------------------
def get_octopus_token(api_key):
    """
    Obtain a Kraken token using the Octopus GraphQL endpoint.
    """
    mutation = f"""
    mutation {{
      obtainKrakenToken(input: {{APIKey: "{api_key}"}}) {{
        token
      }}
    }}
    """
    headers = {'Content-Type': 'application/json'}
    response = requests.post(GRAPHQL_URL, json={'query': mutation}, headers=headers)
    response.raise_for_status()
    return response.json()['data']['obtainKrakenToken']['token']

# ------------------------------------------------------------------------
# 2. GET DEVICE ID (GraphQL)
# ------------------------------------------------------------------------
def get_device_id(token, account_number):
    """
    Fetch the smart device ID from the account using GraphQL.
    """
    query_device_id = f"""
    query {{
      account(accountNumber: "{account_number}") {{
        electricityAgreements {{
          meterPoint {{
            meters {{
              smartDevices {{
                deviceId
              }}
            }}
          }}
        }}
      }}
    }}
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'JWT {token}'
    }
    response = requests.post(GRAPHQL_URL, json={'query': query_device_id}, headers=headers)
    response.raise_for_status()

    data = response.json()['data']['account']['electricityAgreements']
    if not data:
        raise ValueError("No electricityAgreements found for this account.")
    
    device_id = data[0]['meterPoint']['meters'][0]['smartDevices'][0]['deviceId']
    return device_id

# ------------------------------------------------------------------------
# 3. GET SMART METER TELEMETRY (GraphQL)
# ------------------------------------------------------------------------
def get_smart_meter_telemetry(token, device_id):
    """
    Fetch live smart meter telemetry (demand in W, consumption in Wh, etc.) via GraphQL.
    We'll use 'demand' in watts for instantaneous usage.
    """
    query_telemetry = f"""
    query {{
      smartMeterTelemetry(deviceId: "{device_id}") {{
        readAt
        demand
        consumption
      }}
    }}
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'JWT {token}'
    }
    response = requests.post(GRAPHQL_URL, json={'query': query_telemetry}, headers=headers)
    response.raise_for_status()
    return response.json()['data']['smartMeterTelemetry']

# ------------------------------------------------------------------------
# 4. GET CURRENT PRICE (REST)
# ------------------------------------------------------------------------
def get_current_price_rest(api_key, product_code, tariff_code):
    """
    Use the Octopus REST API to fetch the current standard-unit-rate for your tariff.
    We'll parse the returned array, find which segment is valid 'now', and return the rate (p/kWh).
    """
    url = (
        f"https://api.octopus.energy/v1/products/{product_code}/"
        f"electricity-tariffs/{tariff_code}/standard-unit-rates/"
    )
    resp = requests.get(url, auth=(api_key, ""))  # Basic Auth
    resp.raise_for_status()

    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None
    
    now_utc = datetime.now(timezone.utc)
    
    for item in results:
        valid_from = dateutil.parser.isoparse(item["valid_from"])
        valid_to   = dateutil.parser.isoparse(item["valid_to"])
        if valid_from <= now_utc < valid_to:
            # Return the "value_inc_vat" in pence/kWh
            return {
                "rate": float(item["value_inc_vat"]),  # p/kWh
                "valid_from": valid_from,
                "valid_to": valid_to
            }
    
    return None

# ------------------------------------------------------------------------
# 5. COLOR CODING
# ------------------------------------------------------------------------
def color_for_usage(kwh):
    """
    Color code based on usage in kW:
      - Green if < 1.0
      - Yellow if [1.0, 1.3)
      - Orange if [1.3, 1.5)
      - Red if >= 1.5
    """
    if kwh < 1.0:
        return 'green'
    elif 1.0 <= kwh < 1.3:
        return 'yellow'
    elif 1.3 <= kwh < 1.5:
        return 'orange'
    else:
        return 'red'

# ------------------------------------------------------------------------
# 6. UPDATE GUI (every 10 seconds)
# ------------------------------------------------------------------------
def update_data():
    """
    1. Fetch the latest instantaneous usage from GraphQL (demand in W).
    2. Convert to kW.
    3. Fetch the current price from REST (p/kWh).
    4. Calculate cost per hour at that usage level.
    5. Display everything in tkinter labels, color-coded usage.
    6. Schedule next update in 10 seconds.
    """
    global token
    
    # 1. GraphQL telemetry
    try:
        telemetry_data = get_smart_meter_telemetry(token, device_id)
    except Exception as e:
        usage_label.config(text=f"GraphQL Error:\n{e}", fg="red")
        cost_label.config(text="")
        price_label.config(text="")
        time_label.config(text="")
        root.after(10_000, update_data)  # 10 seconds
        return
    
    if not telemetry_data:
        usage_label.config(text="No Telemetry Returned", fg="red")
        cost_label.config(text="")
        price_label.config(text="")
        time_label.config(text="")
        root.after(10_000, update_data)
        return
    
    latest = telemetry_data[0]
    read_at_str = latest['readAt']
    
    # 'demand' might be string, so convert
    demand_w_str = latest['demand']
    demand_w = float(demand_w_str)
    demand_kw = demand_w / 1000.0
    
    # 2. REST price
    try:
        price_data = get_current_price_rest(API_KEY, PRODUCT_CODE, TARIFF_CODE)
    except Exception as e:
        price_data = None
    
    if not price_data:
        current_price_p = 0.0
        valid_str = "N/A"
    else:
        current_price_p = price_data["rate"]  # pence/kWh
        valid_from = price_data["valid_from"]
        valid_to   = price_data["valid_to"]
        valid_str  = (
            f"{valid_from.strftime('%H:%M')} - "
            f"{valid_to.strftime('%H:%M')} (UTC)"
        )
    
    # pence -> pounds
    current_price_gbp_per_kwh = current_price_p / 100.0
    
    # 3. cost per hour
    cost_per_hour = demand_kw * current_price_gbp_per_kwh
    
    # 4. Update labels
    usage_color = color_for_usage(demand_kw)
    usage_label.config(text=f"{demand_kw:.2f} kW", fg=usage_color, bg="black")
    cost_label.config(text=f"£{cost_per_hour:.4f}/hour", fg='white', bg='black')
    price_label.config(
        text=f"Price: £{current_price_gbp_per_kwh:.4f}/kWh\n(valid {valid_str})",
        fg='white', bg='black'
    )
    time_label.config(text=f"Last Reading: {read_at_str}", fg='grey', bg='black')
    
    # 5. Schedule next update in 10 seconds
    root.after(10_000, update_data)

# ------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------
if __name__ == '__main__':
    # 1. Get JWT token
    token = get_octopus_token(API_KEY)

    # 2. Get device ID
    device_id = get_device_id(token, ACCOUNT_NUMBER)

    # 3. Build tkinter GUI (dark mode)
    root = tk.Tk()
    root.title("Octopus Energy Usage")
    root.configure(bg="black")

    usage_label = tk.Label(root, text="-- kW", font=("Arial", 36), fg='white', bg='black')
    usage_label.pack(pady=10)

    cost_label = tk.Label(root, text="-- £/hour", font=("Arial", 24), fg='white', bg='black')
    cost_label.pack(pady=2)

    price_label = tk.Label(root, text="-- Price info --", font=("Arial", 14), fg='white', bg='black')
    price_label.pack(pady=2)

    time_label = tk.Label(root, text="-- Last Reading --", font=("Arial", 12), fg='grey', bg='black')
    time_label.pack(pady=2)

    # 4. Start updating
    update_data()

    # 5. Main loop
    root.mainloop()
