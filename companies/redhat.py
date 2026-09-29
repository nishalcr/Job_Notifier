from companies.workday import workday_company

COMPANY = workday_company(
    slug="redhat",
    display_name="Red Hat",
    host="redhat.wd5.myworkdayjobs.com",
    tenant="redhat",
    site="jobs",
    applied_facets={
        # Red Hat's site uses short facet names: "a" = country, "d" = job function.
        "a": ["bc33aa3152ec42d4995f4791a106ed09"],  # United States of America
        "d": ["c18026e77576010f6ef6126f4e43ec4a"],  # Engineering
    },
)
