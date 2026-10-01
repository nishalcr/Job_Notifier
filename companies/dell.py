from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="dell",
    display_name="Dell",
    host="enterpriseplatform.dell.com",
    site_number="CX_1001",
    # United States
    location_id="300000000471434",
    category_ids=(),
)
