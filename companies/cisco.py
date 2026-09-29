from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="cisco",
    display_name="Cisco",
    host="cisco.wd5.myworkdayjobs.com",
    tenant="cisco",
    site="Cisco_Careers",
    applied_facets={
        # Engineering, Information Technology
        "jobFamilyGroup": [
            "2101eee3ea96016aef42a674fc016429",
            "2101eee3ea96017b1ceba674fc016829",
        ],
    },
    # Cisco's "Technical Leader" is above senior, and "Leader, ..." is a manager.
    extra_excluded_title_phrases=("leader",),
    # No country filter on Cisco's site.
    posting_filter=is_us_posting,
    default_max_pages=4,
)
