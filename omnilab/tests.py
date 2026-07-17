import json
import re
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import TestCase

from .views import (
    HOMEPAGE_FAQS,
    PRODUCTION_BASE_URL,
    PUBLIC_CANONICAL_URLS,
    REACTION_API_BASE_URL,
    REACTION_MODEL,
)


class HomepageFaqTests(TestCase):
    def setUp(self):
        self.response = self.client.get("/")

    def test_faq_content_is_visible_on_homepage(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(len(HOMEPAGE_FAQS), 5)

        for faq in HOMEPAGE_FAQS:
            self.assertContains(self.response, faq["question"])
            self.assertContains(self.response, faq["answer"])

    def test_faq_schema_matches_visible_content(self):
        html = self.response.content.decode()
        schema_match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html,
            re.DOTALL,
        )

        self.assertIsNotNone(schema_match)
        schema = json.loads(schema_match.group(1))
        self.assertEqual(schema["@context"], "https://schema.org")
        self.assertEqual(schema["@type"], "FAQPage")
        self.assertEqual(len(schema["mainEntity"]), len(HOMEPAGE_FAQS))

        for faq, entity in zip(HOMEPAGE_FAQS, schema["mainEntity"]):
            self.assertEqual(entity["@type"], "Question")
            self.assertEqual(entity["name"], faq["question"])
            self.assertEqual(entity["acceptedAnswer"]["@type"], "Answer")
            self.assertEqual(entity["acceptedAnswer"]["text"], faq["answer"])


class SearchDiscoveryTests(TestCase):
    def test_homepage_description_states_audience_action_and_boundary(self):
        response = self.client.get("/")

        self.assertContains(
            response,
            (
                '<meta name="description" content="Explore predicted reactions '
                "in a virtual lab built for chemistry students. OmniLab is "
                "educational and doesn't replace physical lab procedures.\">"
            ),
            html=True,
        )

    def test_public_pages_use_production_canonical_urls(self):
        routes = {
            "/": "index",
            "/pricing/": "pricing",
            "/privacy/": "privacy",
            "/terms/": "terms",
        }

        for path, page_name in routes.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    f'<link rel="canonical" href="{PUBLIC_CANONICAL_URLS[page_name]}">',
                    html=True,
                )

    def test_robots_txt_points_crawlers_to_sitemap(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "Allow: /")
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /ai_insights/")
        self.assertContains(
            response,
            f"Sitemap: {PRODUCTION_BASE_URL}/sitemap.xml",
        )

    def test_sitemap_contains_each_public_canonical_once(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/xml"))
        root = ET.fromstring(response.content)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [
            node.text for node in root.findall("sitemap:url/sitemap:loc", namespace)
        ]
        self.assertEqual(locations, list(PUBLIC_CANONICAL_URLS.values()))

    def test_homepage_has_factual_software_application_schema(self):
        response = self.client.get("/")
        html = response.content.decode()
        schemas = [
            json.loads(match)
            for match in re.findall(
                r'<script type="application/ld\+json">(.*?)</script>',
                html,
                re.DOTALL,
            )
        ]
        software_schema = next(
            schema
            for schema in schemas
            if schema.get("@type") == "SoftwareApplication"
        )

        self.assertEqual(software_schema["name"], "OmniLab")
        self.assertEqual(software_schema["url"], PUBLIC_CANONICAL_URLS["index"])
        self.assertEqual(
            software_schema["applicationCategory"],
            "EducationalApplication",
        )
        self.assertEqual(software_schema["operatingSystem"], "Any")
        self.assertEqual(len(software_schema["featureList"]), 3)
        self.assertNotIn("offers", software_schema)
        self.assertNotIn("aggregateRating", software_schema)
        self.assertNotIn("publisher", software_schema)
        self.assertNotIn("author", software_schema)


class AnalyticsInstrumentationTests(TestCase):
    def test_homepage_uses_privacy_limited_posthog_configuration(self):
        response = self.client.get("/")

        for setting in (
            "autocapture: false",
            "capture_pageview: false",
            "capture_pageleave: false",
            "capture_performance: false",
            "disable_session_recording: true",
        ):
            with self.subTest(setting=setting):
                self.assertContains(response, setting)

        self.assertContains(
            response,
            '<script type="module" src="/static/js/root/main.js"></script>',
            html=True,
        )

    def test_lab_setup_event_contains_only_coarse_setup_properties(self):
        source = "\n".join(
            (
                (
                    settings.BASE_DIR
                    / "static/ts/interactions/interactions.ts"
                ).read_text(),
                (
                    settings.BASE_DIR / "static/ts/userInterface/ui.ts"
                ).read_text(),
            )
        )
        setup_captures = re.findall(
            r"captureLabSetupStarted\(\{(.*?)\}\);",
            source,
            re.DOTALL,
        )

        self.assertEqual(len(setup_captures), 2)
        for properties in setup_captures:
            self.assertIn("vessel", properties)
            self.assertIn("burner_active", properties)

            for private_value in (
                "selectedChemicals",
                "chemical",
                "query",
                "reaction",
                "formData",
            ):
                with self.subTest(private_value=private_value):
                    self.assertNotIn(private_value, properties)

    def test_lab_setup_event_is_captured_once_per_page(self):
        analytics = (
            settings.BASE_DIR / "static/ts/analytics/analytics.ts"
        ).read_text()

        self.assertIn("if (labSetupCaptured) return;", analytics)
        self.assertIn("capture('lab_setup_started', properties);", analytics)

    def test_runtime_entry_uses_browser_resolvable_module_imports(self):
        entry = (settings.BASE_DIR / "static/ts/root/main.ts").read_text()

        for module_path in (
            "../configuration/config.js",
            "../userInterface/ui.js",
            "../rendering/render.js",
            "../interactions/interactions.js",
            "../analytics/analytics.js",
        ):
            with self.subTest(module_path=module_path):
                self.assertIn(f"from '{module_path}'", entry)

    def test_reaction_events_exclude_private_lab_content(self):
        source = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        captures = re.findall(
            r"capture\('reaction_analysis_(?:started|completed|failed)', \{"
            r"(.*?)\}\);",
            source,
            re.DOTALL,
        )

        self.assertEqual(len(captures), 4)
        for properties in captures:
            property_names = set(
                re.findall(r"^\s*([a-zA-Z_]+):", properties, re.MULTILINE)
            )
            for private_value in (
                "selectedChemicals",
                "query",
                "equation",
                "explanation",
                "safety",
                "formData",
            ):
                with self.subTest(private_value=private_value):
                    self.assertNotIn(private_value, property_names)


class LabJourneyRepairTests(TestCase):
    def test_catalog_restores_the_repository_evidenced_sodium_input(self):
        catalog = json.loads(
            (settings.BASE_DIR / "static/js/chemicaldata.json").read_text()
        )

        self.assertEqual(
            catalog,
            [{"id": "Na", "name": "Sodium", "color": "#e09f25"}],
        )

    def test_homepage_and_runtime_use_the_same_canvas_identifier(self):
        response = self.client.get("/")
        runtime = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()

        self.assertContains(
            response,
            '<canvas id="lab-canvas"></canvas>',
            html=True,
        )
        self.assertIn("getElementById('lab-canvas')", runtime)

    def test_runtime_initializes_catalog_canvas_and_drop_path(self):
        entry = (settings.BASE_DIR / "static/ts/root/main.ts").read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        renderer = (
            settings.BASE_DIR / "static/ts/rendering/render.ts"
        ).read_text()

        for expected in (
            "fetch(jsonUrl)",
            "ui.resizeCanvas()",
            "requestAnimationFrame(engineLoop)",
            "addEventListener('drop'",
        ):
            self.assertIn(expected, entry)
        self.assertIn("selectedChemicals: updatedChemicals", interactions)
        self.assertIn("updatedChemicals.join(' + ')", interactions)
        self.assertIn("updatedState.currentVessel", renderer)
        self.assertIn("updatedState.burnerActive", renderer)

    def test_instruction_text_uses_contrast_token_without_opacity(self):
        response = self.client.get("/")
        css = (settings.BASE_DIR / "static/css/style.css").read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertContains(response, "lab-instruction")
        self.assertIn(".lab-instruction", css)
        self.assertIn("color: var(--muted-text);", css)
        self.assertNotIn('style="opacity: 0.6;"', interactions)

    @patch("omnilab.views.get_reaction_client")
    def test_reaction_endpoint_uses_current_provider_defaults(self, get_client):
        create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps(
                                {
                                    "effect": "none",
                                    "equation": "Na(s) -> Na(s)",
                                    "explanation": "No second reagent was selected.",
                                    "safety": (
                                        "Wear eye protection. | Keep sodium dry. | "
                                        "Use trained supervision."
                                    ),
                                }
                            )
                        )
                    )
                ]
            )
        )
        get_client.return_value = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        response = self.client.post("/ai_insights/", {"query": "Na"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(
            REACTION_API_BASE_URL,
            "https://models.github.ai/inference",
        )
        self.assertEqual(REACTION_MODEL, "openai/gpt-4o-mini")
        self.assertEqual(create.call_args.kwargs["model"], REACTION_MODEL)
        self.assertEqual(
            create.call_args.kwargs["response_format"],
            {"type": "json_object"},
        )
