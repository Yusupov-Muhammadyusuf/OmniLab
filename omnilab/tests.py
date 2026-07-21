import json
import re
import struct
import xml.etree.ElementTree as ET
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from .views import (
    GUIDED_EXPERIMENT_PAGES,
    HOMEPAGE_FAQS,
    PRODUCTION_BASE_URL,
    PUBLIC_CANONICAL_URLS,
    SODIUM_CHLORINE_DEMO,
    SODIUM_CHLORINE_DEMO_URL,
    SOCIAL_PREVIEW_ALT,
    SOCIAL_PREVIEW_URL,
    equation_uses_only_selected_reactants,
    validate_complete_reaction_response,
)
from .reactions import (
    PRECIPITATE_COLORS,
    REACTION_MATRIX,
    SUPPORTED_CHEMICAL_IDS,
    get_reaction,
    supported_reaction_pairs,
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

    def test_supported_inputs_faq_states_twenty_three_reaction_pairs(self):
        supported_inputs_faq = next(
            faq
            for faq in HOMEPAGE_FAQS
            if faq["question"] == "Which chemicals and equipment can I use?"
        )
        self.assertIn("supports 23 reaction pairs", supported_inputs_faq["answer"])
        self.assertContains(self.response, supported_inputs_faq["answer"])

        html = self.response.content.decode()
        schema_match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(schema_match)
        schema = json.loads(schema_match.group(1))
        supported_inputs_entity = next(
            entity
            for entity in schema["mainEntity"]
            if entity["name"] == supported_inputs_faq["question"]
        )
        self.assertEqual(
            supported_inputs_entity["acceptedAnswer"]["text"],
            supported_inputs_faq["answer"],
        )


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
                response = self.client.get(path)
                html = response.content.decode()
                visit_source = GUIDED_EXPERIMENT_PAGES[guide_key]["visit_source"]

                self.assertEqual(html.count('class="guide-primary"'), 1)
                self.assertContains(response, "Try Sodium + Chlorine")
                self.assertNotContains(response, "Open the prepared lab")
                self.assertEqual(
                    html.count(
                        'href="/demo/sodium-chlorine/'
                        f'?source={visit_source}"'
                    ),
                    1,
                )

    def test_each_guide_links_to_the_other_two_student_questions(self):
        route_by_key = {
            guide_key: path for path, guide_key in self.routes.items()
        }

        for path, guide_key in self.routes.items():
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                related_block = html.split(
                    'class="guide-related"', 1
                )[1].split("</nav>", 1)[0]

                self.assertEqual(related_block.count("<a href="), 2)
                self.assertNotIn(
                    GUIDED_EXPERIMENT_PAGES[guide_key]["title"],
                    related_block,
                )
                for related_key, related_guide in GUIDED_EXPERIMENT_PAGES.items():
                    if related_key == guide_key:
                        continue
                    self.assertIn(
                        f'href="{route_by_key[related_key]}"',
                        related_block,
                    )
                    self.assertIn(related_guide["title"], related_block)

    def test_related_questions_stay_secondary_to_the_lab_action(self):
        for path in self.routes:
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                related_block = html.split(
                    'class="guide-related"', 1
                )[1].split("</nav>", 1)[0]

                self.assertEqual(html.count('class="guide-primary"'), 1)
                self.assertNotIn('class="guide-primary"', related_block)
                self.assertNotIn('class="btn', related_block)

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
        self.assertContains(
            response,
            '<button type="button" class="apparatus-option-card selected" '
            'id="opt-beaker" aria-pressed="true">Laboratory Beaker</button>',
            html=True,
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
            "Choose a supported pair from Chemicals. Try "
            "<strong>Hydrogen and Oxygen</strong> or "
            "<strong>Hydrochloric acid and Sodium hydroxide</strong>.",
            html=True,
        )
        self.assertContains(
            response,
            '<a class="lab-demo-link" href="/demo/sodium-chlorine/">'
            ' Open the prepared Sodium and Chlorine demo '
            '<span class="lab-control-arrow" aria-hidden="true">&rarr;</span>'
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
        self.assertIn(
            '<span class="lab-control-arrow" aria-hidden="true">&rarr;</span>',
            default_instruction,
        )
        self.assertNotIn("window.reactionDemo", default_instruction)

    def test_lab_pages_do_not_request_unused_icon_or_three_dimensional_assets(self):
        for path in ("/", "/demo/sodium-chlorine/"):
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "bootstrap@5.3.0/dist/css/bootstrap.min.css",
                )
                self.assertNotContains(response, "bootstrap-icons")
                self.assertNotContains(response, "three.min.js")
                self.assertNotContains(response, "cdnjs.cloudflare.com/ajax/libs/three")

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


class AccessibleLabSetupTests(TestCase):
    def test_apparatus_choices_are_native_pressed_buttons(self):
        normal_html = self.client.get("/").content.decode()
        demo_html = self.client.get("/demo/sodium-chlorine/").content.decode()

        for html in (normal_html, demo_html):
            with self.subTest(path="normal" if html is normal_html else "demo"):
                self.assertIn('role="group" aria-label="Choose lab apparatus"', html)
                for option_id in ("flask", "tube", "beaker", "burner"):
                    self.assertIn(
                        f'<button type="button" class="apparatus-option-card',
                        html,
                    )
                    self.assertIn(f'id="opt-{option_id}" aria-pressed=', html)

        self.assertIn('id="opt-flask" aria-pressed="true"', normal_html)
        self.assertIn('id="opt-beaker" aria-pressed="true"', demo_html)

    def test_chemical_buttons_share_one_pointer_keyboard_and_drag_path(self):
        ui = (settings.BASE_DIR / "static/ts/userInterface/ui.ts").read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        entry = (settings.BASE_DIR / "static/ts/root/main.ts").read_text()

        self.assertIn("document.createElement('button')", ui)
        self.assertIn("card.type = 'button'", ui)
        self.assertIn("card.setAttribute('draggable', 'true')", ui)
        self.assertIn("card.setAttribute('aria-label'", ui)
        self.assertIn("card.setAttribute(\n            'aria-pressed'", ui)
        self.assertIn("card.addEventListener('click'", ui)
        self.assertIn("onSelectChemical(chem.id, chem.color)", ui)
        self.assertIn("ev.currentTarget", ui)
        self.assertIn(
            "ui.buildChemicalMenu(interactions.addChemicalToLab)", entry
        )

        add_block = interactions.split(
            "export function addChemicalToLab(", 1
        )[1].split("\n}\n\nexport function drop", 1)[0]
        drop_block = interactions.split(
            "export function drop(ev: DragEvent): void {", 1
        )[1].split("\n}\n\nexport function resetLaboratory", 1)[0]
        self.assertEqual(add_block.count("captureLabSetupStarted({"), 1)
        self.assertIn("updateAnalysisAvailability()", add_block)
        self.assertIn("addChemicalToLab(name, color", drop_block)

    def test_setup_controls_expose_state_focus_and_touch_targets(self):
        html = self.client.get("/").content.decode()
        ui = (settings.BASE_DIR / "static/ts/userInterface/ui.ts").read_text()
        css = (settings.BASE_DIR / "static/css/style.css").read_text()

        self.assertIn('aria-controls="sub-panel-chemicals"', html)
        self.assertIn('aria-controls="sub-panel-apparatus"', html)
        self.assertEqual(html.count('aria-expanded="false"'), 2)
        self.assertIn("trigger.setAttribute('aria-expanded', 'true')", ui)
        self.assertIn("b.setAttribute('aria-expanded', 'false')", ui)
        self.assertIn("option?.focus()", ui)
        self.assertIn(".chemical-card:focus-visible", css)
        self.assertIn(".apparatus-option-card:focus-visible", css)
        self.assertGreaterEqual(css.count("min-height: 44px"), 2)


class SupportedSetupAnalysisStateTests(TestCase):
    def test_normal_lab_starts_disabled_with_missing_input_guidance(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Add two chemicals from a supported reaction pair.",
        )
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
            "Ready to analyze this supported reaction pair.",
        )
        self.assertNotIn("disabled", button)

    def test_browser_uses_one_exact_order_independent_support_rule(self):
        configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        support_rule = configuration.split(
            "export function isSupportedReactionSetup", 1
        )[1].split("\n}\n", 1)[0]

        self.assertIn("supportedReactionPairKeys", configuration)
        self.assertIn("selectedChemicals.length !== 2", support_rule)
        self.assertIn("[...selectedChemicals].sort().join('+')", support_rule)
        self.assertIn("supportedReactionPairKeys.has", support_rule)

    def test_catalog_marks_compatible_partners_from_the_server_pair_list(self):
        response = self.client.get("/")
        configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        ui = (
            settings.BASE_DIR / "static/ts/userInterface/ui.ts"
        ).read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        add_block = interactions.split(
            "export function addChemicalToLab(", 1
        )[1].split("\n}\n\nexport function drop", 1)[0]

        self.assertContains(response, 'id="chemical-partner-guidance"')
        self.assertContains(response, 'aria-live="polite"')
        self.assertIn("supportedReactionPartners", configuration)
        self.assertIn("getCompatibleReactionPartners", configuration)
        self.assertIn("compatible-partner", ui)
        self.assertIn("Compatible with ${selectedName}", ui)
        self.assertIn("refreshChemicalMenuGuidance();", ui)
        self.assertIn("refreshChemicalMenuGuidance();", add_block)
        self.assertLess(
            add_block.index("refreshChemicalMenuGuidance();"),
            add_block.index("updateAnalysisAvailability();"),
        )

    def test_unsupported_pair_guidance_is_specific_and_honest(self):
        ui = (
            settings.BASE_DIR / "static/ts/userInterface/ui.ts"
        ).read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn("isn't in OmniLab's supported set", ui)
        self.assertIn("doesn't mean the combination is chemically impossible", ui)
        self.assertIn("not supported in OmniLab", interactions)
        self.assertIn("marked compatible pair", interactions)

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
        add_block = interactions.split(
            "export function addChemicalToLab(", 1
        )[1].split("\n}\n\nexport function drop", 1)[0]
        drop_block = interactions.split(
            "export function drop(ev: DragEvent): void {", 1
        )[1].split("\n}\n\nexport function resetLaboratory", 1)[0]
        reset_block = interactions.split(
            "export function resetLaboratory(): void {", 1
        )[1].split("\n}\n\nfunction getCsrfToken", 1)[0]
        initialization_block = interactions.split(
            'document.addEventListener("DOMContentLoaded", () => {', 1
        )[1]

        self.assertIn("addChemicalToLab(name, color", drop_block)
        self.assertIn("updateAnalysisAvailability()", add_block)
        self.assertIn("selectedChemicals: []", reset_block)
        self.assertIn("setAnalysisPending(false)", reset_block)
        self.assertLess(
            reset_block.index("selectedChemicals: []"),
            reset_block.index("setAnalysisPending(false)"),
        )
        self.assertIn("updateAnalysisAvailability()", initialization_block)


class SavedChemicalRestorationTests(TestCase):
    def setUp(self):
        self.configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        self.interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        self.restore_block = self.interactions.split(
            'document.addEventListener("DOMContentLoaded", () => {', 1
        )[1]

    def test_saved_chemicals_use_one_safe_parser(self):
        parser = self.configuration.split(
            "export function parseSavedChemicals", 1
        )[1].split("\n}\n", 1)[0]

        self.assertIn("try {", parser)
        self.assertIn("JSON.parse(serializedChemicals)", parser)
        self.assertIn("Array.isArray(parsedChemicals)", parser)
        self.assertIn("supportedChemicalIds.has(chemical)", parser)
        self.assertIn(
            "new Set(parsedChemicals).size !== parsedChemicals.length",
            parser,
        )
        self.assertIn("catch {", parser)
        self.assertNotIn("JSON.parse(savedChemicals)", self.restore_block)
        self.assertIn(
            "config.parseSavedChemicals(storedChemicals)",
            self.restore_block,
        )

    def test_invalid_storage_is_removed_before_initial_state_is_applied(self):
        invalid_guard = (
            "if (storedChemicals !== null && savedChemicals === null) {"
        )
        remove_invalid = "removeStorageValue(chemicalsStorageKey);"
        prepared_state = "const preparedChemicals = savedChemicals"

        self.assertIn(invalid_guard, self.restore_block)
        self.assertIn(remove_invalid, self.restore_block)
        self.assertLess(
            self.restore_block.index(invalid_guard),
            self.restore_block.index(prepared_state),
        )

    def test_valid_empty_and_populated_saved_arrays_override_defaults(self):
        self.assertIn(
            "const preparedChemicals = savedChemicals\n"
            "        ?? reactionDemo?.selectedChemicals\n"
            "        ?? [];",
            self.restore_block,
        )
        self.assertNotIn("savedChemicals ||", self.restore_block)
        self.assertNotIn("savedChemicals ?", self.restore_block)

    def test_prepared_demo_fills_only_when_saved_state_is_absent_or_invalid(self):
        fallback_guard = "if (savedChemicals === null && reactionDemo) {"

        self.assertIn(fallback_guard, self.restore_block)
        fallback_block = self.restore_block.split(fallback_guard, 1)[1].split(
            "\n    }", 1
        )[0]
        self.assertIn(
            "JSON.stringify(reactionDemo.selectedChemicals)",
            fallback_block,
        )
        self.assertIn(
            "writeStorageValue(liquidColorStorageKey, reactionDemo.liquidColor)",
            fallback_block,
        )

    def test_result_color_and_reset_cleanup_contracts_remain_in_place(self):
        self.assertIn(
            "removeStorageValue(liquidColorStorageKey);",
            self.restore_block,
        )
        self.assertIn(
            "removeStorageValue(reactionStorageKey);",
            self.restore_block,
        )
        reset_block = self.interactions.split(
            "export function resetLaboratory(): void {", 1
        )[1].split("\n}\n\nfunction getCsrfToken", 1)[0]
        for storage_name in (
            "savedChemicals",
            "savedLiquidColor",
            "savedReaction",
        ):
            self.assertIn(
                f"removeStorageValue(config.getLabStorageKey('{storage_name}'))",
                reset_block,
            )


class OptionalBrowserStorageTests(TestCase):
    def setUp(self):
        self.storage = (
            settings.BASE_DIR / "static/ts/storage/storage.ts"
        ).read_text()
        self.interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

    def test_storage_helpers_turn_browser_failures_into_safe_defaults(self):
        self.assertIn("return window.localStorage.getItem(key);", self.storage)
        self.assertIn("window.localStorage.setItem(key, value);", self.storage)
        self.assertIn("window.localStorage.removeItem(key);", self.storage)
        self.assertEqual(self.storage.count("try {"), 3)
        self.assertEqual(self.storage.count("catch {"), 3)
        self.assertIn("return null;", self.storage)

    def test_lab_routes_every_storage_operation_through_safe_helpers(self):
        self.assertIn("from '../storage/storage.js';", self.interactions)
        self.assertIn("readStorageValue(chemicalsStorageKey)", self.interactions)
        self.assertIn("readStorageValue(reactionStorageKey)", self.interactions)
        self.assertIn("writeStorageValue(", self.interactions)
        self.assertIn("removeStorageValue(", self.interactions)
        self.assertNotIn("localStorage.", self.interactions)


@override_settings(
    OMNILAB_REACTION_RATE_LIMIT_REQUESTS=2,
    OMNILAB_REACTION_RATE_LIMIT_WINDOW_SECONDS=60,
)
class ReactionRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
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

    def test_normal_reaction_request_returns_matrix_result(self):
        with patch("omnilab.views.time.time", return_value=1200):
            response = self.post_reaction()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(
            response.json()["data"]["equation"],
            "2Na(s) + Cl2(g) -> 2NaCl(s)",
        )

    def test_exceeded_limit_returns_retry_guidance(self):
        with patch("omnilab.views.time.time", return_value=1200):
            self.assertEqual(self.post_reaction().status_code, 200)
            self.assertEqual(self.post_reaction().status_code, 200)
            response = self.post_reaction()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["status"], "rate_limited")
        self.assertIn("Try again in 60 seconds", response.json()["message"])
        self.assertEqual(response.headers["Retry-After"], "60")

    @override_settings(OMNILAB_REACTION_RATE_LIMIT_REQUESTS=1)
    def test_reaction_request_recovers_after_window(self):
        with patch("omnilab.views.time.time", return_value=1200):
            self.assertEqual(self.post_reaction().status_code, 200)
            self.assertEqual(self.post_reaction().status_code, 429)

        with patch("omnilab.views.time.time", return_value=1260):
            response = self.post_reaction()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

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


class SupportedReactionBoundaryTests(TestCase):
    rejection_cases = (
        ("missing", ""),
        ("single input", "Na"),
        ("duplicate input", "Na + Na"),
        ("unknown input", "Na + Xe"),
        ("unknown pair", "Cu + H2O"),
        ("additional input", "Na + Cl2 + H2O"),
    )

    @patch("omnilab.views.reaction_rate_limit")
    def test_rejected_setups_do_not_reach_throttle(
        self, reaction_rate_limit
    ):
        for label, query in self.rejection_cases:
            with self.subTest(label=label, query=query):
                reaction_rate_limit.reset_mock()

                response = self.client.post(
                    "/ai_insights/", {"query": query}
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json(),
                    {
                        "status": "insufficient_input",
                        "message": (
                            "Choose two chemicals from a supported reaction "
                            "pair, then try again."
                        ),
                    },
                )
                reaction_rate_limit.assert_not_called()

    @patch("omnilab.views.reaction_rate_limit", return_value=None)
    def test_both_supported_orders_return_the_same_matrix_result(
        self, reaction_rate_limit
    ):
        for query in ("Na + Cl2", "Cl2 + Na"):
            with self.subTest(query=query):
                reaction_rate_limit.reset_mock()

                response = self.client.post(
                    "/ai_insights/", {"query": query}
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "success")
                reaction_rate_limit.assert_called_once()


class DeterministicReactionMatrixTests(TestCase):
    requested_chemical_ids = {
        "H2",
        "O2",
        "H2O",
        "C",
        "CO2",
        "HCl",
        "NaOH",
        "NaCl",
        "Fe",
        "Cu",
        "NH3",
        "H2SO4",
        "HNO3",
        "CH3COOH",
        "KOH",
        "Ca(OH)2",
        "CuSO4",
        "AgNO3",
        "KI",
        "KMnO4",
        "Na2CO3",
        "NaHCO3",
        "BaCl2",
        "H2O2",
        "Zn",
    }

    def test_catalog_contains_all_requested_substances_once(self):
        catalog = json.loads(
            (settings.BASE_DIR / "static/js/chemicaldata.json").read_text()
        )
        catalog_ids = [chemical["id"] for chemical in catalog]

        self.assertTrue(self.requested_chemical_ids.issubset(catalog_ids))
        self.assertEqual(len(catalog_ids), len(set(catalog_ids)))
        self.assertEqual(len(catalog_ids), 27)
        self.assertEqual(set(catalog_ids), set(SUPPORTED_CHEMICAL_IDS))

    def test_matrix_preserves_existing_pair_and_required_reactions(self):
        expected_equations = {
            frozenset({"Na", "Cl2"}): "2Na(s) + Cl2(g) -> 2NaCl(s)",
            frozenset({"H2", "O2"}): "2H2(g) + O2(g) -> 2H2O(l)",
            frozenset({"HCl", "NaOH"}): (
                "HCl(aq) + NaOH(aq) -> NaCl(aq) + H2O(l)"
            ),
            frozenset({"NH3", "HNO3"}): (
                "NH3(aq) + HNO3(aq) -> NH4NO3(aq)"
            ),
            frozenset({"H2SO4", "KOH"}): (
                "H2SO4(aq) + 2KOH(aq) -> K2SO4(aq) + 2H2O(l)"
            ),
            frozenset({"CH3COOH", "NaHCO3"}): (
                "CH3COOH(aq) + NaHCO3(s) -> "
                "CH3COONa(aq) + CO2(g) + H2O(l)"
            ),
            frozenset({"Ca(OH)2", "CO2"}): (
                "Ca(OH)2(aq) + CO2(g) -> CaCO3(s) + H2O(l)"
            ),
            frozenset({"CuSO4", "KOH"}): (
                "CuSO4(aq) + 2KOH(aq) -> Cu(OH)2(s) + K2SO4(aq)"
            ),
            frozenset({"AgNO3", "NaCl"}): (
                "AgNO3(aq) + NaCl(aq) -> AgCl(s) + NaNO3(aq)"
            ),
            frozenset({"AgNO3", "KI"}): (
                "AgNO3(aq) + KI(aq) -> AgI(s) + KNO3(aq)"
            ),
            frozenset({"KMnO4", "H2O2"}): (
                "2KMnO4(aq) + 3H2O2(aq) -> "
                "2MnO2(s) + 3O2(g) + 2KOH(aq) + 2H2O(l)"
            ),
            frozenset({"Na2CO3", "HCl"}): (
                "Na2CO3(aq) + 2HCl(aq) -> "
                "2NaCl(aq) + CO2(g) + H2O(l)"
            ),
            frozenset({"BaCl2", "Na2CO3"}): (
                "BaCl2(aq) + Na2CO3(aq) -> BaCO3(s) + 2NaCl(aq)"
            ),
            frozenset({"Zn", "HCl"}): (
                "Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g)"
            ),
        }

        for pair, equation in expected_equations.items():
            with self.subTest(pair=pair):
                self.assertEqual(REACTION_MATRIX[pair]["equation"], equation)

    def test_every_matrix_entry_has_a_complete_safe_contract(self):
        self.assertEqual(len(REACTION_MATRIX), 23)

        for pair, reaction in REACTION_MATRIX.items():
            with self.subTest(pair=pair):
                self.assertEqual(len(pair), 2)
                self.assertTrue(pair.issubset(SUPPORTED_CHEMICAL_IDS))
                self.assertIn(
                    reaction["effect"],
                    {"explosion", "bubble", "precipitate", "none"},
                )
                self.assertTrue(reaction["explanation"].strip())
                self.assertEqual(len(reaction["safety"].split("|")), 3)
                self.assertTrue(
                    equation_uses_only_selected_reactants(
                        reaction["equation"], list(pair)
                    )
                )

    def test_five_precipitation_reactions_have_bounded_colors(self):
        expected_precipitates = {
            frozenset({"Ca(OH)2", "CO2"}): "#f5f3ea",
            frozenset({"CuSO4", "KOH"}): "#5ba7d1",
            frozenset({"AgNO3", "NaCl"}): "#f5f3ea",
            frozenset({"AgNO3", "KI"}): "#f2c94c",
            frozenset({"BaCl2", "Na2CO3"}): "#f5f3ea",
        }

        precipitate_reactions = {
            pair: reaction
            for pair, reaction in REACTION_MATRIX.items()
            if reaction["effect"] == "precipitate"
        }
        self.assertEqual(set(precipitate_reactions), set(expected_precipitates))
        for pair, expected_color in expected_precipitates.items():
            with self.subTest(pair=pair):
                reaction = precipitate_reactions[pair]
                self.assertEqual(reaction["precipitate_color"], expected_color)
                self.assertIn(reaction["precipitate_color"], PRECIPITATE_COLORS)

    def test_precipitate_contract_rejects_missing_or_unknown_colors(self):
        valid_reaction = REACTION_MATRIX[frozenset({"AgNO3", "KI"})]

        for color in (None, "yellow", "#ffffff", 2, []):
            with self.subTest(color=color):
                candidate = {**valid_reaction, "precipitate_color": color}
                self.assertIsNone(
                    validate_complete_reaction_response(
                        candidate,
                        ["AgNO3", "KI"],
                    )
                )

    def test_non_precipitate_contract_rejects_precipitate_metadata(self):
        reaction = {
            **REACTION_MATRIX[frozenset({"Na", "Cl2"})],
            "precipitate_color": "#f5f3ea",
        }

        self.assertIsNone(
            validate_complete_reaction_response(reaction, ["Na", "Cl2"])
        )

    def test_every_matrix_pair_is_order_independent_at_the_endpoint(self):
        for first, second in supported_reaction_pairs():
            with self.subTest(pair=(first, second)):
                forward = self.client.post(
                    "/ai_insights/", {"query": f"{first} + {second}"}
                )
                reverse = self.client.post(
                    "/ai_insights/", {"query": f"{second} + {first}"}
                )

                self.assertEqual(forward.status_code, 200)
                self.assertEqual(reverse.status_code, 200)
                self.assertEqual(forward.json(), reverse.json())

    def test_matrix_lookup_returns_defensive_copies(self):
        first = get_reaction(["H2", "O2"])
        second = get_reaction(["O2", "H2"])

        first["equation"] = "changed"
        self.assertEqual(second["equation"], "2H2(g) + O2(g) -> 2H2O(l)")


class ReactionCsrfProtectionTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

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

    def test_tokenless_request_is_rejected(self):
        response = self.post_reaction()

        self.assertEqual(response.status_code, 403)

    def test_invalid_token_is_rejected(self):
        self.get_token()

        response = self.post_reaction("a" * 32)

        self.assertEqual(response.status_code, 403)

    def test_cross_origin_request_is_rejected(self):
        token = self.get_token()

        response = self.post_reaction(token, origin="https://example.net")

        self.assertEqual(response.status_code, 403)

    def test_valid_homepage_token_keeps_reaction_contract(self):
        token = self.get_token()

        response = self.post_reaction(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(
            response.json()["data"]["equation"],
            "2Na(s) + Cl2(g) -> 2NaCl(s)",
        )

    def test_demo_page_sets_token_for_the_same_browser_client(self):
        token = self.get_token("/demo/sodium-chlorine/")

        response = self.post_reaction(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_browser_client_sends_same_origin_token(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn("'X-CSRFToken': getCsrfToken()", interactions)
        self.assertIn("credentials: 'same-origin'", interactions)


class LabJourneyRepairTests(TestCase):
    def test_catalog_exposes_the_supported_reaction_substances(self):
        catalog = json.loads(
            (settings.BASE_DIR / "static/js/chemicaldata.json").read_text()
        )

        self.assertEqual(len(catalog), 27)
        self.assertEqual(len({chemical["id"] for chemical in catalog}), 27)
        self.assertTrue(
            {"Na", "Cl2", "H2", "O2", "HCl", "NaOH", "Fe", "Cu"}
            .issubset(chemical["id"] for chemical in catalog)
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

        self.assertEqual(len(catalog), 27)
        self.assertIn(
            ("HCl", "Hydrochloric acid"),
            [(chemical["id"], chemical["name"]) for chemical in catalog],
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

    def test_reaction_result_marks_do_not_require_an_icon_font(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        css = (settings.BASE_DIR / "static/css/style.css").read_text()
        render_block = interactions.split(
            "export function renderReactionResult", 1
        )[1].split("\n}\n\nfunction renderStatusMessage", 1)[0]

        self.assertNotIn('class="bi ', interactions)
        self.assertNotIn("document.createElement('i')", interactions)
        self.assertEqual(render_block.count('class="result-heading-mark'), 3)
        self.assertIn(
            '<span class="lab-control-arrow" aria-hidden="true">&nearr;</span>',
            render_block,
        )
        self.assertIn("document.createElement('span')", render_block)
        self.assertIn("icon.className = 'safety-rule-mark me-2'", render_block)
        self.assertIn("icon.textContent = '!'", render_block)
        self.assertIn(".result-heading-mark", css)
        self.assertIn(".safety-rule-mark", css)

    def test_reaction_results_render_matrix_fields_as_text(self):
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
        feedback = (
            settings.BASE_DIR / "static/ts/interactions/feedback.ts"
        ).read_text()
        css = (settings.BASE_DIR / "static/css/style.css").read_text()
        render_block = interactions.split(
            "export function renderReactionResult", 1
        )[1].split("\n}\n\nfunction renderStatusMessage", 1)[0]
        status_block = interactions.split(
            "function renderStatusMessage", 1
        )[1].split("\n}\n\nexport function setupCanvasDrag", 1)[0]

        self.assertIn("reaction-feedback", render_block)
        self.assertIn("Optional feedback", render_block)
        self.assertIn(
            "feedbackLink.href = buildFeedbackMailtoUrl(feedbackGuideSource)",
            render_block,
        )
        self.assertIn(
            "const FEEDBACK_EMAIL_ADDRESS = 'omnilab-bk8q@mail.tin.computer'",
            feedback,
        )
        self.assertIn("'What were you trying to predict?'", feedback)
        self.assertIn("'What do you plan to do next?'", feedback)
        self.assertIn("encodeURIComponent(feedbackBody)", feedback)
        for private_value in (
            "selectedChemicals",
            "reaction.equation",
            "reaction.explanation",
            "reaction.safety",
        ):
            self.assertNotIn(private_value, feedback)
        self.assertNotIn("reaction-feedback", status_block)
        self.assertIn(".reaction-feedback-link", css)
        self.assertIn("min-height: 44px;", css)

    def test_feedback_email_labels_only_the_three_fixed_guide_sources(self):
        configuration = (
            settings.BASE_DIR / "static/ts/configuration/config.ts"
        ).read_text()
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        feedback = (
            settings.BASE_DIR / "static/ts/interactions/feedback.ts"
        ).read_text()

        expected_labels = {
            "guide_reaction": "Reaction guide",
            "guide_formula": "Formula guide",
            "guide_ionic_bond": "Ionic bond guide",
        }
        label_block = feedback.split(
            "const FEEDBACK_GUIDE_LABELS", 1
        )[1].split("};", 1)[0]
        found_labels = dict(
            re.findall(r"(guide_[a-z_]+): '([^']+)'", label_block)
        )

        self.assertEqual(found_labels, expected_labels)
        self.assertIn("getGuideVisitSource", configuration)
        self.assertIn(
            "config.getGuideVisitSource(config.getVisitSource())",
            interactions,
        )
        self.assertIn(
            "Object.prototype.hasOwnProperty.call(FEEDBACK_GUIDE_LABELS, source)",
            feedback,
        )
        self.assertIn("? [`Guide source: ${guideLabel}`", feedback)
        for non_guide_value in (
            "student_invite",
            "window.location",
            "URLSearchParams",
            "selectedChemicals",
            "reaction.equation",
            "reaction.explanation",
            "reaction.safety",
            "/guides/",
        ):
            with self.subTest(non_guide_value=non_guide_value):
                self.assertNotIn(non_guide_value, feedback)

    def test_sodium_chlorine_result_links_all_three_guides_as_secondary_paths(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        render_block = interactions.split(
            "export function renderReactionResult", 1
        )[1].split("\n}\n\nfunction renderStatusMessage", 1)[0]

        self.assertIn(
            "config.hasMatchingReactionGuides(selectedChemicals)",
            render_block,
        )
        self.assertEqual(render_block.count('class="reaction-study"'), 1)
        for path, guide in (
            (
                "/guides/sodium-and-chlorine-reaction/",
                GUIDED_EXPERIMENT_PAGES["reaction"],
            ),
            (
                "/guides/sodium-and-chlorine-formula/",
                GUIDED_EXPERIMENT_PAGES["formula"],
            ),
            (
                "/guides/sodium-and-chlorine-ionic-bond/",
                GUIDED_EXPERIMENT_PAGES["ionic-bond"],
            ),
        ):
            with self.subTest(path=path):
                self.assertIn(f'href="{path}"', render_block)
                self.assertIn(guide["title"], render_block)
        self.assertNotIn('class="btn', render_block)
        self.assertNotIn("action-btn-primary", render_block)
        self.assertNotIn("guide-primary", render_block)

    def test_live_and_restored_results_use_their_selected_pair_for_study_links(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        success_block = interactions.split(
            "} else if (resData.status === 'success' && resData.data) {", 1
        )[1].split("} else {", 1)[0]
        restore_block = interactions.split(
            "const savedData = readStorageValue(reactionStorageKey);", 1
        )[1]

        self.assertIn(
            "renderReactionResult(panel, reaction, state.selectedChemicals)",
            success_block,
        )
        self.assertIn(
            "renderReactionResult(panel, savedReaction, preparedChemicals)",
            restore_block,
        )

    def test_reset_removes_the_result_only_study_block(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        reset_block = interactions.split(
            "export function resetLaboratory(): void {", 1
        )[1].split("\n}\n\nfunction getCsrfToken", 1)[0]

        self.assertIn("panel.innerHTML = DEFAULT_REACTION_INSTRUCTION", reset_block)
        self.assertNotIn("reaction-study", reset_block)

    def test_browser_normalizes_effects_before_measurement_storage_and_rendering(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        success_block = interactions.split(
            "} else if (resData.status === 'success' && resData.data) {", 1
        )[1].split("} else {", 1)[0]
        restore_block = interactions.split(
            "const savedData = readStorageValue(reactionStorageKey);", 1
        )[1]

        normalization_index = success_block.index(
            "const reaction = normalizeReactionResult(resData.data);"
        )
        capture_index = success_block.index(
            "capture('reaction_analysis_completed', {"
        )
        storage_index = success_block.index("JSON.stringify(reaction)")
        render_index = success_block.index(
            "renderReactionResult(panel, reaction, state.selectedChemicals);"
        )
        self.assertLess(normalization_index, capture_index)
        self.assertLess(normalization_index, storage_index)
        self.assertLess(normalization_index, render_index)
        self.assertIn("effect: reaction.effect", success_block)
        self.assertNotIn("precipitate_color: reaction.precipitate_color", success_block)
        self.assertNotIn("new_color", interactions)
        self.assertNotIn("triggerSmokeEffect", interactions)
        self.assertNotIn("return { ...reaction, effect }", interactions)
        self.assertIn("parseSavedReactionResult(savedData)", restore_block)
        self.assertIn(
            "writeStorageValue(reactionStorageKey, JSON.stringify(savedReaction))",
            restore_block,
        )

    def test_browser_rejects_incomplete_saved_reactions_before_rendering(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        restore_block = interactions.split(
            "const savedData = readStorageValue(reactionStorageKey);", 1
        )[1]

        validation_index = restore_block.index(
            "const savedReaction = parseSavedReactionResult(savedData);"
        )
        render_index = restore_block.index(
            "renderReactionResult(panel, savedReaction, preparedChemicals);"
        )
        self.assertLess(validation_index, render_index)
        self.assertIn("if (savedData !== null) {", restore_block)
        self.assertIn("removeStorageValue(reactionStorageKey);", restore_block)
        self.assertIn("? DEMO_REACTION_INSTRUCTION", restore_block)
        self.assertIn(": DEFAULT_REACTION_INSTRUCTION", restore_block)
        self.assertNotIn("capture('reaction_analysis_completed'", restore_block)

    def test_browser_discards_invalid_saved_liquid_colors(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()
        restore_block = interactions.split(
            'document.addEventListener("DOMContentLoaded", () => {', 1
        )[1]

        self.assertIn(
            "return color !== null && /^#[0-9a-f]{6}$/i.test(color);",
            interactions,
        )
        self.assertIn(
            "removeStorageValue(liquidColorStorageKey);",
            restore_block,
        )
        self.assertIn(
            "const preparedLiquidColor = savedLiquidColor || reactionDemo?.liquidColor;",
            restore_block,
        )

    def test_browser_uses_one_retry_state_without_completion_measurement(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn(
            "OmniLab couldn't complete this prediction. Please try again.",
            interactions,
        )
        self.assertEqual(interactions.count("renderReactionRetry(panel);"), 2)
        self.assertEqual(
            interactions.count("capture('reaction_analysis_completed', {"),
            1,
        )
        self.assertIn("stage: 'response'", interactions)
        self.assertIn("stage: 'network_or_parse'", interactions)
        self.assertNotIn("err instanceof Error ? err.message", interactions)

    def test_browser_renders_insufficient_input_as_an_educational_state(self):
        interactions = (
            settings.BASE_DIR / "static/ts/interactions/interactions.ts"
        ).read_text()

        self.assertIn("resData.status === 'insufficient_input'", interactions)
        self.assertIn("Try a different setup", interactions)
        self.assertIn(
            "removeStorageValue(config.getLabStorageKey('savedReaction'))",
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
            "removeStorageValue(config.getLabStorageKey('savedChemicals'))",
            reset_block,
        )
        self.assertIn(
            "removeStorageValue(config.getLabStorageKey('savedLiquidColor'))",
            reset_block,
        )
        self.assertIn(
            "removeStorageValue(config.getLabStorageKey('savedReaction'))",
            reset_block,
        )
        self.assertIn("activeAnalysisController?.abort()", reset_block)
        self.assertIn("cancelReactionEffects()", reset_block)
        self.assertIn("selectedChemicals: []", reset_block)
        self.assertIn("isBubbling: false", reset_block)
        self.assertIn("smokeParticles: []", reset_block)
        self.assertIn("explosionParticles: []", reset_block)
        self.assertIn("precipitateColor: null", reset_block)
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
