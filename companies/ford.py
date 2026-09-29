from companies.oracle_hcm import oracle_hcm_company

COMPANY = oracle_hcm_company(
    slug="ford",
    display_name="Ford",
    host="efds.fa.em5.oraclecloud.com",
    site_number="CX_1",
    # United States
    location_id="300000000425727",
    # Enterprise Technology, Global Data Insight & Analytics, Research and Advance Engineering
    category_ids=("300002487990164", "300002487961196", "300002487925832"),
)
