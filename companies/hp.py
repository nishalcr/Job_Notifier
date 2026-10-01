from companies.workday import workday_company

COMPANY = workday_company(
    slug="hp",
    display_name="HP",
    host="hp.wd5.myworkdayjobs.com",
    tenant="hp",
    site="ExternalCareerSite",
    applied_facets={
        # United States of America
        "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
)
