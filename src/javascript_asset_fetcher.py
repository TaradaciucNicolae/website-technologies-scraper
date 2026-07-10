from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class JavaScriptAsset:
    url: str
    status_code: int | None
    content_type: str | None
    content: str
    error: str | None


# Extracts absolute, fetchable script URLs from HTML using the final page URL as the base.
def extract_script_urls(html: str, base_url: str | None) -> list[str]:
    if base_url is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    script_urls: list[str] = []

    for script_tag in soup.find_all("script"):
        script_src = script_tag.get("src")

        if not script_src:
            continue

        script_src = str(script_src).strip()

        if not script_src:
            continue

        script_url = urljoin(base_url, script_src)

        if should_skip_script_url(script_url):
            continue

        if script_url not in script_urls:
            script_urls.append(script_url)

    return script_urls


# Filters out script pseudo-URLs or unsupported schemes that cannot be fetched as network assets.
def should_skip_script_url(script_url: str) -> bool:
    script_url_lower = script_url.lower()
    parsed_url = urlparse(script_url)

    # Pseudo URLs are not fetchable network assets and add noise to the JS scan,
    # so only real HTTP(S) script URLs are kept.
    if script_url_lower.startswith("data:"):
        return True

    if script_url_lower.startswith("blob:"):
        return True

    if script_url_lower.startswith("javascript:"):
        return True

    if parsed_url.scheme not in ["http", "https"]:
        return True

    return False


# Selects the highest-value JavaScript asset URLs to fetch while respecting the per-domain asset cap.
def select_javascript_asset_urls(
    script_urls: list[str],
    base_url: str | None,
    max_assets: int = 5,
) -> list[str]:
    base_domain = ""

    if base_url is not None:
        base_domain = urlparse(base_url).netloc.lower()

    scored_script_urls: list[tuple[int, int, str]] = []

    # Fetching every script can dominate runtime; scoring keeps the scan small
    # while favoring CDNs, bundles, vendor files, and analytics scripts.
    for index, script_url in enumerate(script_urls):
        score = score_script_url(script_url, base_domain)
        scored_script_urls.append((score, index, script_url))

    scored_script_urls.sort(key=lambda item: (-item[0], item[1]))

    selected_urls: list[str] = []

    for score, index, script_url in scored_script_urls[:max_assets]:
        selected_urls.append(script_url)

    return selected_urls


# Scores a script URL so external, CDN, bundle, vendor, and analytics scripts are prioritized.
def score_script_url(script_url: str, base_domain: str) -> int:
    score = 0
    script_url_lower = script_url.lower()
    script_domain = urlparse(script_url).netloc.lower()

    if script_domain and script_domain != base_domain:
        score = score + 3

    important_words = [
        "cdn",
        "bundle",
        "app",
        "main",
        "vendor",
        "chunk",
        "theme",
        "analytics",
        "pixel",
        "tracking",
    ]

    for word in important_words:
        if word in script_url_lower:
            score = score + 2
            break

    if script_url_lower.endswith(".js") or ".js?" in script_url_lower:
        score = score + 1

    return score


# Fetches one JavaScript asset with timeout and byte limits, returning content or an error record.
def fetch_javascript_asset(
    script_url: str,
    timeout_seconds: int = 5,
    max_bytes: int = 500_000,
) -> JavaScriptAsset:
    try:
        response = requests.get(
            script_url,
            timeout=timeout_seconds,
            stream=True,
            headers={
                "User-Agent": "Website Technologies Scraper"
            },
        )

        content_type = response.headers.get("Content-Type")

        if response.status_code >= 400:
            return JavaScriptAsset(
                url=script_url,
                status_code=response.status_code,
                content_type=content_type,
                content="",
                error=f"HTTP {response.status_code}",
            )

        content_bytes = bytearray()

        # Stream with a byte cap so very large bundles cannot consume the whole
        # per-domain budget by themselves.
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue

            remaining_bytes = max_bytes - len(content_bytes)
            content_bytes.extend(chunk[:remaining_bytes])

            if len(content_bytes) >= max_bytes:
                break

        encoding = response.encoding or "utf-8"

        try:
            content = content_bytes.decode(encoding, errors="replace")
        except LookupError:
            content = content_bytes.decode("utf-8", errors="replace")

        return JavaScriptAsset(
            url=script_url,
            status_code=response.status_code,
            content_type=content_type,
            content=content,
            error=None,
        )

    except requests.RequestException as error:
        return JavaScriptAsset(
            url=script_url,
            status_code=None,
            content_type=None,
            content="",
            error=str(error),
        )


# Extracts, prioritizes, and fetches the limited JavaScript assets used as extra detection evidence.
def fetch_javascript_assets(
    html: str,
    base_url: str | None,
    max_assets: int = 5,
    timeout_seconds: int = 5,
    max_bytes: int = 500_000,
) -> list[JavaScriptAsset]:
    script_urls = extract_script_urls(html, base_url)
    selected_script_urls = select_javascript_asset_urls(
        script_urls=script_urls,
        base_url=base_url,
        max_assets=max_assets,
    )

    javascript_assets: list[JavaScriptAsset] = []

    for script_url in selected_script_urls:
        javascript_asset = fetch_javascript_asset(
            script_url=script_url,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        javascript_assets.append(javascript_asset)

    return javascript_assets
