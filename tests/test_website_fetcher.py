import unittest
from unittest.mock import patch

import requests

from src.website_fetcher import DEFAULT_REQUEST_HEADERS, fetch_website


class FakeCookies:

    def __init__(self, cookies: dict[str, str]) -> None:
        self.cookies = cookies

    def get_dict(self) -> dict[str, str]:
        return self.cookies


class FakeResponse:

    def __init__(self) -> None:
        self.url = "https://example.com/blocked"
        self.status_code = 403
        self.headers = {
            "Akamai-GRN": "0.12345678.1234567890.abcdef",
            "Content-Type": "text/html",
        }
        self.cookies = FakeCookies(
            {
                "akacd_example": "example-value",
            }
        )
        self.text = "<html><body>Forbidden</body></html>"
        self.history = []


class WebsiteFetcherTests(unittest.TestCase):

    @patch("src.website_fetcher.requests.get")
    def test_fetch_website_preserves_headers_and_cookies_for_403(self, mock_get) -> None:
        mock_get.return_value = FakeResponse()

        result = fetch_website("example.com")

        self.assertEqual(result.status_code, 403)
        self.assertEqual(result.final_url, "https://example.com/blocked")
        self.assertEqual(result.headers["Akamai-GRN"], "0.12345678.1234567890.abcdef")
        self.assertEqual(result.cookies["akacd_example"], "example-value")
        self.assertIsNone(result.error)


    @patch("src.website_fetcher.requests.get")
    def test_fetch_website_keeps_error_when_no_http_response_exists(self, mock_get) -> None:
        mock_get.side_effect = requests.Timeout("connection timed out")

        result = fetch_website("example.com")

        self.assertEqual(result.attempted_urls, ["https://example.com", "http://example.com"])
        self.assertIsNone(result.status_code)
        self.assertEqual({}, result.headers)
        self.assertEqual({}, result.cookies)
        self.assertEqual("", result.html)
        self.assertIn("connection timed out", result.error)


    @patch("src.website_fetcher.requests.get")
    def test_fetch_website_uses_browser_like_default_headers(self, mock_get) -> None:
        mock_get.return_value = FakeResponse()

        fetch_website("example.com")

        request_headers = mock_get.call_args.kwargs["headers"]

        for header_name, header_value in DEFAULT_REQUEST_HEADERS.items():
            self.assertEqual(request_headers[header_name], header_value)


if __name__ == "__main__":
    unittest.main()
