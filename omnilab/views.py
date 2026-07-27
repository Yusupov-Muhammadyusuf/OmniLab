import hashlib
import ipaddress
import json
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import ContactForm, REACTION_FEEDBACK_SOURCE
from .reactions import (
    PRECIPITATE_COLORS,
    get_reaction,
    supported_reaction_pairs,
)

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
    "contact": f"{PRODUCTION_BASE_URL}/contact/",
    "faq": f"{PRODUCTION_BASE_URL}/faq/",
    "guides": f"{PRODUCTION_BASE_URL}/guides/",
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
    "chemical_reaction_virtual_lab": (
        f"{PRODUCTION_BASE_URL}/guides/chemical-reaction-virtual-lab/"
    ),
    "limewater_carbon_dioxide": (
        f"{PRODUCTION_BASE_URL}/guides/"
        "why-limewater-turns-cloudy-with-carbon-dioxide/"
    ),
    "sodium_carbonate_hydrochloric_acid": (
        f"{PRODUCTION_BASE_URL}/guides/"
        "why-sodium-carbonate-fizzes-with-hydrochloric-acid/"
    ),
    "silver_nitrate_potassium_iodide": (
        f"{PRODUCTION_BASE_URL}/guides/"
        "silver-nitrate-potassium-iodide-precipitate/"
    ),
}
SODIUM_CHLORINE_DEMO_URL = f"{PRODUCTION_BASE_URL}/demo/sodium-chlorine/"
REACTION_FEEDBACK_VIEWED_EVENT = "reaction_feedback_viewed"
REACTION_FEEDBACK_ACCEPTED_EVENT = "reaction_feedback_accepted"
REACTION_FEEDBACK_VALIDATION_FAILED_EVENT = (
    "reaction_feedback_validation_failed"
)
REACTION_FEEDBACK_RATE_LIMITED_EVENT = "reaction_feedback_rate_limited"
REACTION_FEEDBACK_DELIVERY_FAILED_EVENT = (
    "reaction_feedback_delivery_failed"
)
SODIUM_CHLORINE_DEMO = {
    "id": "first-supported-reaction",
    "version": "v1",
    "selectedChemicals": ["Na", "Cl2"],
    "vessel": "beaker",
    "liquidColor": "#89a83b",
    "mixture_label": "Na + Cl2",
    "title": "Sodium and chlorine, ready to analyze",
    "page_title": "OmniLab - Sodium and chlorine reaction demo",
    "page_description": (
        "Open a prepared Sodium and Chlorine setup, then choose whether to "
        "request an educational reaction prediction."
    ),
    "url": SODIUM_CHLORINE_DEMO_URL,
}
REACTION_DEMOS = {
    "sodium-chlorine": SODIUM_CHLORINE_DEMO,
    "carbon-dioxide-calcium-hydroxide": {
        "id": "limewater-carbon-dioxide",
        "version": "v1",
        "selectedChemicals": ["Ca(OH)2", "CO2"],
        "vessel": "beaker",
        "liquidColor": "#6d7782",
        "mixture_label": "Ca(OH)2 + CO2",
        "title": "Limewater and carbon dioxide, ready to analyze",
        "page_title": "OmniLab - Limewater and carbon dioxide demo",
        "page_description": (
            "Open a prepared Calcium hydroxide and Carbon dioxide setup, then "
            "choose whether to request an educational reaction prediction."
        ),
        "url": (
            f"{PRODUCTION_BASE_URL}/demo/"
            "carbon-dioxide-calcium-hydroxide/"
        ),
    },
    "sodium-carbonate-hydrochloric-acid": {
        "id": "sodium-carbonate-hydrochloric-acid",
        "version": "v1",
        "selectedChemicals": ["Na2CO3", "HCl"],
        "vessel": "beaker",
        "liquidColor": "#d0a22f",
        "mixture_label": "Na2CO3 + HCl",
        "title": "Sodium carbonate and hydrochloric acid, ready to analyze",
        "page_title": "OmniLab - Sodium carbonate and hydrochloric acid demo",
        "page_description": (
            "Open a prepared Sodium carbonate and Hydrochloric acid setup, "
            "then choose whether to request an educational reaction prediction."
        ),
        "url": (
            f"{PRODUCTION_BASE_URL}/demo/"
            "sodium-carbonate-hydrochloric-acid/"
        ),
    },
    "silver-nitrate-potassium-iodide": {
        "id": "silver-nitrate-potassium-iodide",
        "version": "v1",
        "selectedChemicals": ["AgNO3", "KI"],
        "vessel": "beaker",
        "liquidColor": "#a77742",
        "mixture_label": "AgNO3 + KI",
        "title": "Silver nitrate and potassium iodide, ready to analyze",
        "page_title": "OmniLab - Silver nitrate and potassium iodide demo",
        "page_description": (
            "Open a prepared Silver nitrate and Potassium iodide setup, then "
            "choose whether to request an educational reaction prediction."
        ),
        "url": (
            f"{PRODUCTION_BASE_URL}/demo/"
            "silver-nitrate-potassium-iodide/"
        ),
    },
}
CHEMICAL_REACTION_VIRTUAL_LAB_VISIT_SOURCE = "guide_virtual_lab"
SUPPORTED_REACTION_EFFECTS = frozenset(
    {"explosion", "bubble", "precipitate", "none"}
)

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

OBSERVATION_GUIDE_PAGES = {
    "limewater-carbon-dioxide": {
        "route_name": "guide_limewater_carbon_dioxide",
        "canonical_key": "limewater_carbon_dioxide",
        "visit_source": "guide_observation_a",
        "demo_route_name": "demo_carbon_dioxide_calcium_hydroxide",
        "title": "Why does limewater turn cloudy when carbon dioxide is added?",
        "page_title": (
            "Why limewater turns cloudy with carbon dioxide | OmniLab"
        ),
        "description": (
            "See why carbon dioxide turns limewater cloudy, read the balanced "
            "equation, and open the exact supported setup in OmniLab."
        ),
        "reading_time": "4 minute read",
        "direct_answer": (
            "Carbon dioxide reacts with calcium hydroxide in limewater to form "
            "solid calcium carbonate. That suspended white precipitate makes "
            "the mixture look cloudy."
        ),
        "reactants": [
            {"name": "Calcium hydroxide", "formula": "Ca(OH)2"},
            {"name": "Carbon dioxide", "formula": "CO2"},
        ],
        "setup_summary": (
            "A beaker is prepared with Calcium hydroxide and Carbon dioxide. "
            "The burner stays off, and you decide when to analyze."
        ),
        "cta_label": "Try the limewater setup",
        "equation": "Ca(OH)2(aq) + CO2(g) -> CaCO3(s) + H2O(l)",
        "explanation": (
            "Carbon dioxide reacts with calcium hydroxide to form a calcium "
            "carbonate precipitate and water. In the common limewater test, "
            "the suspended calcium carbonate makes the solution appear "
            "cloudy. Excess carbon dioxide can cause further changes that "
            "are outside this simplified equation."
        ),
        "observation_title": "A cloudy white precipitate",
        "observation": (
            "OmniLab shows a bounded white precipitate cue inside the beaker "
            "to represent the expected calcium carbonate solid."
        ),
        "observation_class": "observation-cloudy",
        "observation_label": "Cloudy white",
        "safety": [
            (
                "Avoid breathing calcium hydroxide dust or carbon dioxide-rich "
                "air."
            ),
            "Wear splash goggles and gloves when handling limewater.",
            "Work with carbon dioxide in a well-ventilated area.",
        ],
        "boundary": (
            "OmniLab predicts this simplified limewater test. It does not "
            "simulate gas delivery, concentration, rate, yield, or the further "
            "chemistry that excess carbon dioxide can cause."
        ),
    },
    "sodium-carbonate-hydrochloric-acid": {
        "route_name": "guide_sodium_carbonate_hydrochloric_acid",
        "canonical_key": "sodium_carbonate_hydrochloric_acid",
        "visit_source": "guide_observation_b",
        "demo_route_name": "demo_sodium_carbonate_hydrochloric_acid",
        "title": "Why does sodium carbonate fizz with hydrochloric acid?",
        "page_title": (
            "Why sodium carbonate fizzes with hydrochloric acid | OmniLab"
        ),
        "description": (
            "See why sodium carbonate fizzes with hydrochloric acid, read the "
            "balanced equation, and try the exact supported setup in OmniLab."
        ),
        "reading_time": "4 minute read",
        "direct_answer": (
            "Sodium carbonate reacts with hydrochloric acid to form sodium "
            "chloride, water, and carbon dioxide gas. The escaping carbon "
            "dioxide is what makes the mixture fizz."
        ),
        "reactants": [
            {"name": "Sodium carbonate", "formula": "Na2CO3"},
            {"name": "Hydrochloric acid", "formula": "HCl"},
        ],
        "setup_summary": (
            "An open beaker is prepared with Sodium carbonate and Hydrochloric "
            "acid. The burner stays off, and you decide when to analyze."
        ),
        "cta_label": "Try the fizzing setup",
        "equation": (
            "Na2CO3(aq) + 2HCl(aq) -> "
            "2NaCl(aq) + CO2(g) + H2O(l)"
        ),
        "explanation": (
            "Sodium carbonate reacts with hydrochloric acid to form sodium "
            "chloride, carbon dioxide, and water. Carbon dioxide escaping "
            "from the solution causes bubbling. Two hydrogen ions are needed "
            "for each carbonate ion in the balanced equation."
        ),
        "observation_title": "Carbon dioxide bubbles",
        "observation": (
            "OmniLab shows a bounded bubble cue inside the beaker to represent "
            "the expected gas evolution."
        ),
        "observation_class": "observation-bubbles",
        "observation_label": "Visible fizzing",
        "safety": [
            "Wear splash goggles and acid-resistant gloves.",
            "Add hydrochloric acid slowly to control foaming and heat.",
            "Keep the vessel open and work in a ventilated area.",
        ],
        "boundary": (
            "The bubble cue represents expected gas evolution, not its rate, "
            "volume, temperature change, or real-procedure safety. Vessel and "
            "burner choices do not affect the prediction."
        ),
    },
    "silver-nitrate-potassium-iodide": {
        "route_name": "guide_silver_nitrate_potassium_iodide",
        "canonical_key": "silver_nitrate_potassium_iodide",
        "visit_source": "guide_observation_c",
        "demo_route_name": "demo_silver_nitrate_potassium_iodide",
        "title": (
            "What precipitate forms when silver nitrate reacts with "
            "potassium iodide?"
        ),
        "page_title": (
            "Silver nitrate and potassium iodide precipitate | OmniLab"
        ),
        "description": (
            "Identify the precipitate from silver nitrate and potassium "
            "iodide, read the equation, and try the supported setup in OmniLab."
        ),
        "reading_time": "4 minute read",
        "direct_answer": (
            "Silver nitrate and potassium iodide form silver iodide, an "
            "insoluble yellow precipitate. Potassium and nitrate ions remain "
            "dissolved in the solution."
        ),
        "reactants": [
            {"name": "Silver nitrate", "formula": "AgNO3"},
            {"name": "Potassium iodide", "formula": "KI"},
        ],
        "setup_summary": (
            "A beaker is prepared with Silver nitrate and Potassium iodide. "
            "The burner stays off, and you decide when to analyze."
        ),
        "cta_label": "Try the yellow precipitate setup",
        "equation": "AgNO3(aq) + KI(aq) -> AgI(s) + KNO3(aq)",
        "explanation": (
            "Silver nitrate and potassium iodide undergo a precipitation "
            "reaction. Insoluble silver iodide forms as a yellow solid while "
            "potassium and nitrate ions remain in solution. The molecular "
            "equation has a one-to-one reactant ratio."
        ),
        "observation_title": "A yellow silver iodide precipitate",
        "observation": (
            "OmniLab shows a bounded yellow precipitate cue inside the beaker "
            "to represent the expected silver iodide solid."
        ),
        "observation_class": "observation-yellow",
        "observation_label": "Yellow solid",
        "safety": [
            "Wear gloves and splash goggles when handling silver nitrate.",
            "Protect the silver iodide precipitate from strong light.",
            "Collect silver-containing waste for approved disposal.",
        ],
        "boundary": (
            "The yellow cue is a simplified expected observation. OmniLab does "
            "not model concentration, yield, particle size, light-driven "
            "decomposition, or waste handling."
        ),
    },
}

GUIDE_LIBRARY_GROUPS = [
    {
        "label": "Start with the virtual lab",
        "description": (
            "See what OmniLab supports, how to choose a reaction pair, and "
            "how to read the result."
        ),
        "guides": [
            {
                "number": "01",
                "title": "How does the chemical reaction virtual lab work?",
                "summary": (
                    "Choose a supported pair, request a prediction, and read "
                    "the equation, explanation, safety notes, and visible cue."
                ),
                "route_name": "chemical_reaction_virtual_lab",
                "canonical_key": "chemical_reaction_virtual_lab",
            },
        ],
    },
    {
        "label": "Study sodium and chlorine",
        "description": (
            "Follow one reaction from reactants and electron transfer to its "
            "formula and ionic bond."
        ),
        "guides": [
            {
                "number": "02",
                "title": GUIDED_EXPERIMENT_PAGES["reaction"]["title"],
                "summary": (
                    "Follow the reactants, electron transfer, and sodium "
                    "chloride product."
                ),
                "route_name": GUIDED_EXPERIMENT_PAGES["reaction"]["route_name"],
                "canonical_key": GUIDED_EXPERIMENT_PAGES["reaction"][
                    "canonical_key"
                ],
            },
            {
                "number": "03",
                "title": GUIDED_EXPERIMENT_PAGES["formula"]["title"],
                "summary": (
                    "Connect the ion charges to NaCl and the balanced "
                    "equation."
                ),
                "route_name": GUIDED_EXPERIMENT_PAGES["formula"]["route_name"],
                "canonical_key": GUIDED_EXPERIMENT_PAGES["formula"][
                    "canonical_key"
                ],
            },
            {
                "number": "04",
                "title": GUIDED_EXPERIMENT_PAGES["ionic-bond"]["title"],
                "summary": (
                    "Trace the electron transfer from atoms to an ionic "
                    "lattice."
                ),
                "route_name": GUIDED_EXPERIMENT_PAGES["ionic-bond"][
                    "route_name"
                ],
                "canonical_key": GUIDED_EXPERIMENT_PAGES["ionic-bond"][
                    "canonical_key"
                ],
            },
        ],
    },
    {
        "label": "Follow a visible result",
        "description": (
            "Use cloudiness, fizzing, or a colored precipitate to connect an "
            "observation to its equation."
        ),
        "guides": [
            {
                "number": "05",
                "title": OBSERVATION_GUIDE_PAGES[
                    "limewater-carbon-dioxide"
                ]["title"],
                "summary": (
                    "Connect the equation to the cloudy white calcium "
                    "carbonate precipitate."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "limewater-carbon-dioxide"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "limewater-carbon-dioxide"
                ]["canonical_key"],
            },
            {
                "number": "06",
                "title": OBSERVATION_GUIDE_PAGES[
                    "sodium-carbonate-hydrochloric-acid"
                ]["title"],
                "summary": (
                    "Identify the carbon dioxide behind the visible bubbles."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "sodium-carbonate-hydrochloric-acid"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "sodium-carbonate-hydrochloric-acid"
                ]["canonical_key"],
            },
            {
                "number": "07",
                "title": OBSERVATION_GUIDE_PAGES[
                    "silver-nitrate-potassium-iodide"
                ]["title"],
                "summary": (
                    "Trace the ions that produce the yellow silver iodide "
                    "solid."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "silver-nitrate-potassium-iodide"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "silver-nitrate-potassium-iodide"
                ]["canonical_key"],
            },
        ],
    },
]

CHEMICAL_REACTION_LAB_FAQS = [
    {
        "question": "Is OmniLab's chemical reaction virtual lab free?",
        "answer": (
            "Yes. The current public release is free to use without an "
            "account or payment. Future access or pricing may change as the "
            "product develops."
        ),
    },
    {
        "question": "How many chemical reactions can I try?",
        "answer": (
            "OmniLab currently supports 23 specific reaction pairs across "
            "27 available substances. After you choose the first chemical, "
            "the lab marks every supported partner."
        ),
    },
    {
        "question": "Does the beaker or burner change the prediction?",
        "answer": (
            "No. The selected chemicals are the only inputs to the current "
            "prediction. Vessel and burner choices are visual setup aids."
        ),
    },
    {
        "question": "Can a virtual reaction replace a physical lab?",
        "answer": (
            "No. OmniLab is an educational prediction tool, not a physical "
            "simulation or a substitute for instructor supervision, trusted "
            "references, or real-laboratory safety procedures."
        ),
    },
]

PRODUCT_FAQS = [
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
            "The current release supports 23 reaction pairs using the chemicals "
            "listed in its searchable Chemicals menu. Equipment includes an "
            "Erlenmeyer flask, graduated test tube, laboratory beaker, and "
            "virtual Bunsen burner. The menus in the lab are the current source "
            "of truth for supported inputs."
        ),
    },
    {
        "question": "How accurate are the reaction results?",
        "answer": (
            "OmniLab returns educational equations, explanations, visual "
            "effects, and safety guidance for supported chemical pairs. "
            "Results can be incomplete or wrong, so check important "
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
    {
        "question": "How can I contact and get help?",
        "answer": (
            "Use the Contact page to ask a question, report something that "
            "isn't working, or suggest an improvement. Submit only the details "
            "needed to understand your request, and OmniLab will show whether "
            "your message was sent."
        ),
        "answer_before_link": "Use the ",
        "answer_link_text": "Contact page",
        "answer_after_link": (
            " to ask a question, report something that isn't working, or "
            "suggest an improvement. Submit only the details needed to "
            "understand your request, and OmniLab will show whether your "
            "message was sent."
        ),
        "link_url": "/contact/",
    },
]

REACTION_RETRY_MESSAGE = (
    "OmniLab couldn't complete this prediction. Please try again."
)
REACTION_FEEDBACK_LABEL = "Reaction feedback"
REACTION_FEEDBACK_PROMPTS = "\n\n".join(
    [
        "What were you trying to predict?",
        "What do you plan to do next?",
    ]
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


def contact_rate_limit(request):
    limit = max(1, settings.OMNILAB_CONTACT_RATE_LIMIT_REQUESTS)
    window_seconds = max(
        1, settings.OMNILAB_CONTACT_RATE_LIMIT_WINDOW_SECONDS
    )
    now = int(time.time())
    window_number = now // window_seconds
    retry_after = window_seconds - (now % window_seconds)
    client_address = get_client_network_address(request)
    client_digest = hashlib.sha256(client_address.encode()).hexdigest()
    cache_key = f"omnilab:contact:{client_digest}:{window_number}"

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

    return retry_after


def parse_selected_chemicals(user_query):
    return [
        chemical.strip()
        for chemical in user_query.split("+")
        if chemical.strip()
    ]


def is_supported_reaction_setup(selected_chemicals):
    return get_reaction(selected_chemicals) is not None


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
    if not isinstance(effect, str):
        return None

    normalized_effect = effect.strip().casefold()
    return (
        normalized_effect
        if normalized_effect in SUPPORTED_REACTION_EFFECTS
        else None
    )


def validate_complete_reaction_response(data, selected_chemicals):
    if not isinstance(data, dict):
        return None

    equation = data.get("equation")
    explanation = data.get("explanation")
    safety = data.get("safety")
    effect = normalize_reaction_effect(data.get("effect"))
    precipitate_color = data.get("precipitate_color")

    if not all(
        isinstance(value, str)
        for value in (equation, explanation, safety)
    ):
        return None

    equation = equation.strip()
    explanation = explanation.strip()
    safety_rules = [rule.strip() for rule in safety.split("|")]

    if (
        not equation
        or not explanation
        or len(safety_rules) != 3
        or not all(safety_rules)
        or effect is None
        or not equation_uses_only_selected_reactants(
            equation, selected_chemicals
        )
    ):
        return None

    if effect == "precipitate":
        if (
            not isinstance(precipitate_color, str)
            or precipitate_color not in PRECIPITATE_COLORS
        ):
            return None
    elif precipitate_color is not None:
        return None

    reaction = {
        "effect": effect,
        "equation": equation,
        "explanation": explanation,
        "safety": " | ".join(safety_rules),
    }
    if effect == "precipitate":
        reaction["precipitate_color"] = precipitate_color
    return reaction


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
        "software_schema_json": json.dumps(software_schema),
        "reaction_demo": reaction_demo,
        "reaction_demo_json": json.dumps(reaction_demo),
        "supported_reaction_pairs_json": json.dumps(
            supported_reaction_pairs()
        ),
    }
    if reaction_demo:
        context.update(
            {
                "social_url": reaction_demo["url"],
                "page_title": reaction_demo["page_title"],
                "social_title": reaction_demo["page_title"],
                "page_description": reaction_demo["page_description"],
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


@ensure_csrf_cookie
def prepared_reaction_demo(request, demo_key):
    return render(
        request,
        "index.html",
        homepage_context(REACTION_DEMOS[demo_key]),
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


def observation_guide(request, guide_key):
    guide = OBSERVATION_GUIDE_PAGES[guide_key]
    related_guides = [
        related_guide
        for related_key, related_guide in OBSERVATION_GUIDE_PAGES.items()
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
        "learningResourceType": "Experiment observation guide",
        "isPartOf": {
            "@type": "WebSite",
            "name": "OmniLab",
            "url": PUBLIC_CANONICAL_URLS["index"],
        },
    }
    return render(
        request,
        "observation_guide.html",
        {
            "guide": guide,
            "related_guides": related_guides,
            "canonical_url": canonical_url,
            "social_preview_url": SOCIAL_PREVIEW_URL,
            "social_preview_alt": SOCIAL_PREVIEW_ALT,
            "page_schema_json": json.dumps(page_schema),
        },
    )


def chemical_reaction_virtual_lab(request):
    canonical_url = PUBLIC_CANONICAL_URLS["chemical_reaction_virtual_lab"]
    page_title = "Chemical reaction virtual lab for students | OmniLab"
    description = (
        "Try 23 supported reaction pairs in OmniLab's free chemical reaction "
        "virtual lab. See equations, explanations, safety guidance, and "
        "visible reaction cues."
    )
    page_schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "LearningResource",
                "name": "Chemical reaction virtual lab for students",
                "description": description,
                "url": canonical_url,
                "educationalLevel": "Introductory chemistry",
                "learningResourceType": "Virtual laboratory guide",
                "isPartOf": {
                    "@type": "WebSite",
                    "name": "OmniLab",
                    "url": PUBLIC_CANONICAL_URLS["index"],
                },
            },
            {
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
                    for faq in CHEMICAL_REACTION_LAB_FAQS
                ],
            },
        ],
    }
    return render(
        request,
        "chemical_reaction_virtual_lab.html",
        {
            "page_title": page_title,
            "page_description": description,
            "canonical_url": canonical_url,
            "social_preview_url": SOCIAL_PREVIEW_URL,
            "social_preview_alt": SOCIAL_PREVIEW_ALT,
            "page_schema_json": json.dumps(page_schema),
            "faqs": CHEMICAL_REACTION_LAB_FAQS,
            "visit_source": CHEMICAL_REACTION_VIRTUAL_LAB_VISIT_SOURCE,
            "observation_guides": list(OBSERVATION_GUIDE_PAGES.values()),
        },
    )


def guide_library(request):
    canonical_url = PUBLIC_CANONICAL_URLS["guides"]
    description = (
        "Browse seven chemistry guides about virtual reaction labs, sodium "
        "and chlorine, gas evolution, and precipitate observations."
    )
    guides = [
        guide
        for group in GUIDE_LIBRARY_GROUPS
        for guide in group["guides"]
    ]
    page_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "OmniLab chemistry guides",
        "description": description,
        "url": canonical_url,
        "isPartOf": {
            "@type": "WebSite",
            "name": "OmniLab",
            "url": PUBLIC_CANONICAL_URLS["index"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(guides),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "item": {
                        "@type": "LearningResource",
                        "name": guide["title"],
                        "url": PUBLIC_CANONICAL_URLS[
                            guide["canonical_key"]
                        ],
                    },
                }
                for position, guide in enumerate(guides, start=1)
            ],
        },
    }
    return render(
        request,
        "guide_library.html",
        {
            "page_description": description,
            "canonical_url": canonical_url,
            "social_preview_url": SOCIAL_PREVIEW_URL,
            "social_preview_alt": SOCIAL_PREVIEW_ALT,
            "page_schema_json": json.dumps(page_schema),
            "guide_groups": GUIDE_LIBRARY_GROUPS,
        },
    )


def pricing(request):
    return render(
        request,
        "pricing.html",
        {"canonical_url": PUBLIC_CANONICAL_URLS["pricing"]},
    )


def faq(request):
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["answer"],
                },
            }
            for item in PRODUCT_FAQS
        ],
    }
    return render(
        request,
        "faq.html",
        {
            "canonical_url": PUBLIC_CANONICAL_URLS["faq"],
            "faqs": PRODUCT_FAQS,
            "faq_schema_json": json.dumps(faq_schema),
        },
    )


def contact(request):
    sent = request.GET.get("sent") == "1"
    is_feedback = request.GET.get("source") == REACTION_FEEDBACK_SOURCE
    feedback_event = None
    if is_feedback:
        feedback_event = (
            REACTION_FEEDBACK_ACCEPTED_EVENT
            if sent
            else REACTION_FEEDBACK_VIEWED_EVENT
        )
    feedback_initial = (
        {
            "message": REACTION_FEEDBACK_PROMPTS,
            "source": REACTION_FEEDBACK_SOURCE,
        }
        if is_feedback
        else None
    )

    if request.method != "POST":
        return render(
            request,
            "contact.html",
            {
                "canonical_url": PUBLIC_CANONICAL_URLS["contact"],
                "form": ContactForm(initial=feedback_initial),
                "sent": sent,
                "is_feedback": is_feedback,
                "feedback_event": feedback_event,
            },
        )

    form = ContactForm(request.POST)
    is_feedback = request.POST.get("source") == REACTION_FEEDBACK_SOURCE
    if not form.is_valid():
        return render(
            request,
            "contact.html",
            {
                "canonical_url": PUBLIC_CANONICAL_URLS["contact"],
                "form": form,
                "sent": False,
                "is_feedback": is_feedback,
                "feedback_event": (
                    REACTION_FEEDBACK_VALIDATION_FAILED_EVENT
                    if is_feedback
                    else None
                ),
            },
        )

    # Quietly accept bot-filled honeypot submissions without forwarding them.
    if form.cleaned_data["website"]:
        return redirect("/contact/?sent=1")

    retry_after = contact_rate_limit(request)
    if retry_after is not None:
        form.add_error(
            None,
            "Too many messages were sent from this network. "
            "Please try again later.",
        )
        response = render(
            request,
            "contact.html",
            {
                "canonical_url": PUBLIC_CANONICAL_URLS["contact"],
                "form": form,
                "sent": False,
                "is_feedback": is_feedback,
                "feedback_event": (
                    REACTION_FEEDBACK_RATE_LIMITED_EVENT
                    if is_feedback
                    else None
                ),
            },
            status=429,
        )
        response["Retry-After"] = str(retry_after)
        return response

    source = form.cleaned_data["source"]
    is_feedback = source == REACTION_FEEDBACK_SOURCE
    subject = (
        "Learner feedback"
        if is_feedback
        else form.cleaned_data["subject"] or "New website message"
    )
    submitted_subject = (
        "" if is_feedback else form.cleaned_data["subject"]
    )
    body = "\n".join(
        [
            f"Name: {form.cleaned_data['name']}",
            f"Email: {form.cleaned_data['email']}",
            f"Subject: {submitted_subject or '(not provided)'}",
            *(
                [f"Source: {REACTION_FEEDBACK_LABEL}"]
                if is_feedback
                else []
            ),
            *(
                [
                    "Student session interest: "
                    + (
                        "Yes"
                        if form.cleaned_data["session_interest"]
                        else "No"
                    )
                ]
                if is_feedback
                else []
            ),
            "",
            "Message:",
            form.cleaned_data["message"],
        ]
    )
    message = EmailMessage(
        subject=f"OmniLab contact: {subject}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.OMNILAB_CONTACT_TO_EMAIL],
        reply_to=[form.cleaned_data["email"]],
    )

    try:
        message.send(fail_silently=False)
    except Exception:
        form.add_error(
            None,
            "Your message couldn't be sent right now. "
            "Please try again later.",
        )
        return render(
            request,
            "contact.html",
            {
                "canonical_url": PUBLIC_CANONICAL_URLS["contact"],
                "form": form,
                "sent": False,
                "is_feedback": is_feedback,
                "feedback_event": (
                    REACTION_FEEDBACK_DELIVERY_FAILED_EVENT
                    if is_feedback
                    else None
                ),
            },
        )

    if is_feedback:
        return redirect(
            f"/contact/?sent=1&source={REACTION_FEEDBACK_SOURCE}"
        )
    return redirect("/contact/?sent=1")


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
        user_query = request.POST.get("query", "")
        selected_chemicals = parse_selected_chemicals(user_query)
        reaction = get_reaction(selected_chemicals)

        if reaction is None:
            return insufficient_input_response(
                "Choose two chemicals from a supported reaction pair, "
                "then try again."
            )

        rate_limit_response = reaction_rate_limit(request)
        if rate_limit_response is not None:
            return rate_limit_response

        data = validate_complete_reaction_response(
            reaction, selected_chemicals
        )
        if data is None:
            return reaction_retry_response()

        return JsonResponse({"status": "success", "data": data})

    return JsonResponse({"status": "error", "message": "Only POST requests are accepted."})
