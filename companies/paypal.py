from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="paypal",
    display_name="PayPal",
    host="paypal.wd1.myworkdayjobs.com",
    tenant="paypal",
    site="jobs",
    applied_facets={
        # Technology Job Family Group
        "jobFamilyGroup": ["b00c2f6141401001c5f81018e4210000"],
    },
    # PayPal's location filter lists individual cities, not countries.
    posting_filter=is_us_posting,
)
