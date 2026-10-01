from companies.workday import workday_company

COMPANY = workday_company(
    slug="nvidia",
    display_name="NVIDIA",
    host="nvidia.wd5.myworkdayjobs.com",
    tenant="nvidia",
    site="NVIDIAExternalCareerSite",
    applied_facets={
        # United States
        "locationHierarchy1": ["2fcb99c455831013ea52fb338f2932d8"],
    },
    # NVIDIA posts dozens of roles a day.
    default_max_pages=6,
    default_full_scrape_max_pages=60,
)
