"""Deterministic educational reactions supported by OmniLab."""

from copy import deepcopy


def _reaction(effect, equation, explanation, safety):
    return {
        "effect": effect,
        "equation": equation,
        "explanation": explanation,
        "safety": " | ".join(safety),
    }


REACTION_MATRIX = {
    frozenset({"Na", "Cl2"}): _reaction(
        "none",
        "2Na(s) + Cl2(g) -> 2NaCl(s)",
        (
            "Sodium and chlorine form the ionic solid sodium chloride. "
            "The reaction is strongly exothermic because the product lattice "
            "is substantially more stable than the separated elements. "
            "The equation uses two sodium atoms for each chlorine molecule."
        ),
        (
            "Use trained laboratory supervision.",
            "Keep sodium away from moisture before use.",
            "Avoid inhaling chlorine gas.",
        ),
    ),
    frozenset({"H2", "O2"}): _reaction(
        "none",
        "2H2(g) + O2(g) -> 2H2O(l)",
        (
            "Hydrogen and oxygen form water when the mixture is initiated. "
            "The reaction is strongly exothermic as O-H bonds form. "
            "Two hydrogen molecules react with one oxygen molecule to "
            "produce two water molecules."
        ),
        (
            "Keep the gas mixture away from ignition sources.",
            "Use blast shielding in a supervised laboratory.",
            "Wear splash goggles and protective clothing.",
        ),
    ),
    frozenset({"C", "O2"}): _reaction(
        "none",
        "C(s) + O2(g) -> CO2(g)",
        (
            "Carbon undergoes complete combustion in sufficient oxygen to "
            "form carbon dioxide. The oxidation is exothermic and releases "
            "energy as strong carbon-oxygen bonds form. One carbon atom and "
            "one oxygen molecule produce one carbon dioxide molecule."
        ),
        (
            "Use heat-resistant tools for hot carbon.",
            "Vent carbon dioxide from the work area.",
            "Keep combustible materials away from the reaction.",
        ),
    ),
    frozenset({"HCl", "NaOH"}): _reaction(
        "none",
        "HCl(aq) + NaOH(aq) -> NaCl(aq) + H2O(l)",
        (
            "Hydrochloric acid and sodium hydroxide neutralize to form "
            "sodium chloride and water. The net ionic change is the "
            "combination of hydrogen and hydroxide ions into water. "
            "Neutralization is exothermic, so the solution can warm."
        ),
        (
            "Wear chemical splash goggles and gloves.",
            "Add concentrated solutions slowly to control heating.",
            "Rinse acid or alkali splashes with plenty of water.",
        ),
    ),
    frozenset({"Fe", "HCl"}): _reaction(
        "bubble",
        "Fe(s) + 2HCl(aq) -> FeCl2(aq) + H2(g)",
        (
            "Iron displaces hydrogen from hydrochloric acid to form iron(II) "
            "chloride and hydrogen gas. The bubbles correspond to hydrogen "
            "leaving the solution. The reaction is a redox process in which "
            "iron is oxidized and hydrogen ions are reduced."
        ),
        (
            "Keep the reaction away from flames and sparks.",
            "Vent hydrogen gas in a supervised laboratory.",
            "Wear acid-resistant gloves and splash goggles.",
        ),
    ),
    frozenset({"Cu", "O2"}): _reaction(
        "none",
        "2Cu(s) + O2(g) -> 2CuO(s)",
        (
            "Heated copper reacts with oxygen to form black copper(II) "
            "oxide. Copper is oxidized from oxidation state zero to plus "
            "two while oxygen is reduced. The balanced equation uses two "
            "copper atoms for each oxygen molecule."
        ),
        (
            "Handle heated copper with suitable tongs.",
            "Avoid breathing copper oxide dust.",
            "Wear eye protection during heating.",
        ),
    ),
    frozenset({"Fe", "O2"}): _reaction(
        "none",
        "4Fe(s) + 3O2(g) -> 2Fe2O3(s)",
        (
            "Iron can oxidize in oxygen to form iron(III) oxide. The process "
            "is exothermic, although bulk iron may react slowly unless it is "
            "finely divided or heated. Four iron atoms combine with three "
            "oxygen molecules in the simplified balanced equation."
        ),
        (
            "Keep fine iron powder away from ignition sources.",
            "Use heat-resistant tools for heated samples.",
            "Wear eye protection and avoid oxide dust.",
        ),
    ),
    frozenset({"CO2", "NaOH"}): _reaction(
        "none",
        "CO2(g) + 2NaOH(aq) -> Na2CO3(aq) + H2O(l)",
        (
            "Carbon dioxide reacts with excess sodium hydroxide to form "
            "sodium carbonate and water. Carbon dioxide behaves as an acidic "
            "oxide in this acid-base reaction. Two hydroxide equivalents are "
            "required for each carbon dioxide molecule in the stated equation."
        ),
        (
            "Wear gloves and splash goggles when handling sodium hydroxide.",
            "Add sodium hydroxide slowly to limit splashing.",
            "Use ventilation when working with concentrated carbon dioxide.",
        ),
    ),
    frozenset({"H2", "Cl2"}): _reaction(
        "none",
        "H2(g) + Cl2(g) -> 2HCl(g)",
        (
            "Hydrogen and chlorine form hydrogen chloride after initiation, "
            "often by light or heat. The chain reaction is highly exothermic "
            "and can proceed violently. One molecule of each reactant forms "
            "two hydrogen chloride molecules."
        ),
        (
            "Keep the gas mixture away from bright light and ignition sources.",
            "Use blast shielding and trained supervision.",
            "Avoid inhaling chlorine or hydrogen chloride gas.",
        ),
    ),
    frozenset({"Na", "H2O"}): _reaction(
        "bubble",
        "2Na(s) + 2H2O(l) -> 2NaOH(aq) + H2(g)",
        (
            "Sodium reacts with water to form sodium hydroxide and hydrogen "
            "gas. Hydrogen evolution produces bubbles while the strongly "
            "exothermic reaction heats the mixture. Two sodium atoms react "
            "with two water molecules in the balanced equation."
        ),
        (
            "Do not attempt this reaction outside a controlled laboratory.",
            "Keep flames and sparks away from the hydrogen produced.",
            "Use face protection and trained supervision.",
        ),
    ),
    frozenset({"CO2", "H2O"}): _reaction(
        "none",
        "CO2(g) + H2O(l) -> H2CO3(aq)",
        (
            "Dissolved carbon dioxide establishes an equilibrium with "
            "carbonic acid in water. Only a fraction of the dissolved carbon "
            "dioxide is hydrated at equilibrium. Carbonic acid can then "
            "partially dissociate and lower the solution pH."
        ),
        (
            "Use ventilation when handling concentrated carbon dioxide.",
            "Avoid pressurizing a closed vessel with the gas.",
            "Wear eye protection when handling the solution.",
        ),
    ),
    frozenset({"NaCl", "H2O"}): _reaction(
        "none",
        "NaCl(s) + H2O(l) -> Na+(aq) + Cl-(aq) + H2O(l)",
        (
            "Sodium chloride dissolves in water and dissociates into hydrated "
            "sodium and chloride ions. Water is the solvent and is not "
            "consumed, so it appears on both sides of this process equation. "
            "This is dissolution rather than formation of a new compound."
        ),
        (
            "Wear eye protection when handling laboratory solutions.",
            "Do not ingest laboratory-grade sodium chloride.",
            "Clean spills promptly to prevent slippery surfaces.",
        ),
    ),
}


SUPPORTED_CHEMICAL_IDS = frozenset(
    chemical
    for pair in REACTION_MATRIX
    for chemical in pair
)


def reaction_key(selected_chemicals):
    canonical_by_casefold = {
        chemical.casefold(): chemical for chemical in SUPPORTED_CHEMICAL_IDS
    }
    canonical = []
    for chemical in selected_chemicals:
        normalized = chemical.strip().casefold()
        if normalized not in canonical_by_casefold:
            return None
        canonical.append(canonical_by_casefold[normalized])

    if len(canonical) != 2 or len(set(canonical)) != 2:
        return None
    return frozenset(canonical)


def get_reaction(selected_chemicals):
    key = reaction_key(selected_chemicals)
    reaction = REACTION_MATRIX.get(key)
    return deepcopy(reaction) if reaction is not None else None


def supported_reaction_pairs():
    return sorted(
        (sorted(pair) for pair in REACTION_MATRIX),
        key=lambda pair: tuple(chemical.casefold() for chemical in pair),
    )
