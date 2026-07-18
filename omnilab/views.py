import hashlib
import ipaddress
import json
import os
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PRODUCTION_BASE_URL = "https://omnilab-bk8q.onrender.com"
SOCIAL_PREVIEW_URL = (
    f"{PRODUCTION_BASE_URL}/static/images/omnilab-social-preview.png"
)
SOCIAL_PREVIEW_ALT = (
    "OmniLab virtual chemistry lab showing sodium and chlorine selected, "
    "a sodium chloride equation, reaction analysis, and safety guidance."
)
PUBLIC_CANONICAL_URLS = {
    "index": f"{PRODUCTION_BASE_URL}/",
    "pricing": f"{PRODUCTION_BASE_URL}/pricing/",
    "privacy": f"{PRODUCTION_BASE_URL}/privacy/",
    "terms": f"{PRODUCTION_BASE_URL}/terms/",
    "sodium_chlorine_reaction": (
        f"{PRODUCTION_BASE_URL}/guides/sodium-and-chlorine-reaction/"
    ),
    "sodium_chlorine_formula": (
        f"{PRODUCTION_BASE_URL}/guides/sodium-and-chlorine-formula/"
    ),
    "sodium_chlorine_ionic_bond": (
        f"{PRODUCTION_BASE_URL}/guides/sodium-and-chlorine-ionic-bond/"
    ),
}
SODIUM_CHLORINE_DEMO_URL = f"{PRODUCTION_BASE_URL}/demo/sodium-chlorine/"
SODIUM_CHLORINE_DEMO = {
    "id": "first-supported-reaction",
    "version": "v1",
    "selectedChemicals": ["Na", "Cl2"],
    "vessel": "beaker",
    "liquidColor": "#89a83b",
}
SUPPORTED_REACTION_EFFECTS = frozenset({"explosion", "bubble", "none"})

GUIDED_EXPERIMENT_PAGES = {
    "reaction": {
        "route_name": "guide_sodium_chlorine_reaction",
        "canonical_key": "sodium_chlorine_reaction",
        "visit_source": "guide_reaction",
        "title": "What happens when sodium reacts with chlorine?",
        "page_title": "Sodium and chlorine reaction | OmniLab student guide",
        "description": (
            "See what sodium and chlorine form, read the balanced equation, "
            "and open the supported reaction in OmniLab's virtual lab."
        ),
        "context": "Reaction guide",
        "reading_time": "4 minute read",
        "direct_answer": (
            "Sodium and chlorine form sodium chloride, an ionic solid. "
            "The balanced equation is 2Na(s) + Cl₂(g) → 2NaCl(s)."
        ),
        "equation_label": "Balanced reaction",
        "equation": "2Na(s) + Cl₂(g) → 2NaCl(s)",
        "equation_note": (
            "Two sodium atoms are needed for one chlorine molecule because "
            "elemental chlorine is written as Cl₂."
        ),
        "section_title": "Read the reaction in three moves",
        "steps": [
            {
                "number": "01",
                "title": "Start with the reactants",
                "body": (
                    "The reactant side contains sodium metal, Na, and "
                    "diatomic chlorine gas, Cl₂."
                ),
            },
            {
                "number": "02",
                "title": "Track the electron transfer",
                "body": (
                    "Each sodium atom loses one electron and each chlorine "
                    "atom gains one, producing Na⁺ and Cl⁻ ions."
                ),
            },
            {
                "number": "03",
                "title": "Name the product",
                "body": (
                    "Oppositely charged ions attract in a crystal lattice, "
                    "so the product is solid sodium chloride, NaCl."
                ),
            },
        ],
        "notice_title": "What to notice in OmniLab",
        "notice_points": [
            "The prepared setup selects Sodium and Chlorine.",
            "The prediction uses those selected chemicals only.",
            "The beaker is a visual aid and does not change the prediction.",
        ],
    },
    "formula": {
        "route_name": "guide_sodium_chlorine_formula",
        "canonical_key": "sodium_chlorine_formula",
        "visit_source": "guide_formula",
        "title": "What formula forms from sodium and chlorine?",
        "page_title": "Sodium and chlorine formula | OmniLab student guide",
        "description": (
            "Learn why sodium and chlorine form NaCl, connect the ion charges "
            "to the 1:1 formula, and try the supported setup in OmniLab."
        ),
        "context": "Formula guide",
        "reading_time": "3 minute read",
        "direct_answer": (
            "The formula is NaCl. Sodium forms Na⁺ and chlorine forms Cl⁻, "
            "so one ion of each gives an electrically neutral formula unit."
        ),
        "equation_label": "Formula and reaction",
        "equation": "Na⁺ + Cl⁻ → NaCl",
        "equation_note": (
            "For the elemental reaction, balance chlorine as Cl₂: "
            "2Na(s) + Cl₂(g) → 2NaCl(s)."
        ),
        "section_title": "Build the formula from the charges",
        "steps": [
            {
                "number": "01",
                "title": "Write the ions",
                "body": (
                    "Sodium is a group 1 metal and forms Na⁺. Chlorine "
                    "accepts an electron and forms the chloride ion, Cl⁻."
                ),
            },
            {
                "number": "02",
                "title": "Make the charge total zero",
                "body": (
                    "A +1 sodium ion and a −1 chloride ion balance in a 1:1 "
                    "ratio. No subscripts are needed in NaCl."
                ),
            },
            {
                "number": "03",
                "title": "Use formula-unit language",
                "body": (
                    "Solid sodium chloride is a repeating ionic lattice, so "
                    "NaCl describes its simplest ion ratio rather than one "
                    "discrete molecule."
                ),
            },
        ],
        "notice_title": "Use the lab to connect formula and equation",
        "notice_points": [
            "The compounds matrix starts with Na + Cl₂.",
            "The returned equation should use only the selected reactants.",
            "Check the generated explanation against your course materials.",
        ],
    },
    "ionic-bond": {
        "route_name": "guide_sodium_chlorine_ionic_bond",
        "canonical_key": "sodium_chlorine_ionic_bond",
        "visit_source": "guide_ionic_bond",
        "title": "Why do sodium and chlorine form an ionic bond?",
        "page_title": "Sodium and chlorine ionic bond | OmniLab student guide",
        "description": (
            "Follow the electron transfer from sodium to chlorine, see how "
            "Na⁺ and Cl⁻ form an ionic solid, and explore it in OmniLab."
        ),
        "context": "Bonding guide",
        "reading_time": "4 minute read",
        "direct_answer": (
            "Sodium transfers an electron to chlorine, creating Na⁺ and Cl⁻. "
            "Their opposite charges attract, forming an ionic lattice."
        ),
        "equation_label": "Electron transfer model",
        "equation": "Na → Na⁺ + e⁻   |   Cl + e⁻ → Cl⁻",
        "equation_note": (
            "In the full elemental reaction, one Cl₂ molecule accepts two "
            "electrons from two sodium atoms."
        ),
        "section_title": "From neutral atoms to an ionic lattice",
        "steps": [
            {
                "number": "01",
                "title": "Sodium loses one electron",
                "body": (
                    "A neutral sodium atom becomes Na⁺ when it gives up its "
                    "outer electron."
                ),
            },
            {
                "number": "02",
                "title": "Chlorine gains that electron",
                "body": (
                    "A chlorine atom becomes Cl⁻ after accepting one electron, "
                    "giving the two ions opposite charges."
                ),
            },
            {
                "number": "03",
                "title": "Attraction builds the solid",
                "body": (
                    "Electrostatic attraction holds many Na⁺ and Cl⁻ ions in "
                    "a repeating three-dimensional sodium chloride lattice."
                ),
            },
        ],
        "notice_title": "What the virtual prediction can show",
        "notice_points": [
            "The lab can return an equation and short explanation.",
            "Its result is generated and may be incomplete or wrong.",
            "Use a textbook or instructor to verify the bonding model.",
        ],
    },
}

HOMEPAGE_FAQS = [
    {
        "question": "How do I set up an experiment in OmniLab?",
        "answer": (
            "Choose an Erlenmeyer flask, graduated test tube, or laboratory "
            "beaker from Apparatus. Open Chemicals, search the available "
            "inputs, and drag one or more into the vessel. Add the virtual "
            "Bunsen burner if you want to model heating, then select Analyze "
            "Chemical Reaction."
        ),
    },
    {
        "question": "Which chemicals and equipment can I use?",
        "answer": (
            "The current release uses the chemicals listed in its searchable "
            "Chemicals menu. Equipment includes an Erlenmeyer flask, graduated "
            "test tube, laboratory beaker, and virtual Bunsen burner. The menus "
            "in the lab are the current source of truth for supported inputs."
        ),
    },
    {
        "question": "How accurate are the reaction results?",
        "answer": (
            "OmniLab generates predicted equations, explanations, visual "
            "effects, and safety guidance from the chemical names you select. "
            "Generated results can be incomplete or wrong, so check important "
            "information against trusted chemistry sources and follow your "
            "instructor's guidance."
        ),
    },
    {
        "question": "Can OmniLab replace a physical chemistry lab?",
        "answer": (
            "No. OmniLab is an educational prediction tool for exploring "
            "setups before working with real materials. It doesn't reproduce "
            "every real-world condition or replace trained supervision, "
            "professional judgment, or the safety procedures of a physical "
            "laboratory."
        ),
    },
    {
        "question": "Do I need an account to start?",
        "answer": (
            "No. The current public release opens directly in the lab and "
            "doesn't require an account or payment. Future access or pricing "
            "may change as the product develops."
        ),
    },
]

REACTION_API_BASE_URL = os.getenv(
    "OMNILAB_AI_BASE_URL",
    "https://models.github.ai/inference",
)
REACTION_MODEL = os.getenv("OMNILAB_AI_MODEL", "openai/gpt-4o-mini")
REACTION_RETRY_MESSAGE = (
    "OmniLab couldn't complete this prediction. Please try again."
)


def get_client_network_address(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    # Render puts the real client address first and appends proxy hops after it.
    # The application socket address is the safe fallback for malformed input.
    candidates = [
        forwarded_for.split(",", 1)[0].strip(),
        request.META.get("REMOTE_ADDR", "").strip(),
    ]

    for candidate in candidates:
        try:
            return ipaddress.ip_address(candidate).compressed
        except ValueError:
            continue

    return "unknown"


def reaction_rate_limit(request):
    limit = max(1, settings.OMNILAB_REACTION_RATE_LIMIT_REQUESTS)
    window_seconds = max(
        1, settings.OMNILAB_REACTION_RATE_LIMIT_WINDOW_SECONDS
    )
    now = int(time.time())
    window_number = now // window_seconds
    retry_after = window_seconds - (now % window_seconds)
    client_address = get_client_network_address(request)
    client_digest = hashlib.sha256(client_address.encode()).hexdigest()
    cache_key = f"omnilab:reaction-analysis:{client_digest}:{window_number}"

    if cache.add(cache_key, 1, timeout=retry_after):
        request_count = 1
    else:
        try:
            request_count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=retry_after)
            request_count = 1

    if request_count <= limit:
        return None

    response = JsonResponse(
        {
            "status": "rate_limited",
            "message": (
                "Too many reaction analyses were requested from this "
                f"network. Try again in {retry_after} seconds."
            ),
        },
        status=429,
    )
    response["Retry-After"] = str(retry_after)
    return response


def get_reaction_client():
    api_key = os.getenv("GITHUB_MODELS_API_KEY") or os.getenv(
        "FEATHERLESS_AI_API"
    )
    if not api_key:
        raise RuntimeError("Reaction provider is not configured.")

    return OpenAI(base_url=REACTION_API_BASE_URL, api_key=api_key)


def parse_selected_chemicals(user_query):
    return list(
        dict.fromkeys(
            chemical.strip()
            for chemical in user_query.split("+")
            if chemical.strip()
        )
    )


def normalize_reactant(reactant):
    normalized = reactant.strip()
    normalized = re.sub(r"^\d+(?:\.\d+)?\s*", "", normalized)
    normalized = re.sub(r"\((?:s|l|g|aq)\)\s*$", "", normalized, flags=re.I)
    return re.sub(r"\s+", "", normalized).casefold()


def equation_uses_only_selected_reactants(equation, selected_chemicals):
    selected = {
        normalize_reactant(chemical) for chemical in selected_chemicals
    }
    equation_steps = [
        step.strip() for step in equation.split("|") if step.strip()
    ]

    if not equation_steps:
        return False

    for step in equation_steps:
        if "->" not in step:
            return False
        reactant_side, _ = step.split("->", 1)
        reactants = {
            normalize_reactant(reactant)
            for reactant in reactant_side.split("+")
            if reactant.strip()
        }
        if not reactants or not reactants.issubset(selected):
            return False

    return True


def normalize_reaction_effect(effect):
    return (
        effect
        if isinstance(effect, str) and effect in SUPPORTED_REACTION_EFFECTS
        else "none"
    )


def insufficient_input_response(message):
    return JsonResponse(
        {
            "status": "insufficient_input",
            "message": message,
        }
    )


def reaction_retry_response():
    return JsonResponse(
        {
            "status": "error",
            "message": REACTION_RETRY_MESSAGE,
        },
        status=502,
    )


def homepage_context(reaction_demo=None):
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq["answer"],
                },
            }
            for faq in HOMEPAGE_FAQS
        ],
    }
    software_schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "OmniLab",
        "url": PUBLIC_CANONICAL_URLS["index"],
        "description": (
            "An interactive virtual chemistry laboratory for chemistry "
            "students to mix compounds, choose lab equipment, and review "
            "predicted reactions."
        ),
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
        "featureList": [
            "Search and mix supported chemicals",
            "Choose a flask, test tube, beaker, or virtual Bunsen burner",
            (
                "Review predicted equations, explanations, visual effects, "
                "and safety guidance"
            ),
        ],
        "license": (
            "https://github.com/Yusupov-Muhammadyusuf/OmniLab/blob/main/LICENSE"
        ),
        "codeRepository": "https://github.com/Yusupov-Muhammadyusuf/OmniLab",
    }
    context = {
        "canonical_url": PUBLIC_CANONICAL_URLS["index"],
        "social_url": PUBLIC_CANONICAL_URLS["index"],
        "page_title": "OmniLab - Laboratory Experiments Assistant",
        "social_title": "OmniLab - Test chemical reactions in a virtual lab",
        "page_description": (
            "Explore predicted reactions in a virtual lab built for chemistry "
            "students. OmniLab is educational and doesn't replace physical "
            "lab procedures."
        ),
        "social_preview_url": SOCIAL_PREVIEW_URL,
        "social_preview_alt": SOCIAL_PREVIEW_ALT,
        "homepage_faqs": HOMEPAGE_FAQS,
        "faq_schema_json": json.dumps(faq_schema),
        "software_schema_json": json.dumps(software_schema),
        "reaction_demo": reaction_demo,
        "reaction_demo_json": json.dumps(reaction_demo),
    }
    if reaction_demo:
        context.update(
            {
                "social_url": SODIUM_CHLORINE_DEMO_URL,
                "page_title": "OmniLab - Sodium and chlorine reaction demo",
                "social_title": "OmniLab - Sodium and chlorine reaction demo",
                "page_description": (
                    "Open a prepared Sodium and Chlorine setup, then choose "
                    "whether to request an educational reaction prediction."
                ),
            }
        )
    return context


@ensure_csrf_cookie
def index(request):
    return render(request, "index.html", homepage_context())


@ensure_csrf_cookie
def sodium_chlorine_demo(request):
    return render(
        request,
        "index.html",
        homepage_context(SODIUM_CHLORINE_DEMO),
    )


def guided_experiment(request, guide_key):
    guide = GUIDED_EXPERIMENT_PAGES[guide_key]
    related_guides = [
        related_guide
        for related_key, related_guide in GUIDED_EXPERIMENT_PAGES.items()
        if related_key != guide_key
    ]
    canonical_url = PUBLIC_CANONICAL_URLS[guide["canonical_key"]]
    page_schema = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": guide["title"],
        "description": guide["description"],
        "url": canonical_url,
        "educationalLevel": "Introductory chemistry",
        "learningResourceType": "Study guide",
        "isPartOf": {
            "@type": "WebSite",
            "name": "OmniLab",
            "url": PUBLIC_CANONICAL_URLS["index"],
        },
    }
    return render(
        request,
        "guided_experiment.html",
        {
            "guide": guide,
            "related_guides": related_guides,
            "canonical_url": canonical_url,
            "social_preview_url": SOCIAL_PREVIEW_URL,
            "social_preview_alt": SOCIAL_PREVIEW_ALT,
            "page_schema_json": json.dumps(page_schema),
        },
    )

def pricing(request):
    return render(
        request,
        "pricing.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["pricing"]},
    )

def privacy(request):
    return render(
        request,
        "privacy.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["privacy"]},
    )

def terms(request):
    return render(
        request,
        "terms.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["terms"]},
    )


def robots_txt(request):
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /ai_insights/",
            f"Sitemap: {PRODUCTION_BASE_URL}/sitemap.xml",
            "",
        ]
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    urls = "".join(
        f"  <url><loc>{url}</loc></url>\n"
        for url in PUBLIC_CANONICAL_URLS.values()
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )
    return HttpResponse(content, content_type="application/xml; charset=utf-8")

def ai_insights(request):
    if request.method == "POST":
        user_query = request.POST.get("query", "No chemicals specified.")
        selected_chemicals = parse_selected_chemicals(user_query)

        if len(selected_chemicals) < 2:
            return insufficient_input_response(
                "Add at least two chemicals to predict a reaction. "
                "OmniLab only analyzes the chemicals you select and won't "
                "introduce another reagent."
            )

        rate_limit_response = reaction_rate_limit(request)
        if rate_limit_response is not None:
            return rate_limit_response

        system_prompt = (
            "You are an advanced academic chemistry simulator engine for OmniLab. "
            "Analyze the mixture of provided chemicals thoroughly.\n\n"
            "Treat the user's selected chemical list as the complete set of "
            "reactants. Never add water, air, acid, a solvent, or any other "
            "unselected reagent to the reactant side of an equation or describe "
            "it as part of the chosen setup. If the selected chemicals do not "
            "support a meaningful reaction, return effect 'none' and an equation "
            "that contains only the selected chemicals.\n\n"
            "You MUST return strictly a single valid JSON object containing these exact keys:\n"
            "{\n"
            "  \"effect\": \"explosion\",\n"
            "  \"equation\": \"detailed balanced molecular equations with states\",\n"
            "  \"explanation\": \"clear educational explanation\",\n"
            "  \"safety\": \"detailed guidelines\"\n"
            "}\n\n"
            "Instructions for output tuning:\n"
            "1. 'effect': Choose exactly one value from ['explosion', 'bubble', 'none']. Set to 'explosion' only when the selected chemicals support a visible thermal blast, 'bubble' only when they support visible gas evolution, and otherwise use 'none'.\n"
            "2. 'equation': Provide ONLY the balanced chemical molecular equations with states (e.g., '2NaOH(aq) + H2SO4(aq) -> Na2SO4(aq) + 2H2O(l)'). Do NOT include any nested JSON, step-by-step text descriptions, explanations, spectator ions text, or words inside this field. Just raw chemical equations separated by ' | ' if there are multiple steps.\n"        
            "3. 'explanation': Provide a concise, clear, and high-density academic explanation (strictly 3-4 sentences maximum). Do NOT generate random text, messy paragraphs, or long historical essays. Focus exclusively on the main chemical reaction, thermodynamics (exothermic/endothermic), and its core behavior.\n"
            "4. 'safety': Provide exactly three short, practical laboratory safety rules tailored to these reagents. Format them as a single string separated by ' | ' (e.g., 'Wear heavy-duty nitrile gloves. | Avoid inhaling any evolved gases. | Keep the reaction flask away from open flames.'). Start each rule with a strong action verb. Keep them simple, logical, and chemical-focused."
        )

        try:
            response = get_reaction_client().chat.completions.create(
                model=REACTION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  
                max_tokens=3000
            )
            
            ai_raw_text = response.choices[0].message.content.strip()
            data = json.loads(ai_raw_text)

            if not equation_uses_only_selected_reactants(
                data.get("equation", ""), selected_chemicals
            ):
                return insufficient_input_response(
                    "OmniLab couldn't produce a prediction using only your "
                    "selected chemicals. Try a different combination."
                )

            data["effect"] = normalize_reaction_effect(data.get("effect"))
            
            return JsonResponse({"status": "success", "data": data})
            
        except (json.JSONDecodeError, ValueError):
            return reaction_retry_response()
        except Exception:
            return reaction_retry_response()
        
    return JsonResponse({"status": "error", "message": "Only POST requests are accepted."})
