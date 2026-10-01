from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="cisco",
    display_name="Cisco",
    host="cisco.wd5.myworkdayjobs.com",
    tenant="cisco",
    site="Cisco_Careers",
    applied_facets={
    },
    # No country filter on Cisco's site.
    posting_filter=is_us_posting,
    default_max_pages=5,
)
