"""Shared title filters: software-type IC roles from new grad through senior.

All terms match whole words, case-insensitively (see state.passes_title_filters).
"""

# A title must contain at least one of these to be kept.
ENGINEERING_TITLE_KEYWORDS = (
    "engineer",
    "engineering",
    "developer",
    "programmer",
    "sde",
    "sdet",
    "swe",
    "sre",
    "devops",
    "machine learning",
    "ml",
    "applied scientist",
    "mts",
    "amts",
    "smts",
    "lmts",
    "pmts",
)

# Levels above senior. Dropped unless the title also names a target level
# (multi-level postings like "Senior / Lead / Principal Software Engineer").
ABOVE_SENIOR_LEVEL_KEYWORDS = (
    "staff",
    "principal",
    "distinguished",
    "fellow",
    "lmts",
    "pmts",
)

# Levels that are in range: new grad through senior.
TARGET_LEVEL_KEYWORDS = (
    "senior",
    "sr",
    "junior",
    "jr",
    "new grad",
    "graduate",
    "college grad",
    "entry level",
    "early career",
    "associate",
    "analyst",
    "i",
    "ii",
    "iii",
    "mts",
    "amts",
    "smts",
)

# People managers, architects, and internships. Any match drops the title.
NON_IC_TITLE_PHRASES = (
    "manager",
    "director",
    "head of",
    "architect",
    "intern",
    "internship",
    "co-op",
)

# Executive titles. Kept separate because Goldman Sachs uses "Vice President"
# as a senior IC level.
EXECUTIVE_TITLE_PHRASES = (
    "vice president",
    "vp",
)

# Engineering titles that are not software roles. Any match drops the title.
NON_SOFTWARE_TITLE_PHRASES = (
    "sales engineer",
    "solutions engineer",
    "customer engineer",
    "field engineer",
    "field application",
    "data scientist",
    "support engineer",
    "content engineer",
    "hardware engineer",
    "hardware reliability",
    "production quality",
    "data center",
    "electrical",
    "mechanical",
    "thermal",
    "manufacturing",
    "industrial",
    "controls engineer",
    "controls system",
    "antenna",
    "broadcast",
    "logistics",
    "fleet",
    "facilities",
    "construction",
    "civil",
    "chemical",
    "optical",
    "analog",
    "asic",
    "silicon",
    "packaging",
    "specialist",
)

DEFAULT_EXCLUDED_TITLE_PHRASES = NON_IC_TITLE_PHRASES + EXECUTIVE_TITLE_PHRASES + NON_SOFTWARE_TITLE_PHRASES
