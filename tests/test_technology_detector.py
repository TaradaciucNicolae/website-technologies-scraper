import unittest
from pathlib import Path

from src.technology_detector import detect_technologies, load_technology_rules


RULES_PATH = Path("rules/technology_rules.json")


class TechnologyDetectorTests(unittest.TestCase):

    # Test detection using only an HTML URL/signature.
    def test_detects_shopify_from_html(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html='<script src="https://cdn.shopify.com/app.js"></script>',
            headers={},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Shopify", detected_names)



    # Test detection using only an HTML path/signature.
    def test_detects_wordpress_from_html(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html='<link href="/wp-content/themes/theme/style.css">',
            headers={},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("WordPress", detected_names)



    # # Test detection using only a header value.
    def test_detects_cloudflare_from_header_value(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html="",
            headers={"Server": "cloudflare"},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Cloudflare", detected_names)



    # Test detection using only the presence of a header.
    def test_detects_cloudflare_from_header_presence(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html="",
            headers={"CF-Ray": "abc123"},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Cloudflare", detected_names)



    # Test that no technology is detected when HTML and headers do not match any rule.
    def test_returns_empty_list_when_no_rule_matches(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html="<html><body>Hello</body></html>",
            headers={"Server": "nginx"},
            rules=rules,
        )

        self.assertEqual(detections, [])


    # Test detection when HTML and headers contain multiple technology signatures.
    def test_detects_multiple_technologies_from_html_and_headers(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html=(
                '<script src="https://cdn.shopify.com/app.js"></script>'
                '<script src="https://www.googletagmanager.com/gtm.js?id=GTM-ABC"></script>'
                '<link href="/wp-content/themes/theme/style.css">'
            ),
            headers={
                "Server": "cloudflare",
                "CF-Ray": "abc123",
            },
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Shopify", detected_names)
        self.assertIn("Google Tag Manager", detected_names)
        self.assertIn("WordPress", detected_names)
        self.assertIn("Cloudflare", detected_names)


    # Test that detection works even when HTML and headers use uppercase letters.
    def test_detects_signatures_case_insensitively(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html='<script src="https://CDN.SHOPIFY.COM/app.js"></script>',
            headers={"Server": "CLOUDFLARE"},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Shopify", detected_names)
        self.assertIn("Cloudflare", detected_names)


    # Test that a detected technology includes evidence explaining the match.
    def test_detection_includes_evidence_details(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            html='<script src="https://cdn.shopify.com/app.js"></script>',
            headers={},
            rules=rules,
        )

        shopify_detection = next(
            detection
            for detection in detections
            if detection.name == "Shopify"
        )

        self.assertEqual(shopify_detection.category, "Ecommerce")
        self.assertEqual(shopify_detection.confidence, "high")
        self.assertGreater(len(shopify_detection.evidence), 0)
        self.assertEqual(shopify_detection.evidence[0].source, "html")
        self.assertEqual(shopify_detection.evidence[0].matched, "cdn.shopify.com")

if __name__ == "__main__":
    unittest.main()