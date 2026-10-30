#!/usr/bin/env python3
"""
List stored jobs the title filters drop, grouped by the rule that dropped them.

Use after changing companies/filters.py to spot real roles being filtered out:
    .venv/bin/python tools/filter_audit.py            # counts per rule
    .venv/bin/python tools/filter_audit.py --show 20  # plus up to 20 titles each
"""

import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from companies.filters import HARDWARE_DOMAIN_PHRASES, NON_SOFTWARE_TITLE_PHRASES, SOFTWARE_TITLE_KEYWORDS  # noqa: E402
from state import CORE_ROLE_PHRASES, _contains_term, _normalize_title, passes_title_filters  # noqa: E402


def drop_reason(title: str, runtime_config) -> str:
    text = _normalize_title(title)
    included = runtime_config.definition.included_title_keywords
    if included and not any(_contains_term(text, keyword) for keyword in included):
        return "no role keyword"
    is_software = any(_contains_term(text, keyword) for keyword in SOFTWARE_TITLE_KEYWORDS)
    is_core = any(_contains_term(text, phrase) for phrase in CORE_ROLE_PHRASES)
    for phrase in runtime_config.excluded_title_phrases:
        if not _contains_term(text, phrase):
            continue
        if is_software and phrase in HARDWARE_DOMAIN_PHRASES:
            continue
        if is_core and phrase in NON_SOFTWARE_TITLE_PHRASES:
            continue
        return f'phrase "{phrase}"'
    return "level"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", type=int, default=0, help="Titles to print per rule.")
    args = parser.parse_args()

    dropped = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(config.SEEN_JOBS_DIR, "*.json"))):
        slug = os.path.basename(path)[:-5]
        if slug.startswith("_"):
            continue
        runtime_config = config.get_company_runtime(slug)
        with open(path) as handle:
            jobs = json.load(handle).get("jobs", {})
        for entry in jobs.values():
            title = entry.get("title", "")
            if title and not passes_title_filters(title, runtime_config):
                dropped[drop_reason(title, runtime_config)].append(f"{slug}: {title}")

    for reason, titles in sorted(dropped.items(), key=lambda item: -len(item[1])):
        print(f"{len(titles):6}  {reason}")
        for title in sorted(set(titles))[: args.show]:
            print(f"          {title}")


if __name__ == "__main__":
    main()
