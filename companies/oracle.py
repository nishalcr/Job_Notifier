from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="oracle",
    display_name="Oracle",
    host="eeho.fa.us2.oraclecloud.com",
    site_number="CX_45001",
    # United States
    location_id="300000000149325",
    category_ids=(),
    # Oracle posts many jobs a day (~2,000 open in the US).
    default_max_pages=4,
    default_full_scrape_max_pages=90,
)
