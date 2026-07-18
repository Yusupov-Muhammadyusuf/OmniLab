import json
import re
import struct
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from .views import (
    GUIDED_EXPERIMENT_PAGES,
    HOMEPAGE_FAQS,
    PRODUCTION_BASE_URL,
    PUBLIC_CANONICAL_URLS,
    REACTION_API_BASE_URL,
    REACTION_MODEL,
    SODIUM_CHLORINE_DEMO,
    SODIUM_CHLORINE_DEMO_URL,
    SOCIAL_PREVIEW_ALT,
    SOCIAL_PREVIEW_URL,
    equation_uses_only_selected_reactants,
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


class HomepageGuideLinksTests(TestCase):
    guide_links = {
        "/guides/sodium-and-chlorine-reaction/": (
            "What happens when sodium reacts with chlorine?"
        ),
        "/guides/sodium-and-chlorine-formula/": (
            "What formula forms from sodium and chlorine?"
        ),
        "/guides/sodium-and-chlorine-ionic-bond/": (
            "Why do sodium and chlorine form an ionic bond?"
        ),
    }

    def test_homepage_links_all_three_guides_with_descriptive_text(self):
        response = self.client.get("/")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Study the supported pair")
        self.assertEqual(html.count('class="guide-library-link"'), 3)
        for path, title in self.guide_links.items():
            with self.subTest(path=path):
                self.assertContains(response, f'href="{path}"')
                self.assertContains(response, title)

    def test_guide_links_are_secondary_to_the_single_analyze_action(self):
        response = self.client.get("/")
        html = response.content.decode()

        self.assertEqual(html.count('class="btn action-btn-primary'), 1)
        self.assertNotContains(response, 'class="guide-primary"')
        self.assertNotContains(response, 'class="btn guide-library-link"')

    def test_demo_stays_focused_on_the_prepared_reaction(self):
        response = self.client.get("/demo/sodium-chlorine/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Study the supported pair")
        self.assertNotContains(response, 'class="guide-library-link"')


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


class GuidedExperimentPageTests(TestCase):
    routes = {
        "/guides/sodium-and-chlorine-reaction/": "reaction",
        "/guides/sodium-and-chlorine-formula/": "formula",
        "/guides/sodium-and-chlorine-ionic-bond/": "ionic-bond",
    }

    def test_exactly_three_guides_answer_distinct_student_questions(self):
        self.assertEqual(len(GUIDED_EXPERIMENT_PAGES), 3)

        titles = set()
        for path, guide_key in self.routes.items():
            with self.subTest(path=path):
                guide = GUIDED_EXPERIMENT_PAGES[guide_key]
                response = self.client.get(path)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f"<h1 id=\"guide-heading\">{guide['title']}</h1>", html=True)
                self.assertContains(response, guide["direct_answer"])
                titles.add(guide["title"])

        self.assertEqual(len(titles), 3)

    def test_each_guide_has_one_primary_path_to_the_prepared_lab(self):
        for path, guide_key in self.routes.items():
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                visit_source = GUIDED_EXPERIMENT_PAGES[guide_key]["visit_source"]

                self.assertEqual(html.count('class="guide-primary"'), 1)
                self.assertEqual(
                    html.count(
                        'href="/demo/sodium-chlorine/'
                        f'?source={visit_source}"'
                    ),
                    1,
                )

    def test_each_guide_uses_one_fixed_privacy_safe_analytics_source(self):
        expected_sources = {
            "reaction": "guide_reaction",
            "formula": "guide_formula",
            "ionic-bond": "guide_ionic_bond",
        }

        self.assertEqual(
            {
                key: guide["visit_source"]
                for key, guide in GUIDED_EXPERIMENT_PAGES.items()
            },
            expected_sources,
        )
        for path, guide_key in self.routes.items():
            with self.subTest(path=path):
                visit_source = expected_sources[guide_key]
                response = self.client.get(f"{path}?source=arbitrary-private-value")
                html = response.content.decode()

                self.assertContains(
                    response,
                    f'window.guideVisitSource = "{visit_source}";',
                )
                self.assertContains(
                    response,
                    '<script type="module" src="/static/js/root/guide.js"></script>',
                    html=True,
                )
                self.assertNotContains(response, "arbitrary-private-value")

    def test_guides_use_privacy_limited_product_analytics(self):
        for path in self.routes:
            with self.subTest(path=path):
                response = self.client.get(path)

                for setting in (
                    "autocapture: false",
                    "capture_pageview: false",
                    "capture_pageleave: false",
                    "capture_performance: false",
                    "disable_session_recording: true",
                ):
                    self.assertContains(response, setting)

    def test_guides_keep_the_educational_and_safety_boundaries_visible(self):
        for path in self.routes:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertContains(
                    response,
                    "It can be incomplete or wrong and does not replace "
                    "instructor supervision, trusted references, or "
                    "physical-lab safety procedures.",
                )
                self.assertContains(
                    response,
                    "Do not attempt the sodium and chlorine reaction outside "
                    "a properly equipped, supervised laboratory.",
                )

    def test_guides_have_unique_canonicals_metadata_and_learning_schema(self):
        canonical_urls = set()
        for path, guide_key in self.routes.items():
            with self.subTest(path=path):
                guide = GUIDED_EXPERIMENT_PAGES[guide_key]
                response = self.client.get(path)
                html = response.content.decode()
                canonical = PUBLIC_CANONICAL_URLS[guide["canonical_key"]]

                self.assertContains(
                    response,
                    f'<link rel="canonical" href="{canonical}">',
                    html=True,
                )
                self.assertContains(
                    response,
                    f'<meta name="description" content="{guide["description"]}">',
                    html=True,
                )
                schema_match = re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    html,
                    re.DOTALL,
                )
                self.assertIsNotNone(schema_match)
                schema = json.loads(schema_match.group(1))
                self.assertEqual(schema["@type"], "LearningResource")
                self.assertEqual(schema["url"], canonical)
                canonical_urls.add(canonical)

        self.assertEqual(len(canonical_urls), 3)

    def test_sitemap_includes_all_three_guides(self):
        sitemap = self.client.get("/sitemap.xml").content.decode()

        for guide in GUIDED_EXPERIMENT_PAGES.values():
            canonical = PUBLIC_CANONICAL_URLS[guide["canonical_key"]]
            with self.subTest(canonical=canonical):
                self.assertEqual(sitemap.count(canonical), 1)


class SocialPreviewTests(TestCase):
    def setUp(self):
        self.response = self.client.get("/")

    def test_homepage_exposes_absolute_open_graph_metadata(self):
        tags = (
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="OmniLab">',
            (
                '<meta property="og:title" content="OmniLab - Test chemical '
                'reactions in a virtual lab">'
            ),
            (
                '<meta property="og:description" content="Explore predicted '
                "reactions in a virtual lab built for chemistry students. "
                "OmniLab is educational and doesn't replace physical lab "
                'procedures.">'
            ),
            f'<meta property="og:url" content="{PUBLIC_CANONICAL_URLS["index"]}">',
            f'<meta property="og:image" content="{SOCIAL_PREVIEW_URL}">',
            f'<meta property="og:image:secure_url" content="{SOCIAL_PREVIEW_URL}">',
            '<meta property="og:image:type" content="image/png">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{SOCIAL_PREVIEW_ALT}">',
        )

        for tag in tags:
            with self.subTest(tag=tag):
                self.assertContains(self.response, tag, html=True)

        self.assertTrue(SOCIAL_PREVIEW_URL.startswith(f"{PRODUCTION_BASE_URL}/"))

    def test_homepage_exposes_large_twitter_card_metadata(self):
        tags = (
            '<meta name="twitter:card" content="summary_large_image">',
            (
                '<meta name="twitter:title" content="OmniLab - Test chemical '
                'reactions in a virtual lab">'
            ),
            (
                '<meta name="twitter:description" content="Explore predicted '
                "reactions in a virtual lab built for chemistry students. "
                "OmniLab is educational and doesn't replace physical lab "
                'procedures.">'
            ),
            f'<meta name="twitter:image" content="{SOCIAL_PREVIEW_URL}">',
            f'<meta name="twitter:image:alt" content="{SOCIAL_PREVIEW_ALT}">',
        )

        for tag in tags:
            with self.subTest(tag=tag):
                self.assertContains(self.response, tag, html=True)

    def test_social_preview_asset_is_1200_by_630_and_compressed(self):
        asset_path = (
            settings.BASE_DIR / "static/images/omnilab-social-preview.png"
        )
        image_bytes = asset_path.read_bytes()

        self.assertEqual(image_bytes[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", image_bytes[16:24]), (1200, 630))
        self.assertLess(len(image_bytes), 200_000)


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

        self.assertEqual(len(captures), 6)
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

    def test_demo_entry_event_contains_only_coarse_properties(self):
        entry = (settings.BASE_DIR / "static/ts/root/main.ts").read_text()
        capture_match = re.search(
            r"capture\('reaction_demo_entered', \{(.*?)\}\);",
            entry,
            re.DOTALL,
        )

        self.assertIsNotNone(capture_match)
        properties = capture_match.group(1)
        property_names = set(
            re.findall(r"^\s*([a-zA-Z_]+):", properties, re.MULTILINE)
        )
        self.assertIn("demo_version", properties)
        self.assertIn("chemical_count", properties)
        self.assertIn("vessel", properties)
        for private_value in (
            "selectedChemicals:",
            "chemical_name",
            "query",
            "reaction",
            "equation",
            "explanation",
            "safety",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value.rstrip(":"), property_names)

    def test_student_invitation_source_is_allowlisted_for_demo_measurement(self):
        configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        entry = (settings.BASE_DIR / "static/ts/root/main.ts").read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn(
            "export type VisitSource = 'student_invite' | GuideVisitSource;",
            configuration,
        )
        for visit_source in (
            "student_invite",
            "guide_reaction",
            "guide_formula",
            "guide_ionic_bond",
        ):
            with self.subTest(visit_source=visit_source):
                self.assertIn(f"'{visit_source}'", configuration)
        self.assertIn(
            "new URLSearchParams(window.location.search).get('source')",
            configuration,
        )
        self.assertIn("if (!getReactionDemoConfig()) return null;", configuration)
        self.assertEqual(entry.count("visit_source: visitSource"), 1)

        completed_capture = interactions.split(
            "capture('reaction_analysis_completed', {", 1
        )[1].split("});", 1)[0]
        self.assertEqual(completed_capture.count("visit_source: visitSource"), 1)
        for private_value in (
            "selectedChemicals:",
            "chemical_name",
            "email",
            "query:",
            "equation",
            "explanation",
            "safety",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value, completed_capture)

    def test_guide_entry_event_contains_only_the_fixed_source(self):
        entry = (settings.BASE_DIR / "static/ts/root/guide.ts").read_text()
        capture_match = re.search(
            r"capture\('chemistry_guide_entered', \{(.*?)\}\);",
            entry,
            re.DOTALL,
        )

        self.assertIsNotNone(capture_match)
        property_names = set(
            re.findall(
                r"(?:^|\s)([a-zA-Z_]+):",
                capture_match.group(1),
            )
        )
        self.assertEqual(property_names, {"visit_source"})
        self.assertIn("getGuideVisitSource", entry)
        for private_value in (
            "name",
            "email",
            "chemical",
            "query",
            "equation",
            "explanation",
            "safety",
            "location",
            "href",
            "pathname",
            "title",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value, capture_match.group(1))


class ShareableReactionDemoTests(TestCase):
    def test_demo_route_prepares_supported_inputs_and_beaker(self):
        response = self.client.get("/demo/sodium-chlorine/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sodium and chlorine, ready to analyze")
        self.assertContains(response, "Na + Cl2")
        self.assertIn(
            '<div class="apparatus-option-card selected" id="opt-beaker">',
            response.content.decode(),
        )
        self.assertContains(
            response,
            f"window.reactionDemo = {json.dumps(SODIUM_CHLORINE_DEMO)};",
        )

    def test_demo_is_shareable_without_becoming_a_search_page(self):
        response = self.client.get("/demo/sodium-chlorine/")

        self.assertContains(
            response,
            f'<link rel="canonical" href="{PUBLIC_CANONICAL_URLS["index"]}">',
            html=True,
        )
        self.assertContains(
            response,
            '<meta name="robots" content="noindex, follow">',
            html=True,
        )
        self.assertContains(
            response,
            f'<meta property="og:url" content="{SODIUM_CHLORINE_DEMO_URL}">',
            html=True,
        )
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn(SODIUM_CHLORINE_DEMO_URL, sitemap)

    def test_homepage_keeps_its_empty_unscripted_start(self):
        response = self.client.get("/")

        self.assertContains(
            response,
            "<title>OmniLab - Laboratory Experiments Assistant</title>",
            html=True,
        )
        self.assertContains(response, "Test chemical reactions in a virtual lab")
        self.assertContains(response, "Empty Vessel")
        self.assertContains(response, "window.reactionDemo = null;")
        self.assertContains(
            response,
            "Start with <strong>Sodium and Chlorine</strong>, "
            "OmniLab's supported pair. Add both from Chemicals.",
            html=True,
        )
        self.assertContains(
            response,
            '<a class="lab-demo-link" href="/demo/sodium-chlorine/">'
            ' Open the prepared demo '
            '<i class="bi bi-arrow-right" aria-hidden="true"></i>'
            '</a>',
            html=True,
        )
        self.assertNotContains(
            response,
            '<meta name="robots" content="noindex, follow">',
            html=True,
        )
        self.assertNotContains(response, 'name="robots"')

    def test_default_instruction_keeps_demo_link_after_normal_lab_reset(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        default_instruction = interactions.split(
            "const DEFAULT_REACTION_INSTRUCTION =", 1
        )[1].split("const DEMO_REACTION_INSTRUCTION =", 1)[0]

        self.assertIn("Sodium and Chlorine", default_instruction)
        self.assertIn('href="/demo/sodium-chlorine/"', default_instruction)
        self.assertNotIn("window.reactionDemo", default_instruction)

    def test_demo_uses_isolated_storage_and_never_auto_submits(self):
        configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        entry = (settings.BASE_DIR / "static/ts/root/main.ts").read_text()

        self.assertIn("reactionDemo:${reactionDemo.id}:${baseKey}", configuration)
        for key in ("savedChemicals", "savedLiquidColor", "savedReaction"):
            with self.subTest(key=key):
                self.assertIn(f"config.getLabStorageKey('{key}')", interactions)
        self.assertIn(
            "analyzeBtn.addEventListener('click', interactions.fireAIAnalysis)",
            entry,
        )
        demo_initialization = interactions.split(
            'document.addEventListener("DOMContentLoaded", () => {', 1
        )[1]
        self.assertNotIn("fireAIAnalysis", demo_initialization)


class PredictionInputClarityTests(TestCase):
    def test_normal_lab_and_demo_explain_prediction_inputs_before_analysis(self):
        for path in ("/", "/demo/sodium-chlorine/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.content.decode()

                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "Selected chemicals only. Vessel and burner choices are "
                    "visual setup aids.",
                )
                self.assertContains(
                    response,
                    'aria-describedby="prediction-input-note"',
                )
                self.assertLess(
                    html.index('id="prediction-input-note"'),
                    html.index('id="btn-fire-analysis"'),
                )


class SupportedSetupAnalysisStateTests(TestCase):
    def test_normal_lab_starts_disabled_with_missing_input_guidance(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Sodium and Chlorine to enable analysis.")
        self.assertContains(
            response,
            'id="btn-fire-analysis" aria-describedby="prediction-input-note" disabled',
        )

    def test_prepared_demo_starts_ready_to_analyze(self):
        response = self.client.get("/demo/sodium-chlorine/")
        html = response.content.decode()
        button = html.split('id="btn-fire-analysis"', 1)[1].split(">", 1)[0]

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Ready to analyze the supported Sodium and Chlorine pair.",
        )
        self.assertNotIn("disabled", button)

    def test_browser_uses_one_exact_order_independent_support_rule(self):
        configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        support_rule = configuration.split(
            "export function isSupportedReactionSetup", 1
        )[1].split("\n}\n", 1)[0]

        self.assertIn("new Set(['Na', 'Cl2'])", configuration)
        self.assertIn(
            "selectedChemicals.length === SUPPORTED_REACTION_CHEMICALS.size",
            support_rule,
        )
        self.assertIn(
            "selectedChemicals.every(chemical => "
            "SUPPORTED_REACTION_CHEMICALS.has(chemical))",
            support_rule,
        )

    def test_disabled_setup_stops_before_analytics_and_network(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        analysis_block = interactions.split(
            "export function fireAIAnalysis(): void {", 1
        )[1].split('\n}\n\ndocument.addEventListener("DOMContentLoaded"', 1)[0]

        support_guard = analysis_block.index(
            "if (!config.isSupportedReactionSetup(state.selectedChemicals))"
        )
        capture_position = analysis_block.index(
            "capture('reaction_analysis_started'"
        )
        fetch_position = analysis_block.index("fetch('/ai_insights/'")

        self.assertLess(support_guard, capture_position)
        self.assertLess(support_guard, fetch_position)

    def test_drop_demo_reset_and_request_exit_refresh_button_state(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        drop_block = interactions.split(
            "export function drop(ev: DragEvent): void {", 1
        )[1].split("\n}\n\nexport function resetLaboratory", 1)[0]
        reset_block = interactions.split(
            "export function resetLaboratory(): void {", 1
        )[1].split("\n}\n\nfunction getCsrfToken", 1)[0]
        initialization_block = interactions.split(
            'document.addEventListener("DOMContentLoaded", () => {', 1
        )[1]

        self.assertIn("updateAnalysisAvailability()", drop_block)
        self.assertIn("selectedChemicals: []", reset_block)
        self.assertIn("setAnalysisPending(false)", reset_block)
        self.assertLess(
            reset_block.index("selectedChemicals: []"),
            reset_block.index("setAnalysisPending(false)"),
        )
        self.assertIn("updateAnalysisAvailability()", initialization_block)


@override_settings(
    OMNILAB_REACTION_RATE_LIMIT_REQUESTS=2,
    OMNILAB_REACTION_RATE_LIMIT_WINDOW_SECONDS=60,
)
class ReactionRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        payload = {
            "effect": "none",
            "equation": "2Na(s) + Cl2(g) -> 2NaCl(s)",
            "explanation": "The selected reactants form sodium chloride.",
            "safety": (
                "Wear eye protection. | Keep sodium dry. | "
                "Use trained supervision."
            ),
        }
        self.provider_create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(payload))
                    )
                ]
            )
        )
        provider = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=self.provider_create)
            )
        )
        self.client_patcher = patch(
            "omnilab.views.get_reaction_client", return_value=provider
        )
        self.client_patcher.start()

    def tearDown(self):
        self.client_patcher.stop()
        cache.clear()

    def post_reaction(
        self,
        forwarded_for="203.0.113.10",
        remote_addr="127.0.0.1",
    ):
        request_headers = {"REMOTE_ADDR": remote_addr}
        if forwarded_for is not None:
            request_headers["HTTP_X_FORWARDED_FOR"] = forwarded_for
        return self.client.post(
            "/ai_insights/", {"query": "Na + Cl2"}, **request_headers
        )

    def test_normal_reaction_request_reaches_provider(self):
        with patch("omnilab.views.time.time", return_value=1200):
            response = self.post_reaction()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.provider_create.assert_called_once()

    def test_exceeded_limit_returns_retry_guidance_without_provider_call(self):
        with patch("omnilab.views.time.time", return_value=1200):
            self.assertEqual(self.post_reaction().status_code, 200)
            self.assertEqual(self.post_reaction().status_code, 200)
            response = self.post_reaction()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["status"], "rate_limited")
        self.assertIn("Try again in 60 seconds", response.json()["message"])
        self.assertEqual(response.headers["Retry-After"], "60")
        self.assertEqual(self.provider_create.call_count, 2)

    @override_settings(OMNILAB_REACTION_RATE_LIMIT_REQUESTS=1)
    def test_reaction_request_recovers_after_window(self):
        with patch("omnilab.views.time.time", return_value=1200):
            self.assertEqual(self.post_reaction().status_code, 200)
            self.assertEqual(self.post_reaction().status_code, 429)

        with patch("omnilab.views.time.time", return_value=1260):
            response = self.post_reaction()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(self.provider_create.call_count, 2)

    @override_settings(OMNILAB_REACTION_RATE_LIMIT_REQUESTS=1)
    def test_appended_forwarded_hops_cannot_rotate_client_key(self):
        with patch("omnilab.views.time.time", return_value=1200):
            first_response = self.post_reaction(
                forwarded_for="203.0.113.10, 198.51.100.20"
            )
            blocked_response = self.post_reaction(
                forwarded_for="203.0.113.10, 192.0.2.30"
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.provider_create.assert_called_once()

    @override_settings(OMNILAB_REACTION_RATE_LIMIT_REQUESTS=1)
    def test_malformed_forwarded_address_uses_socket_fallback(self):
        with patch("omnilab.views.time.time", return_value=1200):
            first_response = self.post_reaction(
                forwarded_for="not-an-address",
                remote_addr="198.51.100.40",
            )
            blocked_response = self.post_reaction(
                forwarded_for="still-not-an-address",
                remote_addr="198.51.100.40",
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.provider_create.assert_called_once()


class ReactionCsrfProtectionTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        payload = {
            "effect": "none",
            "equation": "2Na(s) + Cl2(g) -> 2NaCl(s)",
            "explanation": "The selected reactants form sodium chloride.",
            "safety": (
                "Wear eye protection. | Keep sodium dry. | "
                "Use trained supervision."
            ),
        }
        self.provider_create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(payload))
                    )
                ]
            )
        )
        provider = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=self.provider_create)
            )
        )
        self.client_patcher = patch(
            "omnilab.views.get_reaction_client", return_value=provider
        )
        self.client_patcher.start()

    def tearDown(self):
        self.client_patcher.stop()

    def post_reaction(self, token=None, origin="https://testserver"):
        headers = {"HTTP_ORIGIN": origin}
        if token is not None:
            headers["HTTP_X_CSRFTOKEN"] = token
        return self.client.post(
            "/ai_insights/",
            {"query": "Na + Cl2"},
            secure=True,
            **headers,
        )

    def get_token(self, path="/"):
        response = self.client.get(path, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        return response.cookies["csrftoken"].value

    def test_tokenless_request_is_rejected_before_provider(self):
        response = self.post_reaction()

        self.assertEqual(response.status_code, 403)
        self.provider_create.assert_not_called()

    def test_invalid_token_is_rejected_before_provider(self):
        self.get_token()

        response = self.post_reaction("a" * 32)

        self.assertEqual(response.status_code, 403)
        self.provider_create.assert_not_called()

    def test_cross_origin_request_is_rejected_before_provider(self):
        token = self.get_token()

        response = self.post_reaction(token, origin="https://example.net")

        self.assertEqual(response.status_code, 403)
        self.provider_create.assert_not_called()

    def test_valid_homepage_token_keeps_reaction_contract(self):
        token = self.get_token()

        response = self.post_reaction(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(
            response.json()["data"]["equation"],
            "2Na(s) + Cl2(g) -> 2NaCl(s)",
        )
        self.provider_create.assert_called_once()

    def test_demo_page_sets_token_for_the_same_browser_client(self):
        token = self.get_token("/demo/sodium-chlorine/")

        response = self.post_reaction(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.provider_create.assert_called_once()

    def test_browser_client_sends_same_origin_token(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn("'X-CSRFToken': getCsrfToken()", interactions)
        self.assertIn("credentials: 'same-origin'", interactions)


class LabJourneyRepairTests(TestCase):
    def test_catalog_exposes_the_repository_evidenced_reaction_pair(self):
        catalog = json.loads(
            (settings.BASE_DIR / "static/js/chemicaldata.json").read_text()
        )

        self.assertEqual(
            catalog,
            [
                {"id": "Na", "name": "Sodium", "color": "#e09f25"},
                {"id": "Cl2", "name": "Chlorine", "color": "#89a83b"},
            ],
        )
        self.assertEqual(len({chemical["id"] for chemical in catalog}), 2)

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

    def test_browser_submits_catalog_ids_as_selected_reactants(self):
        catalog = json.loads(
            (settings.BASE_DIR / "static/js/chemicaldata.json").read_text()
        )
        menu = (
            settings.BASE_DIR / "static/ts/userInterface/ui.ts"
        ).read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertEqual(
            [(chemical["id"], chemical["name"]) for chemical in catalog],
            [("Na", "Sodium"), ("Cl2", "Chlorine")],
        )
        self.assertIn("card.setAttribute('data-name', chem.id)", menu)
        self.assertIn("state.selectedChemicals.join(' + ')", interactions)

    def test_reactant_validation_normalizes_coefficients_and_states(self):
        self.assertTrue(
            equation_uses_only_selected_reactants(
                "2Na(s) + Cl2(g) -> 2NaCl(s)", ["Na", "Cl2"]
            )
        )
        self.assertFalse(
            equation_uses_only_selected_reactants(
                "2Na(s) + 2H2O(l) -> 2NaOH(aq) + H2(g)",
                ["Na", "Cl2"],
            )
        )

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

    def test_reaction_results_keep_heading_order_and_safety_contrast(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        css = (settings.BASE_DIR / "static/css/style.css").read_text()
        render_block = interactions.split(
            "export function renderReactionResult", 1
        )[1].split("\n}\n\nfunction renderStatusMessage", 1)[0]

        self.assertNotIn("<h6", interactions)
        equation_heading = render_block.index("Chemical Equation Formula")
        analysis_heading = render_block.index("Analysis")
        safety_heading = render_block.index("Safety rules")
        self.assertLess(equation_heading, analysis_heading)
        self.assertLess(analysis_heading, safety_heading)
        self.assertIn("safety-heading", interactions)
        self.assertIn("safety-list", interactions)
        self.assertIn(".safety-heading", css)
        self.assertIn(".safety-list", css)
        self.assertIn("color: var(--text-color);", css)

    def test_reaction_results_render_provider_fields_as_text(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        render_block = interactions.split(
            "export function renderReactionResult", 1
        )[1].split("\n}\n\nfunction renderStatusMessage", 1)[0]

        self.assertIn("equation.textContent = reaction.equation", render_block)
        self.assertIn(
            "explanation.textContent = reaction.explanation", render_block
        )
        self.assertIn("document.createTextNode(point)", render_block)
        self.assertNotIn("${reaction.equation}", render_block)
        self.assertNotIn("${reaction.explanation}", render_block)
        self.assertNotIn("${reaction.safety}", render_block)

    def test_successful_result_offers_optional_content_free_feedback_email(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        css = (settings.BASE_DIR / "static/css/style.css").read_text()
        render_block = interactions.split(
            "export function renderReactionResult", 1
        )[1].split("\n}\n\nfunction renderStatusMessage", 1)[0]
        mailto_block = interactions.split(
            "function buildFeedbackMailtoUrl", 1
        )[1].split("\n}\n\nexport function renderReactionResult", 1)[0]
        status_block = interactions.split(
            "function renderStatusMessage", 1
        )[1].split("\n}\n\nexport function setupCanvasDrag", 1)[0]

        self.assertIn("reaction-feedback", render_block)
        self.assertIn("Optional feedback", render_block)
        self.assertIn("feedbackLink.href = buildFeedbackMailtoUrl()", render_block)
        self.assertIn(
            "const FEEDBACK_EMAIL_ADDRESS = 'omnilab-bk8q@mail.tin.computer'",
            interactions,
        )
        self.assertIn("'What were you trying to predict?'", interactions)
        self.assertIn("'What do you plan to do next?'", interactions)
        self.assertIn("encodeURIComponent(FEEDBACK_PROMPTS)", mailto_block)
        for private_value in (
            "selectedChemicals",
            "reaction.equation",
            "reaction.explanation",
            "reaction.safety",
        ):
            self.assertNotIn(private_value, mailto_block)
        self.assertNotIn("reaction-feedback", status_block)
        self.assertIn(".reaction-feedback-link", css)
        self.assertIn("min-height: 44px;", css)

    @patch("omnilab.views.get_reaction_client")
    def test_malicious_provider_markup_stays_data_for_safe_browser_rendering(
        self, get_client
    ):
        payload = {
            "effect": "none",
            "equation": (
                "2Na(s) + Cl2(g) -> 2NaCl(s)"
                '<img src=x onerror="window.__providerMarkupRan=true">'
            ),
            "explanation": (
                '<svg onload="window.__providerMarkupRan=true"></svg>'
                "The selected reactants form sodium chloride."
            ),
            "safety": (
                '<script>window.__providerMarkupRan=true</script>Wear goggles. | '
                '<img src=x onerror="window.__providerMarkupRan=true">Keep sodium dry. | '
                "Use trained supervision."
            ),
        }
        create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(payload))
                    )
                ]
            )
        )
        get_client.return_value = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        response = self.client.post("/ai_insights/", {"query": "Na + Cl2"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"], payload)

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
                                    "equation": "2Na(s) + Cl2(g) -> 2NaCl(s)",
                                    "explanation": "The selected reactants form sodium chloride.",
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

        response = self.client.post(
            "/ai_insights/", {"query": "Na + Cl2"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        reaction = response.json()["data"]
        self.assertTrue(
            equation_uses_only_selected_reactants(
                reaction["equation"], ["Na", "Cl2"]
            )
        )
        self.assertTrue(reaction["explanation"])
        self.assertEqual(
            len(
                [
                    rule.strip()
                    for rule in reaction["safety"].split("|")
                    if rule.strip()
                ]
            ),
            3,
        )
        self.assertEqual(
            REACTION_API_BASE_URL,
            "https://models.github.ai/inference",
        )
        self.assertEqual(REACTION_MODEL, "openai/gpt-4o-mini")
        self.assertEqual(create.call_args.kwargs["model"], REACTION_MODEL)
        self.assertIn(
            "complete set of reactants",
            create.call_args.kwargs["messages"][0]["content"],
        )
        self.assertEqual(
            create.call_args.kwargs["response_format"],
            {"type": "json_object"},
        )

    @patch("omnilab.views.get_reaction_client")
    def test_single_selected_chemical_returns_insufficient_input(self, get_client):
        response = self.client.post("/ai_insights/", {"query": "Na"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "insufficient_input")
        self.assertIn("Add at least two chemicals", response.json()["message"])
        self.assertNotIn("water", response.content.decode().lower())
        get_client.assert_not_called()

    @patch("omnilab.views.get_reaction_client")
    def test_unselected_reactant_is_not_returned_to_the_browser(self, get_client):
        create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps(
                                {
                                    "effect": "explosion",
                                    "equation": (
                                        "2Na(s) + 2H2O(l) -> "
                                        "2NaOH(aq) + H2(g)"
                                    ),
                                    "explanation": (
                                        "Water was introduced by the model."
                                    ),
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

        response = self.client.post(
            "/ai_insights/", {"query": "Na + Cl2"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "insufficient_input")
        self.assertNotIn("equation", response.content.decode().lower())

    def test_browser_renders_insufficient_input_as_an_educational_state(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn("resData.status === 'insufficient_input'", interactions)
        self.assertIn("Try a different setup", interactions)
        self.assertIn(
            "localStorage.removeItem(config.getLabStorageKey('savedReaction'))",
            interactions,
        )
        self.assertIn("stage: 'insufficient_input'", interactions)

    def test_reset_clears_saved_and_visible_reaction_state(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        reset_block = interactions.split(
            "export function resetLaboratory(): void {", 1
        )[1].split("\n}\n\nexport function fireAIAnalysis", 1)[0]

        self.assertIn(
            "localStorage.removeItem(config.getLabStorageKey('savedChemicals'))",
            reset_block,
        )
        self.assertIn(
            "localStorage.removeItem(config.getLabStorageKey('savedLiquidColor'))",
            reset_block,
        )
        self.assertIn(
            "localStorage.removeItem(config.getLabStorageKey('savedReaction'))",
            reset_block,
        )
        self.assertIn("activeAnalysisController?.abort()", reset_block)
        self.assertIn("cancelReactionEffects()", reset_block)
        self.assertIn("selectedChemicals: []", reset_block)
        self.assertIn("isBubbling: false", reset_block)
        self.assertIn("smokeParticles: []", reset_block)
        self.assertIn("explosionParticles: []", reset_block)
        self.assertIn("panel.innerHTML = DEFAULT_REACTION_INSTRUCTION", reset_block)

    def test_reset_cancels_stale_analysis_and_thermal_effects(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        rendering = (
            settings.BASE_DIR / "static/ts/rendering/render.ts"
        ).read_text()

        self.assertIn("signal: requestController.signal", interactions)
        self.assertIn(
            "analysisRunId !== currentAnalysisRunId",
            interactions,
        )
        self.assertIn("export function cancelReactionEffects()", rendering)
        self.assertIn("clearInterval(thermalBlastTimer)", rendering)

    def test_browser_allows_only_one_in_flight_analysis(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        analysis_block = interactions.split(
            "export function fireAIAnalysis(): void {", 1
        )[1].split('\n}\n\ndocument.addEventListener("DOMContentLoaded"', 1)[0]

        guard_position = analysis_block.index(
            "if (activeAnalysisController) return;"
        )
        request_position = analysis_block.index("new AbortController()")
        fetch_position = analysis_block.index("fetch('/ai_insights/'")

        self.assertLess(guard_position, request_position)
        self.assertLess(request_position, fetch_position)
        self.assertNotIn("activeAnalysisController?.abort()", analysis_block)
        self.assertIn("setAnalysisPending(true)", analysis_block)

    def test_every_analysis_exit_restores_the_analyze_control(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        pending_helper = interactions.split(
            "function setAnalysisPending", 1
        )[1].split("\n}\n\ninterface ReactionData", 1)[0]
        analysis_block = interactions.split(
            "export function fireAIAnalysis(): void {", 1
        )[1].split('\n}\n\ndocument.addEventListener("DOMContentLoaded"', 1)[0]
        reset_block = interactions.split(
            "export function resetLaboratory(): void {", 1
        )[1].split("\n}\n\nfunction getCsrfToken", 1)[0]

        self.assertIn("updateAnalysisAvailability()", pending_helper)
        self.assertIn("setAttribute('aria-busy'", pending_helper)
        self.assertIn(".finally(() => {", analysis_block)
        self.assertIn("activeAnalysisController = null", analysis_block)
        self.assertIn("setAnalysisPending(false)", analysis_block)
        self.assertIn("setAnalysisPending(false)", reset_block)
        self.assertNotIn("resetBtn.disabled", interactions)
