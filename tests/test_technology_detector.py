import unittest
from pathlib import Path

from src.technology_detector import detect_technologies, load_technology_rules


RULES_PATH = Path("rules/technology_rules.json")


class TechnologyDetectorTests(unittest.TestCase):

    # Test detection using only an HTML URL/signature.
    def test_detects_shopify_from_html(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
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
            domain="example.com",
            final_url="https://example.com",
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
            domain="example.com",
            final_url="https://example.com",
            html="",
            headers={"Server": "cloudflare"},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Cloudflare", detected_names)


    # Test that header evidence contains detailed fields.
    def test_header_evidence_uses_new_evidence_fields(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html="",
            headers={"Server": "cloudflare"},
            rules=rules,
        )

        cloudflare_detection = next(
            detection
            for detection in detections
            if detection.name == "Cloudflare"
        )

        header_evidence = cloudflare_detection.evidence[0]

        self.assertEqual(header_evidence.type, "header")
        self.assertEqual(header_evidence.source, "headers")
        self.assertEqual(header_evidence.location, "server")
        self.assertEqual(header_evidence.matched_value, "cloudflare")
        self.assertEqual(header_evidence.excerpt, "server: cloudflare")
        self.assertEqual(header_evidence.confidence, "high")
        self.assertIn("server", header_evidence.explanation.lower())


    # Test detection using only the presence of a header.
    def test_detects_cloudflare_from_header_presence(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
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
            domain="example.com",
            final_url="https://example.com",
            html="<html><body>Hello</body></html>",
            headers={"Server": "nginx"},
            rules=rules,
        )

        self.assertEqual(detections, [])


    # Test detection when HTML and headers contain multiple technology signatures.
    def test_detects_multiple_technologies_from_html_and_headers(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
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
            domain="example.com",
            final_url="https://example.com",
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
            domain="example.com",
            final_url="https://example.com",
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

        shopify_evidence = next(
            evidence
            for evidence in shopify_detection.evidence
            if evidence.type == "script_url"
        )

        self.assertEqual(shopify_evidence.type, "script_url")
        self.assertEqual(shopify_evidence.source, "html")
        self.assertEqual(shopify_evidence.location, "script[src]")
        self.assertEqual(shopify_evidence.matched_value, "cdn.shopify.com")
        self.assertIn("cdn.shopify.com", shopify_evidence.excerpt)
        self.assertEqual(shopify_evidence.confidence, "high")
        self.assertIn("script URL", shopify_evidence.explanation)



    # Test detection using only the domain name.
    def test_detects_weebly_from_domain(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="1planettechnologies.weebly.com",
            final_url="https://1planettechnologies.weebly.com",
            html="",
            headers={},
            rules=rules,
        )

        detected_names = [detection.name for detection in detections]

        self.assertIn("Weebly", detected_names)


    # Test that domain evidence contains detailed fields.
    def test_domain_evidence_uses_new_evidence_fields(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="1planettechnologies.weebly.com",
            final_url="https://1planettechnologies.weebly.com",
            html="",
            headers={},
            rules=rules,
        )

        weebly_detection = next(
            detection
            for detection in detections
            if detection.name == "Weebly"
        )

        domain_evidence = weebly_detection.evidence[0]

        self.assertEqual(domain_evidence.type, "domain")
        self.assertEqual(domain_evidence.source, "url")
        self.assertEqual(domain_evidence.location, "domain_or_final_url")
        self.assertEqual(domain_evidence.matched_value, "weebly.com")
        self.assertIn("weebly.com", domain_evidence.excerpt)
        self.assertEqual(domain_evidence.confidence, "high")
        self.assertIn("domain", domain_evidence.explanation.lower())



            # Test detection using only a cookie name.
    def test_detects_google_analytics_from_cookie_name(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html="",
            headers={},
            rules=rules,
            cookies={"_ga": "GA1.1.123456789.123456789"},
        )

        google_analytics_detection = next(
            detection
            for detection in detections
            if detection.name == "Google Analytics"
        )

        cookie_evidence = next(
            evidence
            for evidence in google_analytics_detection.evidence
            if evidence.type == "cookie"
        )

        self.assertEqual(cookie_evidence.source, "cookies")
        self.assertEqual(cookie_evidence.location, "cookie_name")
        self.assertEqual(cookie_evidence.matched_value, "_ga")
        self.assertIn("_ga", cookie_evidence.excerpt)
        self.assertEqual(cookie_evidence.confidence, "high")



    # Test detection using a structured meta generator tag.
    def test_detects_wordpress_from_meta_generator(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<meta name="generator" content="WordPress 6.5">',
            headers={},
            rules=rules,
        )

        wordpress_detection = next(
            detection
            for detection in detections
            if detection.name == "WordPress"
        )

        meta_evidence = next(
            evidence
            for evidence in wordpress_detection.evidence
            if evidence.type == "meta_generator"
        )

        self.assertEqual(meta_evidence.source, "html")
        self.assertEqual(meta_evidence.location, 'meta[name="generator"]')
        self.assertEqual(meta_evidence.matched_value, "wordpress")
        self.assertIn("WordPress 6.5", meta_evidence.excerpt)
        self.assertEqual(meta_evidence.confidence, "high")




    # Test detection using a structured stylesheet URL.
    def test_stylesheet_url_evidence_uses_split_rules(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<link href="/wp-content/themes/theme/style.css">',
            headers={},
            rules=rules,
        )

        wordpress_detection = next(
            detection
            for detection in detections
            if detection.name == "WordPress"
        )

        stylesheet_evidence = next(
            evidence
            for evidence in wordpress_detection.evidence
            if evidence.type == "stylesheet_url"
        )

        self.assertEqual(stylesheet_evidence.source, "html")
        self.assertEqual(stylesheet_evidence.location, "link[href]")
        self.assertEqual(stylesheet_evidence.matched_value, "wp-content")
        self.assertIn("wp-content", stylesheet_evidence.excerpt)
        self.assertEqual(stylesheet_evidence.confidence, "high")


        
if __name__ == "__main__":
    unittest.main()