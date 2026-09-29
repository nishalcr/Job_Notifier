from companies.workday import workday_company

COMPANY = workday_company(
    slug="yahoo",
    display_name="Yahoo",
    host="ouryahoo.wd5.myworkdayjobs.com",
    tenant="ouryahoo",
    site="careers",
    applied_facets={
        # Software Development, Engineering, Information Systems
        "jobFamilyGroup": [
            "91f14896cbbe0150163e1d3fc7463fb2",
            "91f14896cbbe0172a9e4f13ec7462fb2",
            "91f14896cbbe014ea5db023fc74635b2",
        ],
        # United States of America
        "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
)
