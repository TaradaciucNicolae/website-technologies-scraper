import unittest
from pathlib import Path

from src.javascript_asset_fetcher import JavaScriptAsset
from src.technology_detector import detect_technologies, load_technology_rules


RULES_PATH = Path("rules/technology_rules")


class TechnologyDetectorTests(unittest.TestCase):

    def get_detected_names(
        self,
        html: str = "",
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        javascript_assets: list[JavaScriptAsset] | None = None,
    ) -> list[str]:
        rules = load_technology_rules(RULES_PATH)

        if headers is None:
            headers = {}

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html=html,
            headers=headers,
            rules=rules,
            cookies=cookies,
            javascript_assets=javascript_assets,
        )

        return [detection.name for detection in detections]

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
            html="<html><body>Plain test page</body></html>",
            headers={"Server": "ExampleServer"},
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
        self.assertEqual(stylesheet_evidence.matched_value, "/wp-content/")
        self.assertIn("wp-content", stylesheet_evidence.excerpt)
        self.assertEqual(stylesheet_evidence.confidence, "high")

    # Test detection using a structured DOM marker.
    def test_detects_react_from_dom_marker(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<div data-reactroot=""></div>',
            headers={},
            rules=rules,
        )

        react_detection = next(
            detection
            for detection in detections
            if detection.name == "React"
        )

        dom_evidence = next(
            evidence
            for evidence in react_detection.evidence
            if evidence.type == "dom_marker"
        )

        self.assertEqual(dom_evidence.source, "html")
        self.assertEqual(dom_evidence.location, "div[data-reactroot]")
        self.assertEqual(dom_evidence.matched_value, "data-reactroot")
        self.assertIn("data-reactroot", dom_evidence.excerpt)
        self.assertEqual(dom_evidence.confidence, "medium")


    # Test a new CMS rule using the meta generator tag.
    def test_detects_drupal_from_meta_generator(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<meta name="generator" content="Drupal 10">',
            headers={},
            rules=rules,
        )

        drupal_detection = next(
            detection
            for detection in detections
            if detection.name == "Drupal"
        )

        meta_evidence = next(
            evidence
            for evidence in drupal_detection.evidence
            if evidence.type == "meta_generator"
        )

        self.assertEqual(meta_evidence.source, "html")
        self.assertEqual(meta_evidence.location, 'meta[name="generator"]')
        self.assertEqual(meta_evidence.matched_value, "drupal")
        self.assertIn("Drupal 10", meta_evidence.excerpt)
        self.assertEqual(meta_evidence.confidence, "high")


    # Test a new JavaScript framework rule using a DOM marker.
    def test_detects_angular_from_dom_marker(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<app-root ng-version="17.0.0"></app-root>',
            headers={},
            rules=rules,
        )

        angular_detection = next(
            detection
            for detection in detections
            if detection.name == "Angular"
        )

        dom_evidence = next(
            evidence
            for evidence in angular_detection.evidence
            if evidence.type == "dom_marker"
        )

        self.assertEqual(dom_evidence.source, "html")
        self.assertEqual(dom_evidence.location, "app-root[ng-version]")
        self.assertEqual(dom_evidence.matched_value, "ng-version")
        self.assertIn("ng-version", dom_evidence.excerpt)
        self.assertEqual(dom_evidence.confidence, "high")


    # Test a new CDN rule using HTTP headers.
    def test_detects_cloudfront_from_header(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html="",
            headers={"Server": "CloudFront"},
            rules=rules,
        )

        cloudfront_detection = next(
            detection
            for detection in detections
            if detection.name == "Amazon CloudFront"
        )

        header_evidence = next(
            evidence
            for evidence in cloudfront_detection.evidence
            if evidence.type == "header"
        )

        self.assertEqual(header_evidence.source, "headers")
        self.assertEqual(header_evidence.location, "server")
        self.assertEqual(header_evidence.matched_value, "CloudFront")
        self.assertEqual(header_evidence.excerpt, "server: CloudFront")
        self.assertEqual(header_evidence.confidence, "high")


    # Test a new analytics rule using a cookie name.
    def test_detects_microsoft_clarity_from_cookie(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html="",
            headers={},
            rules=rules,
            cookies={"_clck": "example-cookie-value"},
        )

        clarity_detection = next(
            detection
            for detection in detections
            if detection.name == "Microsoft Clarity"
        )

        cookie_evidence = next(
            evidence
            for evidence in clarity_detection.evidence
            if evidence.type == "cookie"
        )

        self.assertEqual(cookie_evidence.source, "cookies")
        self.assertEqual(cookie_evidence.location, "cookie_name")
        self.assertEqual(cookie_evidence.matched_value, "_clck")
        self.assertIn("_clck", cookie_evidence.excerpt)
        self.assertEqual(cookie_evidence.confidence, "high")


    # Test generic package detection from a known CDN package URL.
    def test_detects_react_from_cdn_package_url(self) -> None:
        rules = load_technology_rules(RULES_PATH)

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<script src="https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js"></script>',
            headers={},
            rules=rules,
        )

        react_detection = next(
            detection
            for detection in detections
            if detection.name == "React"
        )

        package_evidence = next(
            evidence
            for evidence in react_detection.evidence
            if evidence.type == "package_url"
        )

        self.assertEqual(package_evidence.source, "html")
        self.assertEqual(package_evidence.location, "script[src]")
        self.assertEqual(package_evidence.matched_value, "react")
        self.assertIn("cdn.jsdelivr.net/npm/react", package_evidence.excerpt)
        self.assertEqual(package_evidence.confidence, "medium")


    # Test detection from the content of a fetched JavaScript asset.
    def test_detects_segment_from_javascript_asset(self) -> None:
        rules = load_technology_rules(RULES_PATH)
        javascript_assets = [
            JavaScriptAsset(
                url="https://example.com/assets/app.bundle.js",
                status_code=200,
                content_type="application/javascript",
                content="analytics.load('example-write-key'); analytics.track('Page Loaded');",
                error=None,
            )
        ]

        detections = detect_technologies(
            domain="example.com",
            final_url="https://example.com",
            html='<script src="/assets/app.bundle.js"></script>',
            headers={},
            rules=rules,
            javascript_assets=javascript_assets,
        )

        segment_detection = next(
            detection
            for detection in detections
            if detection.name == "Segment"
        )

        javascript_evidence = next(
            evidence
            for evidence in segment_detection.evidence
            if evidence.type == "js_asset"
        )

        self.assertEqual(javascript_evidence.source, "javascript")
        self.assertEqual(javascript_evidence.location, "https://example.com/assets/app.bundle.js")
        self.assertEqual(javascript_evidence.matched_value, "analytics.load")
        self.assertIn("analytics.load", javascript_evidence.excerpt)
        self.assertEqual(javascript_evidence.confidence, "high")


    def test_min_js_alone_does_not_detect_removed_marketing_tools(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/assets/min.js"></script>'
        )

        false_positive_names = [
            "Admitad",
            "Apptus",
            "Chord",
            "Marketo Forms",
            "Mixpanel",
            "Q4 Cookie Monster",
            "Quanta",
            "Segmanta",
            "Sitecore Engagement Cloud",
            "Split",
        ]

        for technology_name in false_positive_names:
            self.assertNotIn(technology_name, detected_names)


    def test_og_image_alone_does_not_detect_cococart_or_lede(self) -> None:
        detected_names = self.get_detected_names(
            html='<meta property="og:image" content="https://example.com/image.png">'
        )

        self.assertNotIn("Cococart", detected_names)
        self.assertNotIn("Lede", detected_names)


    def test_wp_content_alone_does_not_detect_perfmatters(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/wp-content"></script>'
        )

        self.assertNotIn("Perfmatters", detected_names)


    def test_frontend_min_js_alone_does_not_detect_form_plugins(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/wp-content/plugins/example/assets/frontend.min.js"></script>'
        )

        self.assertNotIn("WPForms", detected_names)
        self.assertNotIn("ProfilePress", detected_names)


    def test_wpforms_still_detects_from_specific_plugin_path(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/wp-content/plugins/wpforms/assets/js/wpforms.js"></script>'
        )

        self.assertIn("WPForms", detected_names)


    def test_builder_alone_does_not_detect_removed_builders(self) -> None:
        detected_names = self.get_detected_names(
            html='<meta name="generator" content="Builder">'
        )

        self.assertNotIn("GoDaddy Website Builder", detected_names)
        self.assertNotIn("Hostinger Website Builder", detected_names)
        self.assertNotIn("BOOM", detected_names)
        self.assertNotIn("Sapren", detected_names)


    def test_detects_wix_from_specific_headers(self) -> None:
        detected_names = self.get_detected_names(
            headers={
                "Server": "Pepyaka",
                "X-Wix-Request-Id": "1730000000.123456789",
                "Link": "<https://static.wixstatic.com>; rel=preconnect",
            }
        )

        self.assertIn("Wix", detected_names)


    def test_detects_godaddy_website_builder_from_specific_signals(self) -> None:
        detected_names = self.get_detected_names(
            headers={
                "Server": "DPS/2.0.0-beta+sha-test",
                "Link": "<https://img1.wsimg.com/ceph-p3-01/website-builder-data-prod/static/widgets/UX.js>; rel=preload",
            },
            cookies={"dps_site_id": "example-site-id"},
        )

        self.assertIn("GoDaddy Website Builder", detected_names)


    def test_detects_typo3_from_asset_paths(self) -> None:
        detected_names = self.get_detected_names(
            html='<link href="/typo3/sysext/t3skin/stylesheets/standalone/errorpage-message.css" rel="stylesheet">'
        )

        self.assertIn("TYPO3 CMS", detected_names)


    def test_detects_aruba_from_proxy_headers(self) -> None:
        detected_names = self.get_detected_names(
            headers={
                "Server": "aruba-proxy",
                "X-Aruba-Cache": "MISS",
            }
        )

        self.assertIn("Aruba.it", detected_names)


    def test_detects_netobjects_fusion_from_meta_generator(self) -> None:
        detected_names = self.get_detected_names(
            html='<meta name="generator" content="NetObjects Fusion 5.0 for Windows">'
        )

        self.assertIn("NetObjects Fusion", detected_names)


    def test_detects_nazwa_cdn_from_headers(self) -> None:
        detected_names = self.get_detected_names(
            headers={
                "X-CDN-nazwa.pl-location": "AMS",
                "X-CDN-nazwa.pl-cache": "HIT",
            }
        )

        self.assertIn("nazwa.pl CDN", detected_names)


    def test_detects_engintron_from_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-Server-Powered-By": "Engintron"}
        )

        self.assertIn("Engintron", detected_names)


    def test_detects_simply_com_from_headers(self) -> None:
        detected_names = self.get_detected_names(
            headers={
                "Server": "Simply.com",
                "SimplyCom-Server": "Apache",
            }
        )

        self.assertIn("Simply.com", detected_names)


    def test_detects_php_from_x_powered_by_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-Powered-By": "PHP/8.2"}
        )

        self.assertIn("PHP", detected_names)


    def test_detects_php_from_session_cookie(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"PHPSESSID": "example-session"}
        )

        self.assertIn("PHP", detected_names)


    def test_detects_wp_engine_from_x_powered_by_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-Powered-By": "WP Engine"}
        )

        self.assertIn("WP Engine", detected_names)


    def test_detects_elementor_cloud_from_x_powered_by_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-Powered-By": "Elementor Cloud"}
        )

        self.assertIn("Elementor Cloud", detected_names)


    def test_detects_luxury_presence_from_x_powered_by_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-Powered-By": "Luxury Presence"}
        )

        self.assertIn("Luxury Presence", detected_names)


    def test_detects_canva_websites_from_csp_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Content-Security-Policy": "default-src 'self' https://csp.canva.com https://www.canva.com"}
        )

        self.assertIn("Canva Websites", detected_names)


    def test_detects_kinsta_from_vendor_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-Kinsta-Cache": "HIT"}
        )

        self.assertIn("Kinsta", detected_names)


    def test_detects_dealer_com_ddc_from_diagnostic_cookie(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"ddc_diag_akam_clientIP": "127.0.0.1"}
        )

        self.assertIn("Dealer.com / DDC", detected_names)


    def test_detects_salesforce_commerce_cloud_from_demandware_cookies(self) -> None:
        detected_names = self.get_detected_names(
            cookies={
                "dwac_example": "value",
                "dwsid": "session",
            }
        )

        self.assertIn("Salesforce Commerce Cloud", detected_names)


    def test_detects_ddos_guard_from_cookie_prefix(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"__ddg1_": "example-value"}
        )

        self.assertIn("DDoS-Guard", detected_names)


    def test_detects_cloudflare_web_analytics_from_script_url(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="https://performance.radar.cloudflare.com/beacon.js"></script>'
        )

        self.assertIn("Cloudflare Web Analytics", detected_names)


    def test_detects_swfobject_from_script_url(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/assets/swfobject.js"></script>'
        )

        self.assertIn("SWFObject", detected_names)


    def test_detects_asp_net_from_session_cookie(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"ASP.NET_SessionId": "example-session"}
        )

        self.assertIn("ASP.NET", detected_names)


    def test_detects_java_from_jsessionid_cookie(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"JSESSIONID": "example-session"}
        )

        self.assertIn("Java", detected_names)


    def test_detects_sucuri_from_cloudproxy_server_header(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Server": "Sucuri/Cloudproxy"}
        )

        self.assertIn("Sucuri", detected_names)


    def test_detects_breakdance_from_cookie_name(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"breakdance_view_count": "1"}
        )

        self.assertIn("Breakdance", detected_names)


    def test_detects_wp_accessibility_from_plugin_path(self) -> None:
        detected_names = self.get_detected_names(
            html='<link rel="stylesheet" href="/wp-content/plugins/wp-accessibility/css/wpa-style.css">'
        )

        self.assertIn("WP Accessibility", detected_names)


    def test_detects_fastly_from_server_timing(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Server-Timing": "cache;desc=hit, varnish;desc=hit_hit, dc;desc=fastly_g"}
        )

        self.assertIn("Fastly", detected_names)


    def test_detects_varnish_from_server_timing(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Server-Timing": "cache;desc=hit, varnish;desc=hit_hit"}
        )

        self.assertIn("Varnish", detected_names)


    def test_detects_akamai_bot_manager_from_vendor_cookie(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"_abck": "example-value"}
        )

        self.assertIn("Akamai Bot Manager", detected_names)


    def test_cloud_google_and_cache_words_do_not_detect_removed_cdn_tools(self) -> None:
        detected_from_cloud = self.get_detected_names(
            headers={"X-Powered-By": "Cloud"}
        )
        detected_from_google = self.get_detected_names(
            headers={"Via": "google"}
        )
        detected_from_cache = self.get_detected_names(
            headers={"X-Served-By": "cache-abc123"}
        )

        self.assertNotIn("Elementor Cloud", detected_from_cloud)
        self.assertNotIn("Google Cloud CDN", detected_from_google)
        self.assertNotIn("Fastly", detected_from_cache)


    def test_payment_card_words_are_not_reported_as_technologies(self) -> None:
        detected_names = self.get_detected_names(
            html="shopping-cart visa mastercard american express Apple Pay Google Pay Afterpay"
        )

        self.assertNotIn("Cart Functionality", detected_names)
        self.assertNotIn("Visa", detected_names)
        self.assertNotIn("Mastercard", detected_names)
        self.assertNotIn("American Express", detected_names)
        self.assertNotIn("Apple Pay", detected_names)
        self.assertNotIn("Google Pay", detected_names)
        self.assertNotIn("Afterpay", detected_names)


    def test_removed_false_positive_rules_are_not_loaded(self) -> None:
        rules = load_technology_rules(RULES_PATH)
        loaded_technology_names = {
            rule.name
            for rule in rules
        }

        removed_technology_names = [
            "Adally",
            "Ametys",
            "AudioEye",
            "Backdrop",
            "Bun",
            "Cloudinary",
            "Contentful",
            "ECharts",
            "Facebook Chat Plugin",
            "Flask",
            "hCaptcha",
            "Laravel",
            "Plausible Analytics",
            "Vercel",
            "WordPress Multisite",
            "Zendesk",
            "Google Font API",
            "WordPress Block Editor",
            "WordPress Site Editor",
            "Next.js Page Router SSG",
            "Next.js Page Router SSR",
        ]

        for technology_name in removed_technology_names:
            self.assertNotIn(technology_name, loaded_technology_names)


    def test_social_links_do_not_detect_facebook_chat_plugin(self) -> None:
        detected_names = self.get_detected_names(
            html='<a href="https://facebook.com/example-store">Facebook</a>'
        )

        self.assertNotIn("Facebook Chat Plugin", detected_names)


    def test_components_word_does_not_detect_joomla(self) -> None:
        detected_names = self.get_detected_names(
            html="<div>components</div>"
        )

        self.assertNotIn("Joomla", detected_names)


    def test_mage_inside_image_text_does_not_detect_magento(self) -> None:
        detected_names = self.get_detected_names(
            html='<div class="image-gallery image-large"></div>'
        )

        self.assertNotIn("Magento", detected_names)


    def test_contentful_paint_text_does_not_detect_contentful(self) -> None:
        detected_names = self.get_detected_names(
            html="<script>performance.mark('first-contentful-paint')</script>"
        )

        self.assertNotIn("Contentful", detected_names)


    def test_googlesyndication_does_not_detect_esyndicat(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>'
        )

        self.assertNotIn("eSyndiCat", detected_names)


    def test_zendesk_like_function_name_does_not_detect_zendesk(self) -> None:
        javascript_assets = [
            JavaScriptAsset(
                url="https://example.com/assets/vendor.min.js",
                status_code=200,
                content_type="application/javascript",
                content="function zE(){ return 'local helper inside bundled code'; }",
                error=None,
            )
        ]

        detected_names = self.get_detected_names(
            html='<script src="/assets/vendor.min.js"></script>',
            javascript_assets=javascript_assets,
        )

        self.assertNotIn("Zendesk", detected_names)


    def test_next_static_path_does_not_detect_vercel(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/_next/static/chunks/main.js"></script>'
        )

        self.assertNotIn("Vercel", detected_names)


    def test_wp_content_uploads_does_not_detect_wordpress_multisite(self) -> None:
        detected_names = self.get_detected_names(
            html='<img src="/wp-content/uploads/example.jpg">'
        )

        self.assertNotIn("WordPress Multisite", detected_names)


    def test_generic_jsdelivr_url_does_not_detect_chart_libraries(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="https://cdn.jsdelivr.net/example-library.js"></script>'
        )

        self.assertNotIn("Chart.js", detected_names)
        self.assertNotIn("ECharts", detected_names)


    def test_api_js_alone_does_not_detect_hcaptcha(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/assets/api.js"></script>'
        )

        self.assertNotIn("hCaptcha", detected_names)


    def test_google_option_does_not_detect_google_fonts_or_maps(self) -> None:
        javascript_assets = [
            JavaScriptAsset(
                url="https://example.com/assets/app.js",
                status_code=200,
                content_type="application/javascript",
                content="const options = { google: true, GoogleMap: true };",
                error=None,
            )
        ]

        detected_names = self.get_detected_names(
            html='<script src="/assets/app.js"></script>',
            javascript_assets=javascript_assets,
        )

        self.assertNotIn("Google Fonts", detected_names)
        self.assertNotIn("Google Maps", detected_names)


    def test_googleapis_url_does_not_detect_google_cloud(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>'
        )

        self.assertNotIn("Google Cloud", detected_names)


    def test_leaflet_globals_do_not_detect_leaflet_without_asset_evidence(self) -> None:
        javascript_assets = [
            JavaScriptAsset(
                url="https://example.com/assets/map-bundle.js",
                status_code=200,
                content_type="application/javascript",
                content="var L = {}; L.map = function () {}; L.version = 'test';",
                error=None,
            )
        ]

        detected_names = self.get_detected_names(
            html='<script src="/assets/map-bundle.js"></script>',
            javascript_assets=javascript_assets,
        )

        self.assertNotIn("Leaflet", detected_names)


    def test_tracking_js_alone_does_not_detect_livechat(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/assets/tracking.js"></script>'
        )

        self.assertNotIn("LiveChat", detected_names)


    def test_amazonaws_asset_does_not_detect_aws(self) -> None:
        javascript_assets = [
            JavaScriptAsset(
                url="https://example.com/assets/app.js",
                status_code=200,
                content_type="application/javascript",
                content="const imageUrl = 'https://cdn.example.amazonaws.com/banner.jpg';",
                error=None,
            )
        ]

        detected_names = self.get_detected_names(
            html='<script src="https://cdn.example.amazonaws.com/assets/app.js"></script>',
            javascript_assets=javascript_assets,
        )

        self.assertNotIn("Amazon Web Services", detected_names)


    def test_whatsapp_social_link_does_not_detect_whatsapp_business_chat(self) -> None:
        detected_names = self.get_detected_names(
            html='<a href="https://wa.me/40123456789">WhatsApp</a>'
        )

        self.assertNotIn("WhatsApp Business Chat", detected_names)


    def test_akamai_grn_header_detects_akamai(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Akamai-GRN": "0.12345678.1234567890.abcdef"}
        )

        self.assertIn("Akamai", detected_names)
        self.assertNotIn("Akamai Bot Manager", detected_names)
        self.assertNotIn("Akamai Web Application Protector", detected_names)


    def test_akamai_server_timing_header_detects_akamai(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Server-Timing": 'ak_p; desc="123456_7890_123456"'}
        )

        self.assertIn("Akamai", detected_names)


    def test_akamai_cookie_prefix_detects_akamai(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"akacd_myAIDA_App_Testing": "example-value"}
        )

        self.assertIn("Akamai", detected_names)


    def test_akamai_cookie_signature_requires_prefix(self) -> None:
        detected_names = self.get_detected_names(
            cookies={"example_akacd_myAIDA_App_Testing": "example-value"}
        )

        self.assertNotIn("Akamai", detected_names)


    def test_akamai_server_header_detects_akamai(self) -> None:
        detected_names = self.get_detected_names(
            headers={"Server": "AkamaiGHost"}
        )

        self.assertIn("Akamai", detected_names)


    def test_generic_security_headers_do_not_detect_technologies(self) -> None:
        detected_names = self.get_detected_names(
            headers={
                "Strict-Transport-Security": "max-age=31536000",
                "X-Content-Type-Options": "nosniff",
                "Permissions-Policy": "geolocation=()",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            }
        )

        self.assertEqual([], detected_names)


    def test_empty_fetch_error_inputs_do_not_invent_technologies(self) -> None:
        detected_names = self.get_detected_names(
            html="",
            headers={},
            cookies={},
        )

        self.assertEqual([], detected_names)


    def test_detects_adobe_experience_manager_from_clientlibs(self) -> None:
        detected_names = self.get_detected_names(
            html='<script src="/etc.clientlibs/example/clientlib-site.min.js"></script>'
        )

        self.assertIn("Adobe Experience Manager", detected_names)


    def test_detects_adobe_experience_manager_from_content_dam(self) -> None:
        detected_names = self.get_detected_names(
            html='<img src="/content/dam/example/hero.jpg">'
        )

        self.assertIn("Adobe Experience Manager", detected_names)


    def test_adobe_experience_manager_weak_header_alone_does_not_detect(self) -> None:
        detected_names = self.get_detected_names(
            headers={"X-PR-Test": "adobecqms2"}
        )

        self.assertNotIn("Adobe Experience Manager", detected_names)


    def test_cleaned_valid_technologies_have_expected_categories(self) -> None:
        rules = load_technology_rules(RULES_PATH)
        categories_by_name = {
            rule.name: rule.category
            for rule in rules
        }

        expected_categories = {
            "Contact Form 7": "Forms",
            "WPForms": "Forms",
            "Gravity Forms": "Forms",
            "WPML": "Translation / Multilingual",
            "Raygun": "Monitoring / Error Tracking",
            "Trustpilot": "Reviews / Social Proof",
            "Partytown": "JavaScript Performance",
            "core-js": "JavaScript Library",
            "Modernizr": "JavaScript Library",
            "Beaver Builder": "Page Builder",
            "Ahrefs": "SEO / Verification",
            "All in One SEO": "SEO",
            "Cloudflare Bot Management": "Security / Bot Management",
            "FancyBox": "JavaScript Library / Lightbox",
            "MonsterInsights": "Analytics",
            "OWL Carousel": "JavaScript Library / Carousel",
            "jQuery UI": "JavaScript Library / UI Library",
            "Akamai": "CDN / Edge",
            "Adobe Experience Manager": "CMS",
        }

        for technology_name, expected_category in expected_categories.items():
            self.assertEqual(categories_by_name[technology_name], expected_category)


if __name__ == "__main__":
    unittest.main()
