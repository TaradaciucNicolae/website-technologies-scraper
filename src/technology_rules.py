from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class TechnologyEvidence:
    # Evidence is the audit trail: every detection should point to the exact
    # signal that made the rule match.
    type: str
    source: str
    location: str
    matched_value: str
    excerpt: str
    confidence: str
    explanation: str

    # Provides a backwards-compatible alias for code that expects evidence.matched.
    @property
    def matched(self) -> str:
        return self.matched_value


@dataclass
class TechnologyDetection:
    name: str
    category: str
    confidence: str
    evidence: list[TechnologyEvidence]


@dataclass
class TechnologyRule:
    name: str
    category: str
    confidence: str
    domain_signatures: list[str]
    html_signatures: list[str]
    script_url_signatures: list[str]
    js_asset_signatures: list[str]
    package_url_signatures: list[str]
    stylesheet_url_signatures: list[str]
    meta_generator_signatures: list[str]
    dom_marker_signatures: list[str]
    cookie_signatures: list[str]
    header_signatures: dict[str, list[str]]


# Loads raw rule dictionaries from either a rules directory or a single JSON rules file.
def load_raw_technology_rules(rules_path: Path) -> list[dict]:
    if rules_path.is_dir():
        return load_raw_technology_rules_from_directory(rules_path)

    return json.loads(rules_path.read_text(encoding="utf-8"))


# Loads and alphabetically sorts all raw rule dictionaries from split *_rules.json files.
def load_raw_technology_rules_from_directory(rules_directory: Path) -> list[dict]:
    raw_rules: list[dict] = []

    # Stable file and rule ordering makes test failures and generated output
    # easier to compare after rule updates.
    for rules_file in sorted(rules_directory.glob("*_rules.json")):
        raw_rules_from_file = json.loads(rules_file.read_text(encoding="utf-8"))
        raw_rules.extend(raw_rules_from_file)

    raw_rules.sort(key=lambda raw_rule: raw_rule["name"].lower())

    return raw_rules


# Converts raw rule dictionaries into typed TechnologyRule objects used by the detector.
def load_technology_rules(rules_path: Path) -> list[TechnologyRule]:
    raw_rules = load_raw_technology_rules(rules_path)

    rules: list[TechnologyRule] = []

    for raw_rule in raw_rules:
        rules.append(
            TechnologyRule(
                name=raw_rule["name"],
                category=raw_rule["category"],
                confidence=raw_rule["confidence"],
                domain_signatures=raw_rule.get("domain_signatures", []),
                html_signatures=raw_rule.get("html_signatures", []),
                script_url_signatures=raw_rule.get("script_url_signatures", []),
                js_asset_signatures=raw_rule.get("js_asset_signatures", []),
                package_url_signatures=raw_rule.get("package_url_signatures", []),
                stylesheet_url_signatures=raw_rule.get("stylesheet_url_signatures", []),
                meta_generator_signatures=raw_rule.get("meta_generator_signatures", []),
                dom_marker_signatures=raw_rule.get("dom_marker_signatures", []),
                cookie_signatures=raw_rule.get("cookie_signatures", []),
                header_signatures=raw_rule.get("header_signatures", {}),
            )
        )

    return rules


# Removes the version suffix from a CDN package path segment while preserving scoped package names.
def remove_package_version(package_part: str) -> str:
    if package_part.startswith("@"):
        return package_part

    return package_part.split("@")[0]


# Reads a package name from CDN path segments, including scoped npm packages.
def read_package_name_from_url_parts(path_parts: list[str]) -> str | None:
    if not path_parts:
        return None

    first_part = remove_package_version(path_parts[0])

    if first_part.startswith("@"):
        if len(path_parts) < 2:
            return None

        second_part = remove_package_version(path_parts[1])
        return f"{first_part}/{second_part}".lower()

    return first_part.lower()


# Extracts package names from known CDN URL formats such as jsDelivr, unpkg, cdnjs, esm.sh, and Skypack.
def extract_package_name_from_cdn_url(asset_url: str) -> str | None:
    # Known CDN URL layouts expose package names directly, which is safer than
    # guessing from arbitrary filenames.
    parsed_url = urlparse(asset_url)
    hostname = parsed_url.netloc.lower()
    path_parts = [
        part
        for part in parsed_url.path.split("/")
        if part
    ]

    if hostname == "cdn.jsdelivr.net":
        if len(path_parts) >= 2 and path_parts[0] == "npm":
            return read_package_name_from_url_parts(path_parts[1:])

    if hostname in ["unpkg.com", "esm.unpkg.com"]:
        return read_package_name_from_url_parts(path_parts)

    if hostname == "cdnjs.cloudflare.com":
        if len(path_parts) >= 3 and path_parts[0] == "ajax" and path_parts[1] == "libs":
            return path_parts[2].lower()

    if hostname in ["esm.sh", "cdn.skypack.dev"]:
        return read_package_name_from_url_parts(path_parts)

    return None
