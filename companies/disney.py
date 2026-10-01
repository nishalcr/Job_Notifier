from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="disney",
    display_name="Disney",
    host="disney.wd5.myworkdayjobs.com",
    tenant="disney",
    site="disneycareer",
    applied_facets={
    },
    # No country filter on Disney's site.
    posting_filter=is_us_posting,
)
