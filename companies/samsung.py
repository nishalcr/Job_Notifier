from companies.workday import workday_company

COMPANY = workday_company(
    slug="samsung",
    display_name="Samsung",
    host="sec.wd3.myworkdayjobs.com",
    tenant="sec",
    site="Samsung_Careers",
    applied_facets={
        # R&D, Software R&D
        "jobFamilyGroup": [
            "189767dd6c9201b4198fe1a6db2997c7",
            "189767dd6c9201e189e3eaa6db299dc7",
        ],
        # United States of America
        "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
)
