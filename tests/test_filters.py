"""Title filter regressions, from real titles found in filter audits."""

import pytest

import config
from state import passes_title_filters

KEEP = [
    "Senior Software Engineer",
    "Software Engineers II / Senior Software Engineers (Commerce Platforms)",
    "Software Engineer III- Python / AWS / AI Enablement",
    "Senior Data Scientist, GTM Data Science",
    "Sr Embedded SDE III, Hardware Engineering Services",
    "Computer Scientist",
    "Applied Researcher 4 (AI Foundations)",
    "Scientist II - Marketplace (Multiple Teams)",
    "Sr. Technical Staff",
    "SWE2: AI Builder",
    "Senior MLE, CreativeFlux, AI Studios",
    "Senior FullStack - Mid Market",
    "Principal Software Enginner - Parameters & Experimentation",
    "Software Engineering Technical Leader",
    "Quantitative Research [Multiple Positions Available]",
    "Machine Learning Scientist 5 - Sales, Ads DSE",
    "Business Intelligence Engineer, North America Network Sales and Operations planning",
    "Principal Backend Developer – Clinical Applications",
    "Staff Site Reliability Engineer (Hybrid)",
    "Data Engineer II, DSP Analytics",
    "Lead Member of Technical Staff",
]

DROP = [
    "Software Engineering Manager",
    "Managers, Software Engineering",
    "Director, Software Engineering",
    "Dir, Software Development",
    "Leader, Software Engineering",
    "Data Science Supervisor",
    "Software Engineering Intern",
    "NVIDIA 2027 Internships: Software Engineering",
    "Vice President, Product and Software Security",
    "Sales Engineer",
    "Customer Engineer, Cloud AI, Google Cloud",
    "Specialist Solutions Architect - AI/ML",
    "Consulting Engineer",
    "Oracle NetSuite - Account Executive - Corporate - Software West",
    "OD Software Sales Representative- Federal Civilian",
    "US Equity Research - Large Cap Software - Associate",
    "UX Researcher",
    "Senior UX Quantitative Researcher, Agentic AI",
    "Hardware Engineer, AI Accelerator Module Design",
    "Data Center Technician",
    "Product Manager, Data Platform",
    "Administrative Business Partner I - Engineering, Product and Design",
]


@pytest.fixture(scope="module")
def runtime_config():
    return config.get_company_runtime("microsoft")


@pytest.mark.parametrize("title", KEEP)
def test_keeps_target_roles(runtime_config, title):
    assert passes_title_filters(title, runtime_config)


@pytest.mark.parametrize("title", DROP)
def test_drops_other_roles(runtime_config, title):
    assert not passes_title_filters(title, runtime_config)


def test_goldman_vice_president_is_an_ic_level():
    goldman = config.get_company_runtime("goldman-sachs")
    assert passes_title_filters("Software Engineer, Vice President", goldman)
