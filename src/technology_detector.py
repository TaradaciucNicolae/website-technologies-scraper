from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.javascript_asset_fetcher import JavaScriptAsset


@dataclass
class TechnologyEvidence: # Explanation that explains why a technology was detected.
    type: str
    source: str
    location: str
    matched_value: str
    excerpt: str
    confidence: str
    explanation: str

    @property
    def matched(self) -> str:
        return self.matched_value


@dataclass
class TechnologyDetection: # A technology found on a website, together with its evidence.
    name: str
    category: str
    confidence: str
    evidence: list[TechnologyEvidence]


@dataclass
class TechnologyRule: # A rule for detecting a specific technology.
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


def load_raw_technology_rules(rules_path: Path) -> list[dict]:
    if rules_path.is_dir():
        return load_raw_technology_rules_from_directory(rules_path)

    return json.loads(rules_path.read_text(encoding="utf-8"))


def load_raw_technology_rules_from_directory(rules_directory: Path) -> list[dict]:
    raw_rules: list[dict] = []

    for rules_file in sorted(rules_directory.glob("*_rules.json")):
        raw_rules_from_file = json.loads(rules_file.read_text(encoding="utf-8"))
        raw_rules.extend(raw_rules_from_file)

    raw_rules.sort(key=lambda raw_rule: raw_rule["name"].lower())

    return raw_rules


# Load technology detection rules from a JSON file or from a rules directory.
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
                header_signatures=raw_rule.get("header_signatures", {})
            )
        )

    # Return a list of TechnologyRule objects used by the detector.
    return rules


def build_excerpt(text: str, matched_value: str, characters_around_match: int = 60) -> str:
    if not text:
        return ""

    text_lower = text.lower()
    matched_value_lower = matched_value.lower()
    match_index = text_lower.find(matched_value_lower)

    if match_index == -1:
        return " ".join(text[:120].split())

    start_index = max(match_index - characters_around_match, 0)
    end_index = min(match_index + len(matched_value) + characters_around_match, len(text))

    excerpt = text[start_index:end_index]
    excerpt = " ".join(excerpt.split())

    if start_index > 0:
        excerpt = "..." + excerpt

    if end_index < len(text):
        excerpt = excerpt + "..."

    return excerpt


# We detect website technologies by matching known signatures.
# We check both the HTML response and HTTP headers (each match is returned with evidence)
def detect_technologies(
    domain: str,
    final_url: str | None,
    html: str,
    headers: dict[str, str],
    rules: list[TechnologyRule],
    cookies: dict[str, str] | None = None,
    javascript_assets: list[JavaScriptAsset] | None = None,
) -> list[TechnologyDetection]:
    
    # Normalize the headers
    normalized_headers = {
        key.lower(): value
        for key, value in headers.items()
    }

    if cookies is None:
        cookies = {}
    
    if javascript_assets is None:
        javascript_assets = []

    detections: list[TechnologyDetection] = []

    for rule in rules:
        evidence = collect_evidence_for_rule(rule, domain, final_url, html, normalized_headers, cookies, javascript_assets)

        if not evidence:
            continue

        detections.append(
            TechnologyDetection(
                name=rule.name,
                category=rule.category,
                confidence=rule.confidence,
                evidence=evidence
            )
        )

    # Return detected technologies, each containing its evidence list.
    return detections


# Collect all explanation items for a single technology rule.
def collect_evidence_for_rule(
    rule: TechnologyRule,
    domain: str,
    final_url: str | None,
    html: str,
    normalized_headers: dict[str, str],
    cookies: dict[str, str],
    javascript_assets: list[JavaScriptAsset],
) -> list[TechnologyEvidence]:

    evidence: list[TechnologyEvidence] = []

    evidence.extend(
        collect_domain_evidence(domain, final_url, rule.domain_signatures, rule.confidence)
    )
    evidence.extend(
        collect_html_evidence(
            html=html,
            html_signatures=rule.html_signatures,
            script_url_signatures=rule.script_url_signatures,
            package_url_signatures=rule.package_url_signatures,
            stylesheet_url_signatures=rule.stylesheet_url_signatures,
            meta_generator_signatures=rule.meta_generator_signatures,
            dom_marker_signatures=rule.dom_marker_signatures,
            confidence=rule.confidence,
        )
    )
    evidence.extend(
        collect_cookie_evidence(cookies, rule.cookie_signatures, rule.confidence)
    )

    evidence.extend(
        collect_javascript_asset_evidence(
            javascript_assets,
            rule.js_asset_signatures,
            rule.confidence,
        )
    )

    evidence.extend(
        collect_header_evidence(normalized_headers, rule.header_signatures, rule.confidence)
    )

    # Return all explanation items found for this rule.
    return evidence


def collect_domain_evidence(
    domain: str,
    final_url: str | None,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    original_text = domain
    text_to_check = domain.lower()

    if final_url is not None:
        original_text = original_text + " " + final_url
        text_to_check = text_to_check + " " + final_url.lower()

    for signature in signatures:
        normalized_signature = signature.lower()

        if normalized_signature not in text_to_check:
            continue

        evidence.append(
            TechnologyEvidence(
                type="domain",
                source="url",
                location="domain_or_final_url",
                matched_value=signature,
                excerpt=build_excerpt(original_text, signature),
                confidence=confidence,
                explanation=f"Found '{signature}' in the domain or final URL.",
            )
        )

    return evidence

# Find technology signatures inside the HTML response.
def collect_html_evidence(
    html: str,
    html_signatures: list[str],
    script_url_signatures: list[str],
    package_url_signatures: list[str],
    stylesheet_url_signatures: list[str],
    meta_generator_signatures: list[str],
    dom_marker_signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:

    evidence: list[TechnologyEvidence] = []
    soup = BeautifulSoup(html, "html.parser")

    evidence.extend(collect_script_url_evidence(soup, script_url_signatures, confidence))
    evidence.extend(collect_package_url_evidence(soup, package_url_signatures, confidence))
    evidence.extend(collect_stylesheet_url_evidence(soup, stylesheet_url_signatures, confidence))
    evidence.extend(collect_meta_generator_evidence(soup, meta_generator_signatures, confidence))
    evidence.extend(collect_dom_marker_evidence(soup, dom_marker_signatures, confidence))
    evidence.extend(collect_raw_html_evidence(html, html_signatures, confidence))

    # Return HTML evidence items for the matched signatures.
    return evidence


def collect_script_url_evidence(
    soup: BeautifulSoup,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for script_tag in soup.find_all("script"):
        script_url = script_tag.get("src")

        if not script_url:
            continue

        script_url = str(script_url)
        script_url_lower = script_url.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if not normalized_signature:
                continue

            if normalized_signature not in script_url_lower:
                continue

            evidence.append(
                TechnologyEvidence(
                    type="script_url",
                    source="html",
                    location="script[src]",
                    matched_value=signature,
                    excerpt=script_url,
                    confidence=confidence,
                    explanation=f"Found '{signature}' in a script URL.",
                )
            )
            break

    return evidence


def remove_package_version(package_part: str) -> str:
    if package_part.startswith("@"):
        return package_part

    return package_part.split("@")[0]


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


def extract_package_name_from_cdn_url(asset_url: str) -> str | None:
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


def collect_package_url_evidence(
    soup: BeautifulSoup,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []
    normalized_signatures = {
        signature.lower()
        for signature in signatures
        if signature
    }

    if not normalized_signatures:
        return evidence

    for script_tag in soup.find_all("script"):
        script_url = script_tag.get("src")

        if not script_url:
            continue

        evidence_item = build_package_url_evidence(
            asset_url=str(script_url),
            location="script[src]",
            normalized_signatures=normalized_signatures,
            confidence=confidence,
        )

        if evidence_item is not None:
            evidence.append(evidence_item)

    for link_tag in soup.find_all("link"):
        stylesheet_url = link_tag.get("href")

        if not stylesheet_url:
            continue

        evidence_item = build_package_url_evidence(
            asset_url=str(stylesheet_url),
            location="link[href]",
            normalized_signatures=normalized_signatures,
            confidence=confidence,
        )

        if evidence_item is not None:
            evidence.append(evidence_item)

    return evidence


def build_package_url_evidence(
    asset_url: str,
    location: str,
    normalized_signatures: set[str],
    confidence: str,
) -> TechnologyEvidence | None:
    package_name = extract_package_name_from_cdn_url(asset_url)

    if package_name is None:
        return None

    if package_name not in normalized_signatures:
        return None

    return TechnologyEvidence(
        type="package_url",
        source="html",
        location=location,
        matched_value=package_name,
        excerpt=asset_url,
        confidence=confidence,
        explanation="Detected package name from a known CDN package URL.",
    )


def collect_stylesheet_url_evidence(
    soup: BeautifulSoup,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for link_tag in soup.find_all("link"):
        stylesheet_url = link_tag.get("href")

        if not stylesheet_url:
            continue

        stylesheet_url = str(stylesheet_url)
        stylesheet_url_lower = stylesheet_url.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if not normalized_signature:
                continue

            if normalized_signature not in stylesheet_url_lower:
                continue

            evidence.append(
                TechnologyEvidence(
                    type="stylesheet_url",
                    source="html",
                    location="link[href]",
                    matched_value=signature,
                    excerpt=stylesheet_url,
                    confidence=confidence,
                    explanation=f"Found '{signature}' in a stylesheet URL.",
                )
            )
            break

    return evidence


def collect_meta_generator_evidence(
    soup: BeautifulSoup,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for meta_tag in soup.find_all("meta"):
        meta_name = meta_tag.get("name", "")

        if str(meta_name).lower() != "generator":
            continue

        meta_content = str(meta_tag.get("content", ""))
        meta_content_lower = meta_content.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if not normalized_signature:
                continue

            if normalized_signature not in meta_content_lower:
                continue

            evidence.append(
                TechnologyEvidence(
                    type="meta_generator",
                    source="html",
                    location='meta[name="generator"]',
                    matched_value=signature,
                    excerpt=meta_content,
                    confidence=confidence,
                    explanation=f"Found '{signature}' in the meta generator tag.",
                )
            )
            break

    return evidence



def collect_dom_marker_evidence(
    soup: BeautifulSoup,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for html_tag in soup.find_all(True):
        for attribute_name, attribute_value in html_tag.attrs.items():
            if isinstance(attribute_value, list):
                attribute_value_text = " ".join(str(value) for value in attribute_value)
            else:
                attribute_value_text = str(attribute_value)

            attribute_text = f'{attribute_name}="{attribute_value_text}"'
            attribute_text_lower = attribute_text.lower()

            for signature in signatures:
                normalized_signature = signature.lower()

                if not normalized_signature:
                    continue

                if normalized_signature not in attribute_text_lower:
                    continue

                evidence.append(
                    TechnologyEvidence(
                        type="dom_marker",
                        source="html",
                        location=f"{html_tag.name}[{attribute_name}]",
                        matched_value=signature,
                        excerpt=attribute_text,
                        confidence=confidence,
                        explanation=f"Found '{signature}' in an HTML attribute.",
                    )
                )
                break

    return evidence

def collect_raw_html_evidence(
    html: str,
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:

    evidence: list[TechnologyEvidence] = []
    html_lower = html.lower()

    for signature in signatures:
        normalized_signature = signature.lower()

        if not normalized_signature:
            continue

        if normalized_signature not in html_lower:
            continue

        evidence.append(
            TechnologyEvidence(
                type="html_contains",
                source="html",
                location="html",
                matched_value=signature,
                excerpt=build_excerpt(html, signature),
                confidence=confidence,
                explanation=f"Found '{signature}' in the HTML response."
            )
        )

    return evidence









# Find technology signatures inside response cookie names.
def collect_cookie_evidence(
    cookies: dict[str, str],
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for cookie_name, cookie_value in cookies.items():
        cookie_name_lower = cookie_name.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if normalized_signature not in cookie_name_lower:
                continue

            excerpt = f"{cookie_name}={cookie_value}"

            if len(excerpt) > 120:
                excerpt = excerpt[:120] + "..."

            evidence.append(
                TechnologyEvidence(
                    type="cookie",
                    source="cookies",
                    location="cookie_name",
                    matched_value=signature,
                    excerpt=excerpt,
                    confidence=confidence,
                    explanation=f"Found cookie name '{cookie_name}' matching signature '{signature}'.",
                )
            )
            break

    return evidence


# Find technology signatures inside fetched JavaScript assets.
def collect_javascript_asset_evidence(
    javascript_assets: list[JavaScriptAsset],
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for javascript_asset in javascript_assets:
        if javascript_asset.error is not None:
            continue

        javascript_content_lower = javascript_asset.content.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if not normalized_signature:
                continue

            if normalized_signature not in javascript_content_lower:
                continue

            evidence.append(
                TechnologyEvidence(
                    type="js_asset",
                    source="javascript",
                    location=javascript_asset.url,
                    matched_value=signature,
                    excerpt=build_excerpt(javascript_asset.content, signature),
                    confidence=confidence,
                    explanation=f"Found '{signature}' inside a JavaScript asset.",
                )
            )
            break

    return evidence



# Find technology signatures inside HTTP response headers.
def collect_header_evidence(
    normalized_headers: dict[str, str],
    header_signatures: dict[str, list[str]],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for header_name, signatures in header_signatures.items():

        # Normalize the header name
        normalized_header_name = header_name.lower()

        # In the headers dictionary, the header name is the key and the header content is the value.
        # Example: looking up key "server" returns value "cloudflare".
        header_value = normalized_headers.get(normalized_header_name)

        if header_value is None:
            continue

        header_value_lower = header_value.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if normalized_signature and normalized_signature not in header_value_lower:
                continue

            if normalized_signature:
                matched_value = signature
                explanation = f"Found '{signature}' in HTTP header '{normalized_header_name}'."
            else:
                matched_value = header_value
                explanation = f"Found HTTP header '{normalized_header_name}'."

            evidence.append(
                TechnologyEvidence(
                    type="header",
                    source="headers",
                    location=normalized_header_name,
                    matched_value=matched_value,
                    excerpt=f"{normalized_header_name}: {header_value}",
                    confidence=confidence,
                    explanation=explanation,
                )
            )
            break

    # Return header evidence items for the matched signatures.
    return evidence
