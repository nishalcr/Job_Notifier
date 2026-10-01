from companies.workday import workday_company

COMPANY = workday_company(
    slug="yahoo",
    display_name="Yahoo",
    host="ouryahoo.wd5.myworkdayjobs.com",
    tenant="ouryahoo",
    site="careers",
    applied_facets={
        # United States of America
        "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
)
