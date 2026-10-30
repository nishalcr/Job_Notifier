from dataclasses import replace

from companies.workday import workday_company

COMPANY = replace(
    workday_company(
        slug="cvs_wd",
        display_name="CVS Health (Workday)",
        host="cvshealth.wd1.myworkdayjobs.com",
        tenant="cvshealth",
        site="CVS_Health_Careers",
        applied_facets={
            # Job family group: Technology
            "jobFamilyGroup": ["e65dbadf6a50100168ed86fe4cf50001"],
        },
    ),
    # jobs.cvshealth.com (the "cvs" adapter) lists the same requisitions.
    shares_jobs_with=("cvs",),
)
