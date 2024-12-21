# OctopusEnergyUsage
A python application to show live energy usage (UK only)

![image](https://github.com/user-attachments/assets/31839a6c-28fa-48a9-a633-e8ba9eccc96e)

# This aplication requires an Octopus Home Mini device which will need to be added to your devices from the Octopus app.
https://octopus.energy/blog/octopus-home-mini/

If you don't have one, you can request one using this link:
https://octopus.typeform.com/to/B5ifg5rQ


# Prereqs:
pip install python-dotenv python-dateutil



# Run the python script:   python .\octopusUsageGUI.py

A tkinter GUI will launch showing your current usage (polled every 10 seconds via GraphQL API) and the electricity cost and rates (via REST - 30 minute refresh interval).

The current KWH usage is colour coded:

    Color code based on usage in kW:
      - Green if < 1.0
      - Yellow if [1.0, 1.3)
      - Orange if [1.3, 1.5)
      - Red if >= 1.5

These can be tweaked based on your preferences
