from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TechnologyEvidence: # Proof that explains why a technology was detected.
    source: str
    matched: str
    proof: str


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
    header_signatures: dict[str, list[str]]


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
                header_signatures=raw_rule.get("header_signatures", {})
            )
        )

    # Return a list of TechnologyRule objects used by the detector.
    return rules



# We detect website technologies by matching known signatures. 
# We check both the HTML response and HTTP headers (each match is returned with evidence)
def detect_technologies(
    html: str,
    headers: dict[str, str],
    rules: list[TechnologyRule],
) -> list[TechnologyDetection]:
    
    # Normalize the HTML and headers
    html_lower = html.lower()
    normalized_headers = {
        key.lower(): value.lower()
        for key, value in headers.items()
    }

    detections: list[TechnologyDetection] = []

    for rule in rules:
        evidence = collect_evidence_for_rule(rule, html_lower, normalized_headers)

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


# Collect all proof items for a single technology rule.
def collect_evidence_for_rule(
    rule: TechnologyRule,
    html_lower: str,
    normalized_headers: dict[str, str],
) -> list[TechnologyEvidence]:
    

    evidence: list[TechnologyEvidence] = []
    evidence.extend(collect_html_evidence(html_lower, rule.html_signatures))
    evidence.extend(collect_header_evidence(normalized_headers, rule.header_signatures))

    # Return all proof items found for this rule.
    return evidence


# Find technology signatures inside the HTML response.
def collect_html_evidence(
    html_lower: str,
    signatures: list[str],
) -> list[TechnologyEvidence]:
    
    evidence: list[TechnologyEvidence] = []

    for signature in signatures:
        normalized_signature = signature.lower()

        if normalized_signature not in html_lower:
            continue

        evidence.append(
            TechnologyEvidence(
                source="html",
                matched=signature,
                proof=f"Found '{signature}' in the HTML response."
            )
        )
    # Return HTML evidence items for the matched signatures.
    return evidence



# Find technology signatures inside HTTP response headers.
def collect_header_evidence(
    normalized_headers: dict[str, str],
    header_signatures: dict[str, list[str]],
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

        for signature in signatures:
            normalized_signature = signature.lower()

            if not normalized_signature:
                # Empty signature: the header only needs to exist.
                pass
            elif normalized_signature not in header_value:
                # Non-empty signature: the header value must contain it.
                continue

            evidence.append(
                TechnologyEvidence(
                    source="headers",
                    matched=f"{header_name}: {signature or '<present>'}",
                    proof=(
                        f"Found HTTP header '{header_name}' "
                        f"with value '{header_value}'."
                    ),
                )
            )
            break

    # Return header evidence items for the matched signatures.
    return evidence