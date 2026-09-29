from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="dell",
    display_name="Dell",
    host="enterpriseplatform.dell.com",
    site_number="CX_1001",
    # United States
    location_id="300000000471434",
    # Software Engineering, Systems Development Engineering
    category_ids=("300000036340556", "300000036264054"),
)
