from bs4 import BeautifulSoup
from src.javascript_asset_fetcher import JavaScriptAsset
from src.technology_rules import (
    TechnologyDetection,
    TechnologyEvidence,
    TechnologyRule,
    extract_package_name_from_cdn_url,
    load_raw_technology_rules,
    load_raw_technology_rules_from_directory,
    load_technology_rules,
    read_package_name_from_url_parts,
    remove_package_version,
)


MAX_EVIDENCE_ITEMS_PER_TECHNOLOGY = 10


# Builds a short excerpt around a matched signature so evidence remains readable in output files.
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


# Applies all technology rules to one fetched domain and returns detections with capped evidence.
def detect_technologies(
    domain: str,
    final_url: str | None,
    html: str,
    headers: dict[str, str],
    rules: list[TechnologyRule],
    cookies: dict[str, str] | None = None,
    javascript_assets: list[JavaScriptAsset] | None = None,
) -> list[TechnologyDetection]:
    # The detector is intentionally deterministic: rules decide the result, and
    # every match returns evidence that can be reviewed later.
    normalized_headers = {
        key.lower(): value
        for key, value in headers.items()
    }

    if cookies is None:
        cookies = {}
    
    if javascript_assets is None:
        javascript_assets = []

    soup = BeautifulSoup(html, "html.parser")
    detections: list[TechnologyDetection] = []

    for rule in rules:
        evidence = collect_evidence_for_rule(
            rule,
            domain,
            final_url,
            html,
            soup,
            normalized_headers,
            cookies,
            javascript_assets,
        )

        if not evidence:
            continue

        detections.append(
            TechnologyDetection(
                name=rule.name,
                category=rule.category,
                confidence=rule.confidence,
                evidence=evidence[:MAX_EVIDENCE_ITEMS_PER_TECHNOLOGY],
            )
        )

    return detections


# Collects all evidence types for one rule across URLs, HTML, cookies, fetched JS assets, and headers.
def collect_evidence_for_rule(
    rule: TechnologyRule,
    domain: str,
    final_url: str | None,
    html: str,
    soup: BeautifulSoup,
    normalized_headers: dict[str, str],
    cookies: dict[str, str],
    javascript_assets: list[JavaScriptAsset],
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    # Separate evidence sources make the output more useful than a single broad
    # HTML match and help reviewers understand false positives.
    evidence.extend(
        collect_domain_evidence(domain, final_url, rule.domain_signatures, rule.confidence)
    )
    evidence.extend(
        collect_html_evidence(
            html=html,
            soup=soup,
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

    return evidence


# Finds technology signatures in the original domain and final redirected URL.
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


# Collects HTML-derived evidence from script URLs, package URLs, stylesheets,
# meta tags, DOM markers, and raw HTML.
def collect_html_evidence(
    html: str,
    soup: BeautifulSoup,
    html_signatures: list[str],
    script_url_signatures: list[str],
    package_url_signatures: list[str],
    stylesheet_url_signatures: list[str],
    meta_generator_signatures: list[str],
    dom_marker_signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    # URL/meta/DOM matches are usually more explainable than raw HTML matches,
    # so they are collected as dedicated evidence types first.
    if script_url_signatures:
        evidence.extend(collect_script_url_evidence(soup, script_url_signatures, confidence))

    if package_url_signatures:
        evidence.extend(collect_package_url_evidence(soup, package_url_signatures, confidence))

    if stylesheet_url_signatures:
        evidence.extend(collect_stylesheet_url_evidence(soup, stylesheet_url_signatures, confidence))

    if meta_generator_signatures:
        evidence.extend(collect_meta_generator_evidence(soup, meta_generator_signatures, confidence))

    if dom_marker_signatures:
        evidence.extend(collect_dom_marker_evidence(soup, dom_marker_signatures, confidence))

    if html_signatures:
        evidence.extend(collect_raw_html_evidence(html, html_signatures, confidence))

    return evidence


# Finds technology signatures inside script src URLs extracted from the parsed HTML.
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


# Collects package-name evidence from script and stylesheet URLs hosted on known package CDNs.
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


# Builds one package URL evidence item when a known CDN package name matches the rule.
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


# Finds technology signatures inside stylesheet href URLs extracted from the parsed HTML.
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


# Finds technology signatures exposed through meta name="generator" tags.
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

# Finds technology signatures in HTML tag attributes such as classes, data attributes, and framework markers.
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


# Finds technology signatures anywhere in the raw HTML response as a fallback evidence source.
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

# Finds technology signatures in response cookie names, including optional prefix signatures.
def collect_cookie_evidence(
    cookies: dict[str, str],
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for cookie_name, cookie_value in cookies.items():
        cookie_name_lower = cookie_name.lower()

        for signature in signatures:
            if not cookie_signature_matches(cookie_name_lower, signature):
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


# Checks whether a cookie name matches an exact/contains signature or a caret-prefixed cookie family.
def cookie_signature_matches(cookie_name_lower: str, signature: str) -> bool:
    normalized_signature = signature.lower()

    if not normalized_signature:
        return False

    if normalized_signature.startswith("^"):
        # A leading caret means prefix matching for cookie families with
        # generated suffixes, such as security or ecommerce cookies.
        expected_prefix = normalized_signature[1:]
        return cookie_name_lower.startswith(expected_prefix)

    return normalized_signature in cookie_name_lower


# Finds technology signatures inside the content of fetched JavaScript assets.
def collect_javascript_asset_evidence(
    javascript_assets: list[JavaScriptAsset],
    signatures: list[str],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    # JavaScript content is useful for widgets and libraries that do not expose
    # clear HTML markers, but asset fetching is limited before this point.
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

# Finds technology signatures inside normalized HTTP response headers.
def collect_header_evidence(
    normalized_headers: dict[str, str],
    header_signatures: dict[str, list[str]],
    confidence: str,
) -> list[TechnologyEvidence]:
    evidence: list[TechnologyEvidence] = []

    for header_name, signatures in header_signatures.items():
        normalized_header_name = header_name.lower()
        header_value = normalized_headers.get(normalized_header_name)

        if header_value is None:
            continue

        header_value_lower = header_value.lower()

        for signature in signatures:
            normalized_signature = signature.lower()

            if normalized_signature and normalized_signature not in header_value_lower:
                continue

            # An empty signature means the header's presence is specific enough
            # to count, for example vendor-only diagnostic headers.
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

    return evidence
