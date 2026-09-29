from companies.workday import workday_company

COMPANY = workday_company(
    slug="nvidia",
    display_name="NVIDIA",
    host="nvidia.wd5.myworkdayjobs.com",
    tenant="nvidia",
    site="NVIDIAExternalCareerSite",
    applied_facets={
        # Engineering, University Employment, IT
        "jobFamilyGroup": [
            "0c40f6bd1d8f10ae43ffaefd46dc7e78",
            "0c40f6bd1d8f10ae43ffda1e8d447e94",
            "0c40f6bd1d8f10ae43ffbd1459047e84",
        ],
        # United States
        "locationHierarchy1": ["2fcb99c455831013ea52fb338f2932d8"],
    },
    # NVIDIA posts dozens of roles a day.
    default_max_pages=5,
    default_full_scrape_max_pages=60,
)
