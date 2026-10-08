from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="paloalto",
    display_name="Palo Alto Networks",
    host="paloaltonetworks.wd5.myworkdayjobs.com",
    tenant="paloaltonetworks",
    site="panwexternalcareers",
    applied_facets={
    },
    # Palo Alto's location filter lists individual cities, not countries.
    posting_filter=is_us_posting,
    default_max_pages=4,
)
