from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="jpmc",
    display_name="JPMorgan Chase",
    host="jpmc.fa.oraclecloud.com",
    site_number="CX_1001",
    # United States
    location_id="300000000289738",
    # Software Engineering, Infrastructure Engineering, Predictive Science
    category_ids=("300000086152753", "300000086249821", "300000086152508"),
    default_max_pages=3,
)
