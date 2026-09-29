from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="capitalone",
    display_name="Capital One",
    host="capitalone.wd12.myworkdayjobs.com",
    tenant="capitalone",
    site="Capital_One",
    applied_facets={
        # Software-Engineering, AI & ML Engineering and Sciences, Data-Engineering,
        # Infrastructure Engineering, Cyber
        "jobFamilyGroup": [
            "23c40d87cd84100035bd7d9296540000",
            "797094e02d441000c3f4fece96e10000",
            "23c40d87cd84100035bd9201b2bf0000",
            "c456977f3e611000c3e1be4b227f0000",
            "a3ffb53edaa61000c3f5dc76643a0000",
        ],
    },
    # No country filter; paths look like "/job/McLean-VA/...".
    posting_filter=is_us_posting,
    default_max_pages=4,
)
