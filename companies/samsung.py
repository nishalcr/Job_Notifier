from companies.workday import workday_company

COMPANY = workday_company(
    slug="samsung",
    display_name="Samsung",
    host="sec.wd3.myworkdayjobs.com",
    tenant="sec",
    site="Samsung_Careers",
    applied_facets={
        # United States of America
        "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
)
