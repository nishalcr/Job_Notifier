from companies.workday import workday_company

COMPANY = workday_company(
    slug="salesforce",
    display_name="Salesforce",
    host="salesforce.wd12.myworkdayjobs.com",
    tenant="salesforce",
    site="external_career_site",
    applied_facets={
        # Country: United States of America
        "CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended": [
            "bc33aa3152ec42d4995f4791a106ed09"
        ],
        # Full time
        "timeType": ["0e28126347c3100fe3b402cf26290000"],
        # Regular (not intern or contractor)
        "workerSubType": ["3a910852b2c31010f48d2bbc8b020000"],
    },
)
