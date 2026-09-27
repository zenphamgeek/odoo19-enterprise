from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestInsilosWebsiteRoutes(HttpCase):
    def test_public_pages(self):
        for route in (
            "/",
            "/platform",
            "/solutions",
            "/industries",
            "/industry",
            "/resources",
            "/pricing",
            "/about",
            "/request-demo",
            "/thank-you",
            "/media-credits",
        ):
            response = self.url_open(route)
            self.assertEqual(response.status_code, 200, f"Route failed: {route}")

    def test_solution_routes(self):
        canonical_solutions = (
            "/solutions/vertical-idp",
            "/solutions/enterprise-knowledge-graph",
            "/solutions/trade-compliance",
            "/solutions/field-service-intelligence",
            "/solutions/asset-reliability",
            "/solutions/logistics-control-tower",
            "/solutions/process-optimization",
            "/solutions/operations-assistant",
        )
        for route in canonical_solutions:
            response = self.url_open(route)
            self.assertEqual(response.status_code, 200, f"Solution route failed: {route}")

        aliases = (
            ("/solutions/autonomous-trade-compliance", "/solutions/trade-compliance"),
            ("/solutions/fsm", "/solutions/field-service-intelligence"),
            ("/solutions/logistics", "/solutions/logistics-control-tower"),
        )
        for alias_route, target in aliases:
            response = self.url_open(alias_route)
            self.assertEqual(response.status_code, 200, f"Alias route failed: {alias_route}")
            self.assertTrue(response.url.endswith(target), f"Expected redirect to {target}, got {response.url}")

    def test_industry_routes_and_brochures(self):
        for route in (
            "/industries/fsm",
            "/industries/logistics",
            "/industries/energy",
            "/industries/pharma",
        ):
            response = self.url_open(route)
            self.assertEqual(response.status_code, 200, f"Industry route failed: {route}")

        # Brochure download
        response = self.url_open("/industries/logistics/brochure")
        self.assertEqual(response.status_code, 200, "Logistics brochure failed")
        self.assertEqual(response.headers.get("Content-Type"), "application/pdf")
        self.assertGreater(len(response.content), 1000000, "Brochure PDF file size too small")

    def test_resource_articles(self):
        for route in (
            "/resources/operational-ai",
            "/resources/industrial-ai-agents",
            "/resources/governed-ai-pharma",
            "/resources/vertical-idp-logistics-roi",
            "/resources/trade-compliance-handbook",
        ):
            response = self.url_open(route)
            self.assertEqual(response.status_code, 200, f"Resource route failed: {route}")

        # Resource alias
        response = self.url_open("/resources/predictive-maintenance-whitepaper")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.url.endswith("/resources/operational-ai"))

    def test_pages_do_not_leak_default_branding(self):
        """`<title>` không được mang tên website mặc định của upstream."""
        self.assertEqual(self.env.ref("base.default_website").name, "Insilos")
        for route in ("/", "/platform", "/about", "/pricing", "/solutions"):
            html = self.url_open(route).text
            self.assertNotIn("My Website", html, route)

