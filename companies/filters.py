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
    "mts",
    "amts",
    "smts",
)

# People managers, architects, and internships. Any match drops the title.
NON_IC_TITLE_PHRASES = (
    "manager",
    "mgr",
    "director",
    "head of",
    "leader",
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

# Engineering-sounding roles that are not software engineering. Any match drops the title.
NON_SOFTWARE_ROLE_PHRASES = (
    "sales engineer",
    "solutions engineer",
    "solution engineer",
    "solution engineering",
    "technical solutions",
    "implementation engineer",
    "partner engineer",
    "developer advocate",
    "gtm",
    "marketing engineer",
    "enablement",
    "customer engineer",
    "field engineer",
    "field application",
    "support engineer",
    "content engineer",
    "data scientist",
    "consultant",
    "specialist",
    "technician",
    "sourcer",
    "recruiter",
    "technologist",
    "contractor",
)

# Hardware, fab and physical-engineering domains. A match drops the title unless
# it also names software work (SOFTWARE_TITLE_KEYWORDS), so
# "Software Engineer, Hardware Platforms" is kept but "Hardware Engineer" is not.
HARDWARE_DOMAIN_PHRASES = (
    "hardware",
    "electrical",
    "mechanical",
    "thermal",
    "manufacturing",
    "industrial",
    "controls",
    "antenna",
    "broadcast",
    "rf",
    "power engineer",
    "serdes",
    "rtl",
    "asic",
    "silicon",
    "analog",
    "optical",
    "emulation",
    "verification",
    "testability",
    "mixed signal",
    "power and performance",
    "reliability engineer",
    "reliability test",
    "validation",
    "quality & reliability",
    "production quality",
    "regulation",
    "human factors",
    "product design",
    "interactive design",
    "packaging",
    "package design",
    "pcb",
    "layout engineer",
    "assembly",
    "flight test",
    "writing systems",
    "process engineer",
    "process integration",
    "module integration",
    "device integration",
    "equipment",
    "yield",
    "metrology",
    "defect",
    "material",
    "cvd",
    "cmp",
    "etch",
    "implant",
    "diffusion",
    "anneal",
    "amhs",
    "dfm",
    "data center",
    "logistics",
    "fleet",
    "facilities",
    "construction",
    "civil",
    "chemical",
    "physical security",
    # Automotive
    "cae",
    "mechatronics",
    "propulsion",
    "powertrain",
    "driveline",
    "emissions",
    "aftertreatment",
    "subsystem",
    "occupant safety",
    "body exteriors",
    "battery",
    "electronics",
    # Chip design and test
    "design engineer",
    "architecture engineer",
    "product development engineer",
    "applications engineer",
    "cad",
    "signal integrity",
    "dft",
    "atpg",
    "fpga",
    "power analysis",
    "pdk",
    "tfm",
    "density fill",
)

# Words that mark a title as software work despite a hardware-domain phrase.
SOFTWARE_TITLE_KEYWORDS = (
    "software",
    "firmware",
    "sdet",
    "sre",
    "site reliability",
    "network reliability",
    "devops",
    "machine learning",
    "ml",
    "data engineer",
    "full stack",
    "backend",
    "frontend",
    "front end",
    "front-end",
)

NON_SOFTWARE_TITLE_PHRASES = NON_SOFTWARE_ROLE_PHRASES + HARDWARE_DOMAIN_PHRASES

DEFAULT_EXCLUDED_TITLE_PHRASES = NON_IC_TITLE_PHRASES + EXECUTIVE_TITLE_PHRASES + NON_SOFTWARE_TITLE_PHRASES
