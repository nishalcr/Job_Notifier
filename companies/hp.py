from companies.workday import workday_company

COMPANY = workday_company(
    slug="hp",
    display_name="HP",
    host="hp.wd5.myworkdayjobs.com",
    tenant="hp",
    site="ExternalCareerSite",
    applied_facets={
        # Software, Engineering, Data & Information Technology
        "jobFamilyGroup": [
            "80667f5f2da3010ee8417a74cf4b0000",
            "98cbd30d374e10333e00271ec8445e81",
            "98cbd30d374e10333e000e782ca45e69",
        ],
        # United States of America
        "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
    },
)
