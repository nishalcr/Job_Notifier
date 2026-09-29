import re

from companies.workday import workday_company

# Cisco's Workday site has no country filter; the posting path starts with the
# primary location, e.g. "/job/San-Jose-California-US/...".
US_PATH_RE = re.compile(r"^/job/[^/]*-US/")


COMPANY = workday_company(
    slug="cisco",
    display_name="Cisco",
    host="cisco.wd5.myworkdayjobs.com",
    tenant="cisco",
    site="Cisco_Careers",
    applied_facets={
        # Engineering, Information Technology
        "jobFamilyGroup": [
            "2101eee3ea96016aef42a674fc016429",
            "2101eee3ea96017b1ceba674fc016829",
        ],
    },
    # Cisco's "Technical Leader" is above senior, and "Leader, ..." is a manager.
    extra_excluded_title_phrases=("leader",),
    posting_filter=lambda posting: bool(US_PATH_RE.match(posting.get("externalPath") or "")),
    default_max_pages=4,
)
