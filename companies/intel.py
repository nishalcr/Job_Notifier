from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="intel",
    display_name="Intel",
    host="intel.wd1.myworkdayjobs.com",
    tenant="intel",
    site="External",
    applied_facets={
    },
    # Intel's location filter lists individual sites, not countries.
    posting_filter=is_us_posting,
)
