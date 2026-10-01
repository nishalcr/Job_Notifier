from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="capitalone",
    display_name="Capital One",
    host="capitalone.wd12.myworkdayjobs.com",
    tenant="capitalone",
    site="Capital_One",
    applied_facets={
        # Software-Engineering, AI & ML Engineering and Sciences, Data-Engineering,
    },
    # No country filter; paths look like "/job/McLean-VA/...".
    posting_filter=is_us_posting,
    default_max_pages=5,
)
