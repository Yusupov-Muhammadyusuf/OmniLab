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
    "copper_sulfate_potassium_hydroxide": (
        f"{PRODUCTION_BASE_URL}/guides/"
        "copper-ii-sulfate-potassium-hydroxide-precipitate/"
    ),
    "sodium_water": (
        f"{PRODUCTION_BASE_URL}/guides/reaction-of-sodium-in-water/"
    ),
    "zinc_hydrochloric_acid": (
        f"{PRODUCTION_BASE_URL}/guides/"
        "zinc-and-hydrochloric-acid-reaction/"
    ),
    "acetic_acid_sodium_bicarbonate": (
        f"{PRODUCTION_BASE_URL}/guides/"
        "acetic-acid-and-sodium-bicarbonate-reaction/"
    ),
    "hydrogen_oxygen": (
        f"{PRODUCTION_BASE_URL}/guides/hydrogen-and-oxygen-reaction/"
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
    "copper-sulfate-potassium-hydroxide": {
        "id": "copper-sulfate-potassium-hydroxide",
        "version": "v1",
        "selectedChemicals": ["CuSO4", "KOH"],
        "vessel": "beaker",
        "liquidColor": "#5ba7d1",
        "mixture_label": "CuSO4 + KOH",
        "title": (
            "Copper(II) sulfate and potassium hydroxide, ready to analyze"
        ),
        "page_title": (
            "OmniLab - Copper(II) sulfate and potassium hydroxide demo"
        ),
        "page_description": (
            "Open a prepared Copper(II) sulfate and Potassium hydroxide "
            "setup, then choose whether to request an educational reaction "
            "prediction."
        ),
        "url": (
            f"{PRODUCTION_BASE_URL}/demo/"
            "copper-sulfate-potassium-hydroxide/"
        ),
    },
    "sodium-water": {
        "id": "sodium-water",
        "version": "v1",
        "selectedChemicals": ["Na", "H2O"],
        "vessel": "beaker",
        "liquidColor": "#2b9ed8",
        "mixture_label": "Na + H2O",
        "title": "Sodium and water, ready to analyze",
        "page_title": "OmniLab - Sodium and water reaction demo",
        "page_description": (
            "Open a prepared Sodium and Water setup, then choose whether to "
            "request an educational reaction prediction."
        ),
        "url": f"{PRODUCTION_BASE_URL}/demo/sodium-water/",
    },
    "zinc-hydrochloric-acid": {
        "id": "zinc-hydrochloric-acid",
        "version": "v1",
        "selectedChemicals": ["Zn", "HCl"],
        "vessel": "beaker",
        "liquidColor": "#8d98a3",
        "mixture_label": "Zn + HCl",
        "title": "Zinc and hydrochloric acid, ready to analyze",
        "page_title": "OmniLab - Zinc and hydrochloric acid demo",
        "page_description": (
            "Open a prepared Zinc and Hydrochloric acid setup, then choose "
            "whether to request an educational reaction prediction."
        ),
        "url": (
            f"{PRODUCTION_BASE_URL}/demo/zinc-hydrochloric-acid/"
        ),
    },
    "acetic-acid-sodium-bicarbonate": {
        "id": "acetic-acid-sodium-bicarbonate",
        "version": "v1",
        "selectedChemicals": ["CH3COOH", "NaHCO3"],
        "vessel": "beaker",
        "liquidColor": "#b9c4cc",
        "mixture_label": "CH3COOH + NaHCO3",
        "title": "Acetic acid and sodium bicarbonate, ready to analyze",
        "page_title": (
            "OmniLab - Acetic acid and sodium bicarbonate demo"
        ),
        "page_description": (
            "Open a prepared Acetic acid and Sodium bicarbonate setup, then "
            "choose whether to request an educational reaction prediction."
        ),
        "url": (
            f"{PRODUCTION_BASE_URL}/demo/"
            "acetic-acid-sodium-bicarbonate/"
        ),
    },
    "hydrogen-oxygen": {
        "id": "hydrogen-oxygen",
        "version": "v1",
        "selectedChemicals": ["H2", "O2"],
        "vessel": "beaker",
        "liquidColor": "#d7edf7",
        "mixture_label": "H2 + O2",
        "title": "Hydrogen and oxygen, ready to analyze",
        "page_title": "OmniLab - Hydrogen and oxygen reaction demo",
        "page_description": (
            "Open a prepared Hydrogen and Oxygen setup, then choose whether "
            "to request an educational reaction prediction."
        ),
        "url": f"{PRODUCTION_BASE_URL}/demo/hydrogen-oxygen/",
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
    "copper-sulfate-potassium-hydroxide": {
        "route_name": "guide_copper_sulfate_potassium_hydroxide",
        "canonical_key": "copper_sulfate_potassium_hydroxide",
        "visit_source": "guide_observation_d",
        "demo_route_name": "demo_copper_sulfate_potassium_hydroxide",
        "title": (
            "What precipitate forms from copper(II) sulfate and potassium "
            "hydroxide?"
        ),
        "page_title": (
            "Copper(II) sulfate and potassium hydroxide precipitate | OmniLab"
        ),
        "description": (
            "Identify the blue precipitate from copper(II) sulfate and "
            "potassium hydroxide, read the ionic equation, and try it in "
            "OmniLab."
        ),
        "reading_time": "5 minute read",
        "direct_answer": (
            "Copper(II) sulfate and potassium hydroxide form copper(II) "
            "hydroxide, an insoluble blue precipitate. Potassium and sulfate "
            "ions remain dissolved in the solution."
        ),
        "reactants": [
            {"name": "Copper(II) sulfate", "formula": "CuSO4"},
            {"name": "Potassium hydroxide", "formula": "KOH"},
        ],
        "setup_summary": (
            "A beaker is prepared with Copper(II) sulfate and Potassium "
            "hydroxide. The burner stays off, and you decide when to analyze."
        ),
        "cta_label": "Try the blue precipitate setup",
        "equation": (
            "CuSO4(aq) + 2KOH(aq) -> Cu(OH)2(s) + K2SO4(aq)"
        ),
        "explanation": (
            "Copper(II) sulfate and potassium hydroxide undergo a double "
            "displacement reaction. Insoluble copper(II) hydroxide forms as "
            "a blue precipitate while potassium sulfate remains in solution. "
            "Two hydroxide ions are required for each copper(II) ion."
        ),
        "observation_title": "A blue copper(II) hydroxide precipitate",
        "observation": (
            "OmniLab shows a bounded blue precipitate cue inside the beaker "
            "to represent the expected copper(II) hydroxide solid."
        ),
        "observation_class": "observation-blue",
        "observation_label": "Blue solid",
        "net_ionic_equation": (
            "Cu2+(aq) + 2OH-(aq) -> Cu(OH)2(s)"
        ),
        "spectator_ions": "K+(aq) and SO4^2-(aq)",
        "ionic_explanation": (
            "Copper(II) ions combine with hydroxide ions because copper(II) "
            "hydroxide is insoluble in water. Potassium and sulfate ions do "
            "not form the solid, so they cancel from the complete ionic "
            "equation."
        ),
        "study_steps": [
            {
                "title": "Split the soluble reactants into ions",
                "body": (
                    "CuSO4 provides Cu2+ and SO4^2-. Each KOH provides K+ "
                    "and OH-."
                ),
            },
            {
                "title": "Identify the insoluble product",
                "body": (
                    "Cu2+ combines with two OH- ions to form solid Cu(OH)2, "
                    "the blue precipitate."
                ),
            },
            {
                "title": "Cancel the spectator ions",
                "body": (
                    "K+ and SO4^2- remain aqueous on both sides, leaving the "
                    "net ionic equation for precipitation."
                ),
            },
        ],
        "safety": [
            "Wear splash goggles and chemical-resistant gloves.",
            (
                "Avoid skin contact with copper sulfate and potassium "
                "hydroxide."
            ),
            "Collect copper-containing waste for proper disposal.",
        ],
        "boundary": (
            "The blue cue is a simplified expected observation. OmniLab does "
            "not model concentration, yield, particle size, temperature, "
            "addition order, or waste handling. Vessel and burner choices do "
            "not affect the prediction."
        ),
    },
    "sodium-water": {
        "route_name": "guide_sodium_water",
        "canonical_key": "sodium_water",
        "visit_source": "guide_observation_e",
        "demo_route_name": "demo_sodium_water",
        "title": "What happens when sodium reacts with water?",
        "page_title": (
            "Sodium reacts with water: equation and result | OmniLab"
        ),
        "description": (
            "See what happens when sodium reacts with water, including the "
            "balanced equation, hydrogen bubbles, sodium hydroxide, and "
            "safety limits."
        ),
        "reading_time": "6 minute read",
        "direct_answer": (
            "Sodium reacts with water to form sodium hydroxide and hydrogen "
            "gas. The reaction releases substantial heat, and the escaping "
            "hydrogen appears as bubbles."
        ),
        "reactants": [
            {"name": "Sodium", "formula": "Na"},
            {"name": "Water", "formula": "H2O"},
        ],
        "setup_summary": (
            "A beaker is prepared with Sodium and Water. The burner stays off, "
            "and you decide when to request the supported prediction."
        ),
        "cta_label": "Try the sodium and water setup",
        "equation": "2Na(s) + 2H2O(l) -> 2NaOH(aq) + H2(g)",
        "explanation": (
            "Sodium reacts with water to form sodium hydroxide and hydrogen "
            "gas. Hydrogen evolution produces bubbles while the strongly "
            "exothermic reaction heats the mixture. Two sodium atoms react "
            "with two water molecules in the balanced equation."
        ),
        "observation_title": "Hydrogen bubbles and released heat",
        "observation": (
            "OmniLab shows a bounded bubble cue inside the beaker to represent "
            "hydrogen gas forming. It does not reproduce the speed, surface "
            "motion, flame, or heat of a physical demonstration."
        ),
        "observation_class": "observation-bubbles",
        "observation_label": "Hydrogen bubbles",
        "study_steps": [
            {
                "title": "Balance sodium and water",
                "body": (
                    "The coefficient 2 appears before Na and H2O. It also "
                    "appears before NaOH, leaving two hydrogen atoms to form "
                    "one H2 molecule."
                ),
            },
            {
                "title": "Identify the gas",
                "body": (
                    "H2 is hydrogen gas. The bubbles are evidence of gas "
                    "evolution, not simply water boiling."
                ),
            },
            {
                "title": "Identify the solution",
                "body": (
                    "NaOH is sodium hydroxide. It remains dissolved, making "
                    "the resulting solution alkaline and corrosive."
                ),
            },
        ],
        "detail_sections": [
            {
                "title": "Why sodium floats and moves",
                "body": (
                    "Sodium is less dense than water, so a small piece floats. "
                    "The reaction heats the metal, which may melt into a ball, "
                    "while uneven hydrogen release can push it across the "
                    "surface. Those physical effects are not part of "
                    "OmniLab's simplified bubble cue."
                ),
            },
            {
                "title": "Why the reaction may show a flame",
                "body": (
                    "The reaction is strongly exothermic and creates flammable "
                    "hydrogen. In some demonstrations, enough heat can ignite "
                    "the hydrogen. A yellow-orange color may also appear from "
                    "excited sodium atoms. OmniLab does not predict ignition."
                ),
            },
            {
                "title": "What remains in the beaker",
                "body": (
                    "The gas leaves the mixture, but sodium hydroxide stays in "
                    "solution. That means the liquid is not merely unchanged "
                    "water: it becomes alkaline and can cause chemical burns."
                ),
            },
        ],
        "common_questions": [
            {
                "question": "What type of reaction is sodium with water?",
                "answer": (
                    "It is a redox reaction and a metal displacement reaction. "
                    "Sodium is oxidized to Na+ while hydrogen in water is "
                    "reduced to H2 gas."
                ),
            },
            {
                "question": "Why does sodium move on the surface of water?",
                "answer": (
                    "Sodium floats because it is less dense than water. Gas "
                    "formation and uneven heat release can make it move."
                ),
            },
            {
                "question": "Why is sodium and water dangerous?",
                "answer": (
                    "The reaction releases substantial heat, produces "
                    "flammable hydrogen, and leaves corrosive sodium hydroxide. "
                    "It belongs only in a controlled laboratory."
                ),
            },
            {
                "question": "Is the liquid product still water?",
                "answer": (
                    "Water remains, but the reaction also creates dissolved "
                    "sodium hydroxide. The resulting solution is alkaline."
                ),
            },
        ],
        "safety": [
            "Do not attempt this reaction outside a controlled laboratory.",
            "Keep flames and sparks away from the hydrogen produced.",
            "Use face protection and trained supervision.",
        ],
        "boundary": (
            "OmniLab predicts the balanced products and shows a simplified "
            "bubble cue. It does not model sodium mass, water volume, reaction "
            "rate, temperature, motion, ignition, or a physical procedure."
        ),
    },
    "zinc-hydrochloric-acid": {
        "route_name": "guide_zinc_hydrochloric_acid",
        "canonical_key": "zinc_hydrochloric_acid",
        "visit_source": "guide_virtual_lab",
        "demo_route_name": "demo_zinc_hydrochloric_acid",
        "title": "What happens when zinc reacts with hydrochloric acid?",
        "page_title": (
            "Zinc and hydrochloric acid reaction | OmniLab"
        ),
        "description": (
            "See the zinc and hydrochloric acid reaction, balanced equation, "
            "hydrogen bubbles, zinc chloride product, and safety limits."
        ),
        "reading_time": "5 minute read",
        "direct_answer": (
            "Zinc reacts with hydrochloric acid to form zinc chloride and "
            "hydrogen gas. Zinc is oxidized, hydrogen ions are reduced, and "
            "the escaping hydrogen appears as bubbles."
        ),
        "student_job": (
            "Use this guide to balance the equation, identify the gas, and "
            "connect the bubbles to a metal-acid displacement reaction."
        ),
        "reactants": [
            {"name": "Zinc", "formula": "Zn"},
            {"name": "Hydrochloric acid", "formula": "HCl"},
        ],
        "setup_summary": (
            "A beaker is prepared with Zinc and Hydrochloric acid. The burner "
            "stays off, and you decide when to request the supported prediction."
        ),
        "cta_label": "Try the zinc and acid setup",
        "equation": "Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g)",
        "explanation": (
            "Zinc displaces hydrogen from hydrochloric acid to form zinc "
            "chloride and hydrogen gas. The bubbles are hydrogen leaving the "
            "solution. Zinc is oxidized while hydrogen ions are reduced in "
            "this single-displacement reaction."
        ),
        "observation_title": "Hydrogen bubbles as zinc is consumed",
        "observation": (
            "OmniLab shows a bounded bubble cue inside the beaker to represent "
            "hydrogen gas forming. It does not reproduce the reaction rate, "
            "temperature change, or gradual loss of the zinc surface."
        ),
        "observation_class": "observation-bubbles",
        "observation_label": "Hydrogen bubbles",
        "study_steps": [
            {
                "title": "Balance the acid",
                "body": (
                    "The coefficient 2 before HCl supplies two chloride ions "
                    "for ZnCl2 and two hydrogen atoms for one H2 molecule."
                ),
            },
            {
                "title": "Track the electrons",
                "body": (
                    "Zinc loses two electrons to become Zn2+. Two hydrogen "
                    "ions gain those electrons and combine as H2 gas."
                ),
            },
            {
                "title": "Identify the evidence",
                "body": (
                    "The bubbles are hydrogen leaving the solution. Zinc is "
                    "consumed while aqueous zinc chloride remains."
                ),
            },
        ],
        "common_questions": [
            {
                "question": "What gas forms when zinc reacts with hydrochloric acid?",
                "answer": (
                    "Hydrogen gas forms. In the balanced equation, two H+ "
                    "ions gain electrons and combine to make H2."
                ),
            },
            {
                "question": "What type of reaction is zinc with hydrochloric acid?",
                "answer": (
                    "It is a single-displacement and redox reaction. Zinc "
                    "displaces hydrogen from the acid."
                ),
            },
            {
                "question": "What is oxidized and what is reduced?",
                "answer": (
                    "Zinc is oxidized from Zn to Zn2+. Hydrogen ions are "
                    "reduced to H2 gas."
                ),
            },
            {
                "question": "What remains in the solution?",
                "answer": (
                    "Zinc chloride remains dissolved in water while hydrogen "
                    "gas leaves the mixture."
                ),
            },
        ],
        "safety": [
            "Keep flames and sparks away from the hydrogen produced.",
            "Work in a ventilated area under trained supervision.",
            "Wear acid-resistant gloves and splash goggles.",
        ],
        "boundary": (
            "OmniLab predicts the products and shows a simplified bubble cue. "
            "It does not model reagent concentration, zinc surface area, gas "
            "volume, temperature, reaction rate, or a physical procedure."
        ),
    },
    "acetic-acid-sodium-bicarbonate": {
        "route_name": "guide_acetic_acid_sodium_bicarbonate",
        "canonical_key": "acetic_acid_sodium_bicarbonate",
        "visit_source": "guide_virtual_lab",
        "demo_route_name": "demo_acetic_acid_sodium_bicarbonate",
        "title": (
            "What happens when acetic acid reacts with sodium bicarbonate?"
        ),
        "page_title": (
            "Acetic acid and sodium bicarbonate reaction | OmniLab"
        ),
        "description": (
            "See the acetic acid and sodium bicarbonate reaction, balanced "
            "equation, carbon dioxide bubbles, products, and safety limits."
        ),
        "reading_time": "5 minute read",
        "direct_answer": (
            "Acetic acid reacts with sodium bicarbonate to form sodium "
            "acetate, carbon dioxide, and water. The carbon dioxide escapes "
            "as bubbles, which can make the mixture fizz and foam."
        ),
        "student_job": (
            "Use this guide to balance the equation, identify the gas, and "
            "connect the fizzing to an acid-bicarbonate reaction."
        ),
        "reactants": [
            {"name": "Acetic acid", "formula": "CH3COOH"},
            {"name": "Sodium bicarbonate", "formula": "NaHCO3"},
        ],
        "setup_summary": (
            "A beaker is prepared with Acetic acid and Sodium bicarbonate. "
            "The burner stays off, and you decide when to request the "
            "supported prediction."
        ),
        "cta_label": "Try the fizzing setup",
        "equation": (
            "CH3COOH(aq) + NaHCO3(s) -> "
            "CH3COONa(aq) + CO2(g) + H2O(l)"
        ),
        "explanation": (
            "Acetic acid reacts with sodium bicarbonate to form sodium "
            "acetate, carbon dioxide, and water. The visible bubbling comes "
            "from carbon dioxide leaving the mixture. The equation has a "
            "one-to-one ratio of acid and bicarbonate."
        ),
        "observation_title": "Carbon dioxide bubbles and visible fizzing",
        "observation": (
            "OmniLab shows a bounded bubble cue inside the beaker to represent "
            "carbon dioxide leaving the mixture. It does not reproduce foam "
            "height, reaction rate, cooling, or spillover."
        ),
        "observation_class": "observation-bubbles",
        "observation_label": "Carbon dioxide bubbles",
        "study_steps": [
            {
                "title": "Balance the one-to-one reaction",
                "body": (
                    "One acetic acid molecule reacts with one bicarbonate "
                    "unit, so every coefficient in the balanced equation is 1."
                ),
            },
            {
                "title": "Identify the gas",
                "body": (
                    "Bicarbonate accepts a proton from the acid. The resulting "
                    "carbonic acid breaks down into CO2 and H2O."
                ),
            },
            {
                "title": "Identify what stays dissolved",
                "body": (
                    "Sodium and acetate ions remain in solution as sodium "
                    "acetate while carbon dioxide leaves as gas."
                ),
            },
        ],
        "common_questions": [
            {
                "question": (
                    "What gas forms when acetic acid reacts with sodium "
                    "bicarbonate?"
                ),
                "answer": (
                    "Carbon dioxide gas forms. Its escape from the liquid "
                    "produces the visible fizzing and bubbles."
                ),
            },
            {
                "question": "What are the products of the reaction?",
                "answer": (
                    "The products are aqueous sodium acetate, carbon dioxide "
                    "gas, and liquid water."
                ),
            },
            {
                "question": "Why does the mixture foam?",
                "answer": (
                    "Rapidly forming carbon dioxide creates many bubbles. "
                    "Their behavior at the liquid surface can produce foam."
                ),
            },
            {
                "question": "What type of reaction is this?",
                "answer": (
                    "It is an acid-base reaction followed by carbonic acid "
                    "decomposition, which releases carbon dioxide gas."
                ),
            },
        ],
        "safety": [
            (
                "Keep the reaction vessel open so carbon dioxide cannot "
                "build pressure."
            ),
            "Wear eye protection to guard against splashes.",
            "Add the bicarbonate in small portions to control foaming.",
        ],
        "boundary": (
            "OmniLab predicts the products and shows a simplified bubble cue. "
            "It does not model reagent concentration, foam height, gas volume, "
            "temperature change, reaction rate, or a physical procedure."
        ),
    },
    "hydrogen-oxygen": {
        "route_name": "guide_hydrogen_oxygen",
        "canonical_key": "hydrogen_oxygen",
        "visit_source": "guide_virtual_lab",
        "demo_route_name": "demo_hydrogen_oxygen",
        "title": "What happens when hydrogen reacts with oxygen?",
        "page_title": "Hydrogen and oxygen reaction: equation and result | OmniLab",
        "description": (
            "See the hydrogen and oxygen reaction, balanced equation, water "
            "product, energy release, initiation requirement, and safety limits."
        ),
        "reading_time": "5 minute read",
        "direct_answer": (
            "Hydrogen reacts with oxygen to form water when the mixture is "
            "initiated. The reaction is strongly exothermic, and the balanced "
            "equation uses two hydrogen molecules for each oxygen molecule."
        ),
        "student_job": (
            "Use this guide to balance the equation, identify the product, and "
            "separate the reaction conditions from the chemical result."
        ),
        "reactants": [
            {"name": "Hydrogen", "formula": "H2"},
            {"name": "Oxygen", "formula": "O2"},
        ],
        "setup_summary": (
            "A beaker is prepared with Hydrogen and Oxygen. The burner stays "
            "off, and you decide when to request the supported prediction."
        ),
        "cta_label": "Try the hydrogen and oxygen setup",
        "equation": "2H2(g) + O2(g) -> 2H2O(l)",
        "explanation": (
            "Hydrogen and oxygen form water when the mixture is initiated. "
            "The reaction is strongly exothermic as O-H bonds form. "
            "Two hydrogen molecules react with one oxygen molecule to "
            "produce two water molecules."
        ),
        "observation_title": "Water forms in a strongly exothermic reaction",
        "observation": (
            "The supported prediction identifies water as the product. OmniLab "
            "does not add a flame, blast, or motion cue for this pair because "
            "its visual effects are simplified, not a physical simulation."
        ),
        "observation_class": "observation-clear",
        "observation_label": "Water product",
        "study_steps": [
            {
                "title": "Balance the two-to-one ratio",
                "body": (
                    "Two H2 molecules supply four hydrogen atoms. One O2 "
                    "molecule supplies two oxygen atoms, producing two H2O "
                    "molecules."
                ),
            },
            {
                "title": "Separate initiation from the products",
                "body": (
                    "Hydrogen and oxygen need an initiation source before the "
                    "reaction proceeds rapidly. That condition is not written "
                    "as another reactant in the balanced equation."
                ),
            },
            {
                "title": "Account for the energy release",
                "body": (
                    "Forming strong O-H bonds releases substantial energy, so "
                    "the reaction is exothermic even though energy does not "
                    "appear as a product formula."
                ),
            },
        ],
        "common_questions": [
            {
                "question": "What is the product of hydrogen and oxygen?",
                "answer": (
                    "The product is water. The balanced equation forms two "
                    "water molecules from two hydrogen molecules and one "
                    "oxygen molecule."
                ),
            },
            {
                "question": "Why is the equation 2H2 + O2 -> 2H2O?",
                "answer": (
                    "Those coefficients balance four hydrogen atoms and two "
                    "oxygen atoms on each side of the equation."
                ),
            },
            {
                "question": "Does hydrogen react with oxygen on its own?",
                "answer": (
                    "A hydrogen-oxygen mixture generally needs initiation, "
                    "such as a spark, before it reacts rapidly. That same fact "
                    "also makes the mixture hazardous."
                ),
            },
            {
                "question": "What type of reaction is hydrogen with oxygen?",
                "answer": (
                    "It is a combustion and redox reaction. Hydrogen is "
                    "oxidized, oxygen is reduced, and water forms."
                ),
            },
        ],
        "safety": [
            "Keep the gas mixture away from ignition sources.",
            "Use blast shielding in a supervised laboratory.",
            "Wear splash goggles and protective clothing.",
        ],
        "boundary": (
            "OmniLab predicts water as the product without simulating ignition, "
            "flame, pressure, temperature, gas ratio, reaction rate, or a "
            "physical procedure."
        ),
    },
}

CHEMICAL_REACTION_VIRTUAL_LAB_PAGE = {
    "route_name": "chemical_reaction_virtual_lab",
    "canonical_key": "chemical_reaction_virtual_lab",
    "title": "How does the chemical reaction virtual lab work?",
    "page_title": "Chemical reaction virtual lab for students | OmniLab",
    "description": (
        "Try 23 supported reaction pairs in OmniLab's free chemical reaction "
        "virtual lab. See equations, explanations, safety guidance, and "
        "visible reaction cues."
    ),
}

GUIDE_PAGE_REFERENCES = {
    CHEMICAL_REACTION_VIRTUAL_LAB_PAGE["canonical_key"]: (
        CHEMICAL_REACTION_VIRTUAL_LAB_PAGE
    ),
    **{
        guide["canonical_key"]: guide
        for guide in GUIDED_EXPERIMENT_PAGES.values()
    },
    **{
        guide["canonical_key"]: guide
        for guide in OBSERVATION_GUIDE_PAGES.values()
    },
}

# These links stay deliberately small. Each one names the chemistry connection
# a student can carry from the current guide into the next one.
GUIDE_RELATIONSHIPS = {
    "chemical_reaction_virtual_lab": [
        ("sodium_chlorine_reaction", "Start with one supported reaction"),
        ("limewater_carbon_dioxide", "See a cloudy precipitate result"),
        ("zinc_hydrochloric_acid", "See a gas-evolution result"),
    ],
    "sodium_chlorine_reaction": [
        ("sodium_chlorine_formula", "Use the same substances to build NaCl"),
        ("sodium_chlorine_ionic_bond", "Follow the same electron transfer"),
        ("sodium_water", "Compare another reaction of sodium"),
    ],
    "sodium_chlorine_formula": [
        ("sodium_chlorine_reaction", "Put NaCl into the balanced reaction"),
        ("sodium_chlorine_ionic_bond", "Connect the formula to ion charges"),
        ("sodium_water", "Compare another reaction of sodium"),
    ],
    "sodium_chlorine_ionic_bond": [
        ("sodium_chlorine_formula", "Use the ion charges to build NaCl"),
        ("sodium_chlorine_reaction", "See the same ions in the full reaction"),
        ("sodium_water", "Compare another reaction of sodium"),
    ],
    "limewater_carbon_dioxide": [
        (
            "sodium_carbonate_hydrochloric_acid",
            "Follow carbon dioxide from gas to precipitate",
        ),
        (
            "acetic_acid_sodium_bicarbonate",
            "See another reaction that produces carbon dioxide",
        ),
        (
            "silver_nitrate_potassium_iodide",
            "Compare a yellow precipitate result",
        ),
    ],
    "sodium_carbonate_hydrochloric_acid": [
        ("zinc_hydrochloric_acid", "Compare another hydrochloric acid reaction"),
        ("limewater_carbon_dioxide", "Use the carbon dioxide in limewater"),
        (
            "acetic_acid_sodium_bicarbonate",
            "Compare another carbon dioxide-producing reaction",
        ),
    ],
    "silver_nitrate_potassium_iodide": [
        (
            "copper_sulfate_potassium_hydroxide",
            "Compare a blue precipitate result",
        ),
        ("limewater_carbon_dioxide", "Compare a cloudy precipitate result"),
    ],
    "copper_sulfate_potassium_hydroxide": [
        (
            "silver_nitrate_potassium_iodide",
            "Compare a yellow precipitate result",
        ),
        ("limewater_carbon_dioxide", "Compare a cloudy precipitate result"),
    ],
    "sodium_water": [
        ("sodium_chlorine_reaction", "Compare another reaction of sodium"),
        ("zinc_hydrochloric_acid", "Compare another hydrogen-producing reaction"),
        ("hydrogen_oxygen", "Follow hydrogen into a water-forming reaction"),
    ],
    "zinc_hydrochloric_acid": [
        (
            "sodium_carbonate_hydrochloric_acid",
            "Compare another hydrochloric acid reaction",
        ),
        ("sodium_water", "Compare another hydrogen-producing reaction"),
        ("hydrogen_oxygen", "Follow hydrogen into a water-forming reaction"),
    ],
    "acetic_acid_sodium_bicarbonate": [
        (
            "sodium_carbonate_hydrochloric_acid",
            "Compare another carbon dioxide-producing reaction",
        ),
        ("limewater_carbon_dioxide", "Use the carbon dioxide in limewater"),
    ],
    "hydrogen_oxygen": [
        ("sodium_water", "Trace hydrogen from a water reaction"),
        ("zinc_hydrochloric_acid", "Trace hydrogen from a metal-acid reaction"),
    ],
}


def related_guides_for(canonical_key):
    return [
        {
            "route_name": GUIDE_PAGE_REFERENCES[related_key]["route_name"],
            "title": GUIDE_PAGE_REFERENCES[related_key]["title"],
            "reason": reason,
        }
        for related_key, reason in GUIDE_RELATIONSHIPS[canonical_key]
    ]

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
                "title": CHEMICAL_REACTION_VIRTUAL_LAB_PAGE["title"],
                "summary": (
                    "Choose a supported pair, request a prediction, and read "
                    "the equation, explanation, safety notes, and visible cue."
                ),
                "route_name": CHEMICAL_REACTION_VIRTUAL_LAB_PAGE[
                    "route_name"
                ],
                "canonical_key": CHEMICAL_REACTION_VIRTUAL_LAB_PAGE[
                    "canonical_key"
                ],
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
            "Use cloudiness, fizzing, gas bubbles, or a colored precipitate "
            "to connect an observation to its equation."
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
            {
                "number": "08",
                "title": OBSERVATION_GUIDE_PAGES[
                    "copper-sulfate-potassium-hydroxide"
                ]["title"],
                "summary": (
                    "Connect the double displacement equation to a blue "
                    "copper(II) hydroxide precipitate."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "copper-sulfate-potassium-hydroxide"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "copper-sulfate-potassium-hydroxide"
                ]["canonical_key"],
            },
            {
                "number": "09",
                "title": OBSERVATION_GUIDE_PAGES["sodium-water"]["title"],
                "summary": (
                    "Connect hydrogen bubbles, heat release, and sodium "
                    "hydroxide to the balanced equation."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "sodium-water"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "sodium-water"
                ]["canonical_key"],
            },
            {
                "number": "10",
                "title": OBSERVATION_GUIDE_PAGES[
                    "zinc-hydrochloric-acid"
                ]["title"],
                "summary": (
                    "Connect hydrogen bubbles and electron transfer to the "
                    "balanced metal-acid reaction."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "zinc-hydrochloric-acid"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "zinc-hydrochloric-acid"
                ]["canonical_key"],
            },
            {
                "number": "11",
                "title": OBSERVATION_GUIDE_PAGES[
                    "acetic-acid-sodium-bicarbonate"
                ]["title"],
                "summary": (
                    "Connect carbon dioxide bubbles to the balanced "
                    "acid-bicarbonate reaction."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "acetic-acid-sodium-bicarbonate"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "acetic-acid-sodium-bicarbonate"
                ]["canonical_key"],
            },
            {
                "number": "12",
                "title": OBSERVATION_GUIDE_PAGES[
                    "hydrogen-oxygen"
                ]["title"],
                "summary": (
                    "Balance the two-to-one gas ratio and connect the "
                    "exothermic reaction to its water product."
                ),
                "route_name": OBSERVATION_GUIDE_PAGES[
                    "hydrogen-oxygen"
                ]["route_name"],
                "canonical_key": OBSERVATION_GUIDE_PAGES[
                    "hydrogen-oxygen"
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
    related_guides = related_guides_for(guide["canonical_key"])
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
    related_guides = related_guides_for(guide["canonical_key"])
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
    guide = CHEMICAL_REACTION_VIRTUAL_LAB_PAGE
    canonical_url = PUBLIC_CANONICAL_URLS[guide["canonical_key"]]
    description = guide["description"]
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
            "page_title": guide["page_title"],
            "page_description": description,
            "canonical_url": canonical_url,
            "social_preview_url": SOCIAL_PREVIEW_URL,
            "social_preview_alt": SOCIAL_PREVIEW_ALT,
            "page_schema_json": json.dumps(page_schema),
            "faqs": CHEMICAL_REACTION_LAB_FAQS,
            "visit_source": CHEMICAL_REACTION_VIRTUAL_LAB_VISIT_SOURCE,
            "related_guides": related_guides_for(guide["canonical_key"]),
        },
    )


def guide_library(request):
    canonical_url = PUBLIC_CANONICAL_URLS["guides"]
    description = (
        "Browse twelve chemistry guides about virtual reaction labs, sodium "
        "and chlorine, combustion, acid reactions, gas evolution, and precipitates."
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
