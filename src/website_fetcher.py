from dataclasses import dataclass
import time

import requests


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



def fetch_website(domain: str, timeout_seconds: int = 10) -> WebsiteFetchResult:
    attempted_urls: list[str] = []
    last_error: str | None = None
    start_time = time.perf_counter()

    for transfer_protocol in ["https", "http"]:
        attempted_url = f"{transfer_protocol}://{domain}"
        attempted_urls.append(attempted_url)

        try:
            response = requests.get(
                attempted_url,
                timeout=timeout_seconds,
                allow_redirects=True,
                headers={
                    "User-Agent": "Website Technologies Scraper"
                },
            )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            content_type = response.headers.get("Content-Type")
            redirect_count = len(response.history)

            return WebsiteFetchResult( # Return the result if the request is successful
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

    return WebsiteFetchResult( # Return the result with error information if all attempts fail
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