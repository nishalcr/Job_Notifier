from companies.greenhouse import greenhouse_company

COMPANY = greenhouse_company(
    slug="stripe",
    display_name="Stripe",
    board="stripe",
    # Locations are bare city names; offices are "US", "US-SF-HQ", "US-Remote", ...
    us_office=lambda name: name == "US" or name.startswith("US-"),
)
