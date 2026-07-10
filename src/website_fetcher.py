from dataclasses import dataclass
import time

import requests


# Browser-like request headers help many sites return their normal homepage
# instead of a simplified bot or block response.
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


@dataclass
class WebsiteFetchResult:
    domain: str
    attempted_urls: list[str]
    successful_url: str | None
    final_url: str | None
    status_code: int | None
    headers: dict[str, str]
    cookies: dict[str, str]
    html: str
    error: str | None
    elapsed_ms: int | None
    content_type: str | None
    redirect_count: int



# Fetches a website homepage over HTTPS with HTTP fallback and returns response
# metadata, cookies, and HTML for technology detection.
def fetch_website(
    domain: str,
    timeout_seconds: int = 20,
    request_headers: dict[str, str] | None = None,
) -> WebsiteFetchResult:
    attempted_urls: list[str] = []
    last_error: str | None = None
    start_time = time.perf_counter()
    headers = DEFAULT_REQUEST_HEADERS.copy()

    if request_headers is not None:
        headers.update(request_headers)

    # HTTPS is the canonical version for most sites, while the HTTP fallback
    # keeps older or misconfigured domains from being discarded too early.
    for transfer_protocol in ["https", "http"]:
        attempted_url = f"{transfer_protocol}://{domain}"
        attempted_urls.append(attempted_url)

        try:
            response = requests.get(
                attempted_url,
                timeout=timeout_seconds,
                allow_redirects=True,
                headers=headers,
            )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            content_type = response.headers.get("Content-Type")
            redirect_count = len(response.history)

            return WebsiteFetchResult(
                domain=domain,
                attempted_urls=attempted_urls,
                successful_url=attempted_url,
                final_url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=response.cookies.get_dict(),
                html=response.text,
                error=None,
                elapsed_ms=elapsed_ms,
                content_type=content_type,
                redirect_count=redirect_count,
            )

        except requests.RequestException as error:
            last_error = str(error)

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    return WebsiteFetchResult(
        domain=domain,
        attempted_urls=attempted_urls,
        successful_url=None,
        final_url=None,
        status_code=None,
        headers={},
        cookies={},
        html="",
        error=last_error,
        elapsed_ms=elapsed_ms,
        content_type=None,
        redirect_count=0,
    )
