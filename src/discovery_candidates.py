import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.javascript_asset_fetcher import JavaScriptAsset
from src.technology_detector import TechnologyDetection, extract_package_name_from_cdn_url
from src.website_fetcher import WebsiteFetchResult


# This limit only controls which sites are written to discovery_candidates.json.
# It does not limit the real technology detections from the main output files.
MAX_DETECTION_COUNT_SHOWN_IN_DISCOVERY = 5


def create_discovery_store() -> dict:
    return {
        "sites": []
    }


def get_absolute_url(asset_url: str, base_url: str | None) -> str:
    if base_url is None:
        return asset_url

    return urljoin(base_url, asset_url)


def get_url_domain(asset_url: str | None) -> str:
    if asset_url is None:
        return ""

    return urlparse(asset_url).netloc.lower()


def is_external_url(asset_url: str, base_url: str | None) -> bool:
    asset_domain = get_url_domain(asset_url)
    base_domain = get_url_domain(base_url)

    if not asset_domain:
        return False

    if not base_domain:
        return True

    return asset_domain != base_domain


def is_stylesheet_link(link_tag) -> bool:
    stylesheet_url = str(link_tag.get("href", ""))
    stylesheet_url_lower = stylesheet_url.lower()
    rel_value = link_tag.get("rel", [])

    if isinstance(rel_value, list):
        rel_values = [
            str(value).lower()
            for value in rel_value
        ]
    else:
        rel_values = str(rel_value).lower().split()

    if "stylesheet" in rel_values:
        return True

    if stylesheet_url_lower.endswith(".css") or ".css?" in stylesheet_url_lower:
        return True

    if "fonts.googleapis.com/css" in stylesheet_url_lower:
        return True

    return False


def build_asset_signal(
    source: str,
    asset_url: str,
    base_url: str | None,
) -> dict:
    # Discovery keeps domains and package names beside the raw URL so repeated
    # unknown assets can be grouped into future rule candidates.
    absolute_url = get_absolute_url(asset_url, base_url)
    package_name = extract_package_name_from_cdn_url(absolute_url)

    return {
        "source": source,
        "url": absolute_url,
        "domain": get_url_domain(absolute_url),
        "is_external": is_external_url(absolute_url, base_url),
        "package_name": package_name,
    }


def collect_script_signals(soup: BeautifulSoup, base_url: str | None) -> list[dict]:
    script_signals: list[dict] = []

    for script_tag in soup.find_all("script"):
        script_url = script_tag.get("src")

        if not script_url:
            continue

        script_signals.append(
            build_asset_signal(
                source="script[src]",
                asset_url=str(script_url),
                base_url=base_url,
            )
        )

    return script_signals


def collect_stylesheet_signals(soup: BeautifulSoup, base_url: str | None) -> list[dict]:
    stylesheet_signals: list[dict] = []

    for link_tag in soup.find_all("link"):
        stylesheet_url = link_tag.get("href")

        if not stylesheet_url:
            continue

        if not is_stylesheet_link(link_tag):
            continue

        stylesheet_signals.append(
            build_asset_signal(
                source="link[href]",
                asset_url=str(stylesheet_url),
                base_url=base_url,
            )
        )

    return stylesheet_signals


def collect_meta_generator_values(soup: BeautifulSoup) -> list[str]:
    meta_generator_values: list[str] = []

    for meta_tag in soup.find_all("meta"):
        meta_name = str(meta_tag.get("name", "")).lower()

        if meta_name != "generator":
            continue

        meta_content = str(meta_tag.get("content", "")).strip()

        if meta_content:
            meta_generator_values.append(meta_content)

    return meta_generator_values


def collect_meta_tag_summaries(soup: BeautifulSoup) -> list[dict]:
    meta_tag_summaries: list[dict] = []

    for meta_tag in soup.find_all("meta"):
        meta_name = str(meta_tag.get("name", "")).strip()
        meta_property = str(meta_tag.get("property", "")).strip()
        meta_content = str(meta_tag.get("content", "")).strip()

        if not meta_name and not meta_property:
            continue

        if len(meta_content) > 160:
            meta_content = meta_content[:160] + "..."

        meta_tag_summaries.append(
            {
                "name": meta_name,
                "property": meta_property,
                "content": meta_content,
            }
        )

    return meta_tag_summaries


def build_javascript_asset_signals(javascript_assets: list[JavaScriptAsset]) -> list[dict]:
    javascript_asset_signals: list[dict] = []

    for javascript_asset in javascript_assets:
        javascript_asset_signals.append(
            {
                "source": "javascript_asset",
                "url": javascript_asset.url,
                "domain": get_url_domain(javascript_asset.url),
                "status_code": javascript_asset.status_code,
                "content_type": javascript_asset.content_type,
                "bytes_read": len(javascript_asset.content.encode("utf-8")),
                "error": javascript_asset.error,
                "package_name": extract_package_name_from_cdn_url(javascript_asset.url),
            }
        )

    return javascript_asset_signals


def build_package_candidates(
    script_signals: list[dict],
    stylesheet_signals: list[dict],
    javascript_asset_signals: list[dict],
) -> list[dict]:
    package_candidates: list[dict] = []

    for signal in script_signals + stylesheet_signals + javascript_asset_signals:
        package_name = signal.get("package_name")

        if package_name is None:
            continue

        package_candidates.append(
            {
                "source": signal["source"],
                "package_name": package_name,
                "url": signal["url"],
                "domain": signal["domain"],
            }
        )

    return package_candidates


def build_detected_technology_names(detections: list[TechnologyDetection]) -> list[str]:
    detected_technology_names: list[str] = []

    for detection in detections:
        detected_technology_names.append(detection.name)

    return detected_technology_names


def build_site_record(
    fetch_result: WebsiteFetchResult,
    detections: list[TechnologyDetection],
    javascript_assets: list[JavaScriptAsset],
) -> dict:
    # Discovery records are intentionally richer than normal result records:
    # they are for rule research, not for the public detection schema.
    base_url = fetch_result.final_url or fetch_result.successful_url
    soup = BeautifulSoup(fetch_result.html, "html.parser")
    script_signals = collect_script_signals(soup, base_url)
    stylesheet_signals = collect_stylesheet_signals(soup, base_url)
    javascript_asset_signals = build_javascript_asset_signals(javascript_assets)

    return {
        "domain": fetch_result.domain,
        "detection_count": len(detections),
        "detected": build_detected_technology_names(detections),
        "attempted_urls": fetch_result.attempted_urls,
        "successful_url": fetch_result.successful_url,
        "final_url": fetch_result.final_url,
        "status": fetch_result.status_code,
        "error": fetch_result.error,
        "content_type": fetch_result.content_type,
        "redirect_count": fetch_result.redirect_count,
        "html_length": len(fetch_result.html),
        "headers": fetch_result.headers,
        "cookies": fetch_result.cookies,
        "script_signals": script_signals,
        "stylesheet_signals": stylesheet_signals,
        "javascript_asset_signals": javascript_asset_signals,
        "meta_generator_values": collect_meta_generator_values(soup),
        "meta_tags": collect_meta_tag_summaries(soup),
        "package_candidates": build_package_candidates(
            script_signals=script_signals,
            stylesheet_signals=stylesheet_signals,
            javascript_asset_signals=javascript_asset_signals,
        ),
    }


def collect_discovery_candidates(
    discovery_store: dict,
    fetch_result: WebsiteFetchResult,
    detections: list[TechnologyDetection],
    javascript_assets: list[JavaScriptAsset],
) -> None:
    detection_count = len(detections)

    # High-detection pages already have enough evidence; the useful research
    # signal is concentrated in undetected or low-detection pages.
    if detection_count > MAX_DETECTION_COUNT_SHOWN_IN_DISCOVERY:
        return

    discovery_store["sites"].append(
        build_site_record(fetch_result, detections, javascript_assets)
    )


def sort_discovery_sites(sites: list[dict]) -> list[dict]:
    return sorted(
        sites,
        key=lambda site: (
            site["detection_count"],
            site["domain"],
        ),
    )


def split_discovery_sites_by_detection_count(sites: list[dict]) -> tuple[list[dict], list[dict]]:
    undetected_sites: list[dict] = []
    detected_low_number_sites: list[dict] = []

    for site in sort_discovery_sites(sites):
        if site["detection_count"] == 0:
            undetected_sites.append(site)
        else:
            detected_low_number_sites.append(site)

    return undetected_sites, detected_low_number_sites


def load_existing_discovery_candidates(output_path: Path) -> list[dict]:
    if not output_path.exists():
        return []

    if output_path.stat().st_size == 0:
        return []

    try:
        existing_discovery_candidates = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    existing_undetected_sites = existing_discovery_candidates.get("undetected")
    existing_detected_low_number_sites = existing_discovery_candidates.get("detected_low_number")

    # Older files used a single "sites" list; accepting both shapes lets append
    # mode work across local development runs.
    if isinstance(existing_undetected_sites, list) or isinstance(existing_detected_low_number_sites, list):
        existing_sites: list[dict] = []

        if isinstance(existing_undetected_sites, list):
            existing_sites.extend(existing_undetected_sites)

        if isinstance(existing_detected_low_number_sites, list):
            existing_sites.extend(existing_detected_low_number_sites)

        return existing_sites

    old_format_sites = existing_discovery_candidates.get("sites", [])

    if isinstance(old_format_sites, list):
        return old_format_sites

    return []


def save_discovery_candidates(discovery_store: dict, output_path: Path, rewrite: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sites = discovery_store["sites"]

    if rewrite == 0:
        existing_sites = load_existing_discovery_candidates(output_path)
        sites = existing_sites + sites

    undetected_sites, detected_low_number_sites = split_discovery_sites_by_detection_count(sites)

    output_path.write_text(
        json.dumps(
            {
                "undetected": undetected_sites,
                "detected_low_number": detected_low_number_sites,
                "max_detection_count_shown_in_discovery": MAX_DETECTION_COUNT_SHOWN_IN_DISCOVERY,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
