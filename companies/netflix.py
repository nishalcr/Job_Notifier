from companies.eightfold import eightfold_company

COMPANY = eightfold_company(
    slug="netflix",
    display_name="Netflix",
    host="explore.jobs.netflix.net",
    domain="netflix.com",
    # Netflix levels: L4 mid, L5 senior, L6+ staff and above.
    extra_excluded_title_phrases=("l6", "l7", "l8", "engineer 6", "engineer 7", "engineer 8"),
)
