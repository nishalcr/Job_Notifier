from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="jpmc",
    display_name="JPMorgan Chase",
    host="jpmc.fa.oraclecloud.com",
    site_number="CX_1001",
    # United States
    location_id="300000000289738",
    category_ids=(),
    default_max_pages=4,
)
