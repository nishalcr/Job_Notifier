from companies.workday import is_us_posting, workday_company

COMPANY = workday_company(
    slug="disney",
    display_name="Disney",
    host="disney.wd5.myworkdayjobs.com",
    tenant="disney",
    site="disneycareer",
    applied_facets={
        # Technology, Data Science and Analytics, Gaming and Interactive
        "jobFamilyGroup": [
            "4f84d9e8a097010115f104197eec0000",
            "4f84d9e8a097010115f146ed994a0000",
            "4f84d9e8a097010115f0c30fe69e0000",
        ],
    },
    # No country filter on Disney's site.
    posting_filter=is_us_posting,
)
