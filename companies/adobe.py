from companies.workday import workday_company

COMPANY = workday_company(
    slug="adobe",
    display_name="Adobe",
    host="adobe.wd5.myworkdayjobs.com",
    tenant="adobe",
    site="external_experienced",
    applied_facets={
        # United States of America
        "locationCountry": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
    # Adobe lists featured jobs first rather than newest first, so read every page.
    default_max_pages=20,
)
