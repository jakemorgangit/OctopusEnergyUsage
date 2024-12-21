# OctopusEnergyUsage
A python application to show live energy usage (UK only)

![image](https://github.com/user-attachments/assets/31839a6c-28fa-48a9-a633-e8ba9eccc96e)

# Requirements

**Hardware:**

This application requires an Octopus Home Mini device

![image](https://github.com/user-attachments/assets/7864b43c-7703-4804-a6f6-127e4bcc0b92)

which needs to be added to your devices via the Octopus app.
https://octopus.energy/blog/octopus-home-mini/

If you don't have an Octopus Home Mini, you can request one using this link:
https://octopus.typeform.com/to/B5ifg5rQ

# Setup

**Step 1: Obtain Your Credentials**
You will need to update the `.env` file with your personal Octopus Energy details:

```
OCTOPUS_API_KEY=[YOUR_API_KEY]
OCTOPUS_ACCOUNT_NUMBER=[OCTOPUS_ACCOUNT_NUMBER]
OCTOPUS_MPAN=[OCTOPUS_MPAN]
OCTOPUS_METER_SERIAL=[OCTOPUS_METER_SERIAL]
OCTOPUS_PRODUCT_CODE=[OCTOPUS_PRODUCT_CODE]
OCTOPUS_TARIFF_CODE=[OCTOPUS_TARIFF_CODE]
```


Most details can be retrieved from the Octopus Energy API access page: https://octopus.energy/dashboard/new/accounts/personal-details/api-access

![image](https://github.com/user-attachments/assets/6fe2eb10-cc9e-4512-a321-bf05523c539d)

The product and tariff codes can be obtained from the unit rates API:

![image](https://github.com/user-attachments/assets/4ce50eea-ba3e-4a6c-b56f-4b067bfa0f5b)

 ```
curl -u "OCTOPUS_API_KEY:" \
"https://api.octopus.energy/v1/products/AGILE-FLEX-22-11-25/electricity-tariffs/E-1R-AGILE-FLEX-22-11-25-D/standard-unit-rates/"

```
In the example above:

`AGILE-FLEX-22-11-25` is the product code.
`E-1R-AGILE-FLEX-22-11-25-D` is the tariff code.
Make sure to replace these with your specific product and tariff codes.

**Step 2: Install Prerequisites**

Install the required Python libraries:

`pip install python-dotenv python-dateutil`


**Step 3: Run the Application**

Execute the script:

`python .\octopusUsageGUI.py`


This will launch a Tkinter GUI that displays:

Current usage (updated every 10 seconds via the GraphQL API).
Electricity costs and rates (updated every 30 minutes via REST).

# Features
Real-Time Usage Tracking
Color-coded current KWh usage:

    Color code based on usage in kW:
      - Green if < 1.0
      - Yellow if [1.0, 1.3)
      - Orange if [1.3, 1.5)
      - Red if >= 1.5

These can be tweaked based on your preferences

# Notes

**API Rate Limits**

Octopus imposes rate limits on their API. If you encounter the following error:

![image](https://github.com/user-attachments/assets/f95b0aae-a2c4-4544-95d8-d4d20d2621c1)

Reduce the polling frequency in the script (e.g., line 248):

```
# Schedule next update in 10 seconds
root.after(10_000, update_data)
```

Lowering the polling frequency can help you stay within the rate limits.
