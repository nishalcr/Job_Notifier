from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="intel",
    display_name="Intel",
    host="intel.wd1.myworkdayjobs.com",
    tenant="intel",
    site="External",
    applied_facets={
        # Software Engineering, Information Technology, Data UX and Ecosystem Sciences
        "jobFamilyGroup": [
            "ace7a3d23b7e01a0544279031a0ec85c",
            "dc8bf79476611087d67b2cccdde47034",
            "a55ea4dd831d1000c6fce5a0c4d30000",
        ],
    },
    # Intel's location filter lists individual sites, not countries.
    posting_filter=is_us_posting,
)
