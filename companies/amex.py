from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="amex",
    display_name="American Express",
    host="egug.fa.us2.oraclecloud.com",
    site_number="CX_1",
    # United States
    location_id="300000000229164",
    # Technology, Data Mgmt and Analytics
    category_ids=("300000081299474", "300000573321731"),
)
