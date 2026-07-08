from dataclasses import dataclass
import requests


@dataclass
class WebsiteFetchResult:
    domain: str
    attempted_urls: list[str]
    successful_url: str | None
    final_url: str | None
    status_code: int | None
    headers: dict[str, str]
    html: str
    error: str | None

    

def fetch_website(domain: str, timeout_seconds: int = 10) -> WebsiteFetchResult:
    attempted_urls: list[str] = []
    last_error: str | None = None

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

            return WebsiteFetchResult( # Return the result if the request is successful
                domain=domain,
                attempted_urls=attempted_urls,
                successful_url=attempted_url,
                final_url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                html=response.text,
                error=None,
            )

        except requests.RequestException as error:
            last_error = str(error)


    return WebsiteFetchResult( # Return the result with error information if all attempts fail
        domain=domain,
        attempted_urls=attempted_urls,
        successful_url=None,
        final_url=None,
        status_code=None,
        headers={},
        html="",
        error=last_error,
    )

