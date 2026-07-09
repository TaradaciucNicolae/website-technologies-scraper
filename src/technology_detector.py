from dataclasses import dataclass
import json
from pathlib import Path


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
    html_signatures: list[str]
    cookie_signatures: list[str]
    header_signatures: dict[str, list[str]]
    domain_signatures: list[str]


# Load technology detection rules from a JSON file.
def load_technology_rules(rules_path: Path) -> list[TechnologyRule]:
    raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))

    rules: list[TechnologyRule] = []

    for raw_rule in raw_rules:
        rules.append(
            TechnologyRule(
                name=raw_rule["name"],
                category=raw_rule["category"],
                confidence=raw_rule["confidence"],
                html_signatures=raw_rule.get("html_signatures", []),
                cookie_signatures=raw_rule.get("cookie_signatures", []),
                header_signatures=raw_rule.get("header_signatures", {}),
                domain_signatures=raw_rule.get("domain_signatures", [])
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
) -> list[TechnologyDetection]:
    
    # Normalize the headers
    normalized_headers = {
        key.lower(): value
        for key, value in headers.items()
    }

    if cookies is None:
        cookies = {}

    detections: list[TechnologyDetection] = []

    for rule in rules:
        evidence = collect_evidence_for_rule(rule, domain, final_url, html, normalized_headers, cookies)

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
) -> list[TechnologyEvidence]:

    evidence: list[TechnologyEvidence] = []

    evidence.extend(
        collect_domain_evidence(domain, final_url, rule.domain_signatures, rule.confidence)
    )
    evidence.extend(
        collect_html_evidence(html, rule.html_signatures, rule.confidence)
    )
    evidence.extend(
        collect_cookie_evidence(cookies, rule.cookie_signatures, rule.confidence)
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
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:

    evidence: list[TechnologyEvidence] = []
    html_lower = html.lower()

    for signature in signatures:
        normalized_signature = signature.lower()

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

    # Return HTML evidence items for the matched signatures.
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