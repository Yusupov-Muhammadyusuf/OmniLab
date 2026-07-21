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
    frozenset({"NH3", "HNO3"}): _reaction(
        "none",
        "NH3(aq) + HNO3(aq) -> NH4NO3(aq)",
        (
            "Ammonia accepts a proton from nitric acid to form ammonium "
            "nitrate in solution. This is an acid-base reaction and can "
            "release heat, especially when concentrated solutions are used. "
            "The balanced equation uses one molecule of each reactant."
        ),
        (
            "Use dilute solutions under trained laboratory supervision.",
            "Avoid inhaling ammonia or nitric acid vapors.",
            "Do not isolate or heat the ammonium nitrate product.",
        ),
    ),
    frozenset({"H2SO4", "KOH"}): _reaction(
        "none",
        "H2SO4(aq) + 2KOH(aq) -> K2SO4(aq) + 2H2O(l)",
        (
            "Sulfuric acid and potassium hydroxide neutralize to form "
            "potassium sulfate and water. Two hydroxide ions are needed to "
            "neutralize the two acidic protons represented in the balanced "
            "equation. The solution can warm because neutralization is "
            "exothermic."
        ),
        (
            "Wear chemical splash goggles and alkali-resistant gloves.",
            "Add one dilute solution slowly to the other to control heating.",
            "Rinse acid or alkali splashes immediately with plenty of water.",
        ),
    ),
    frozenset({"CH3COOH", "NaHCO3"}): _reaction(
        "bubble",
        (
            "CH3COOH(aq) + NaHCO3(s) -> "
            "CH3COONa(aq) + CO2(g) + H2O(l)"
        ),
        (
            "Acetic acid reacts with sodium bicarbonate to form sodium "
            "acetate, carbon dioxide, and water. The visible bubbling comes "
            "from carbon dioxide leaving the mixture. The equation has a "
            "one-to-one ratio of acid and bicarbonate."
        ),
        (
            "Keep the reaction vessel open so carbon dioxide cannot build "
            "pressure.",
            "Wear eye protection to guard against splashes.",
            "Add the bicarbonate in small portions to control foaming.",
        ),
    ),
    frozenset({"Ca(OH)2", "CO2"}): _reaction(
        "none",
        "Ca(OH)2(aq) + CO2(g) -> CaCO3(s) + H2O(l)",
        (
            "Carbon dioxide reacts with calcium hydroxide to form a calcium "
            "carbonate precipitate and water. In the common limewater test, "
            "the suspended calcium carbonate makes the solution appear "
            "cloudy. Excess carbon dioxide can cause further changes that "
            "are outside this simplified equation."
        ),
        (
            "Avoid breathing calcium hydroxide dust or carbon dioxide-rich "
            "air.",
            "Wear splash goggles and gloves when handling limewater.",
            "Work with carbon dioxide in a well-ventilated area.",
        ),
    ),
    frozenset({"CuSO4", "KOH"}): _reaction(
        "none",
        "CuSO4(aq) + 2KOH(aq) -> Cu(OH)2(s) + K2SO4(aq)",
        (
            "Copper(II) sulfate and potassium hydroxide undergo a double "
            "displacement reaction. Insoluble copper(II) hydroxide forms as "
            "a blue precipitate while potassium sulfate remains in solution. "
            "Two hydroxide ions are required for each copper(II) ion."
        ),
        (
            "Wear splash goggles and chemical-resistant gloves.",
            "Avoid skin contact with copper sulfate and potassium hydroxide.",
            "Collect copper-containing waste for proper disposal.",
        ),
    ),
    frozenset({"AgNO3", "NaCl"}): _reaction(
        "none",
        "AgNO3(aq) + NaCl(aq) -> AgCl(s) + NaNO3(aq)",
        (
            "Silver nitrate and sodium chloride exchange ions to form "
            "insoluble silver chloride. The white silver chloride precipitate "
            "is the usual evidence for chloride ions in this simplified test. "
            "Sodium and nitrate ions remain in solution."
        ),
        (
            "Wear gloves and splash goggles when handling silver nitrate.",
            "Protect the mixture from strong light after the precipitate "
            "forms.",
            "Collect silver-containing waste instead of pouring it down a "
            "drain.",
        ),
    ),
    frozenset({"AgNO3", "KI"}): _reaction(
        "none",
        "AgNO3(aq) + KI(aq) -> AgI(s) + KNO3(aq)",
        (
            "Silver nitrate and potassium iodide undergo a precipitation "
            "reaction. Insoluble silver iodide forms as a yellow solid while "
            "potassium and nitrate ions remain in solution. The molecular "
            "equation has a one-to-one reactant ratio."
        ),
        (
            "Wear gloves and splash goggles when handling silver nitrate.",
            "Protect the silver iodide precipitate from strong light.",
            "Collect silver-containing waste for approved disposal.",
        ),
    ),
    frozenset({"KMnO4", "H2O2"}): _reaction(
        "bubble",
        (
            "2KMnO4(aq) + 3H2O2(aq) -> "
            "2MnO2(s) + 3O2(g) + 2KOH(aq) + 2H2O(l)"
        ),
        (
            "In neutral or alkaline conditions, permanganate oxidizes "
            "hydrogen peroxide to oxygen while manganese dioxide forms. "
            "Oxygen evolution produces bubbles and the permanganate color "
            "fades as brown manganese dioxide appears. Different acidity "
            "can change the products."
        ),
        (
            "Use dilute solutions and add hydrogen peroxide slowly.",
            "Keep both reagents away from combustible or reducing materials.",
            "Do not seal the vessel because oxygen gas is produced.",
        ),
    ),
    frozenset({"Na2CO3", "HCl"}): _reaction(
        "bubble",
        "Na2CO3(aq) + 2HCl(aq) -> 2NaCl(aq) + CO2(g) + H2O(l)",
        (
            "Sodium carbonate reacts with hydrochloric acid to form sodium "
            "chloride, carbon dioxide, and water. Carbon dioxide escaping "
            "from the solution causes bubbling. Two hydrogen ions are needed "
            "for each carbonate ion in the balanced equation."
        ),
        (
            "Wear splash goggles and acid-resistant gloves.",
            "Add hydrochloric acid slowly to control foaming and heat.",
            "Keep the vessel open and work in a ventilated area.",
        ),
    ),
    frozenset({"BaCl2", "Na2CO3"}): _reaction(
        "none",
        "BaCl2(aq) + Na2CO3(aq) -> BaCO3(s) + 2NaCl(aq)",
        (
            "Barium chloride and sodium carbonate exchange ions to form "
            "insoluble barium carbonate. The white precipitate removes "
            "barium ions from the solution while sodium and chloride ions "
            "remain dissolved. The reactants combine in a one-to-one ratio."
        ),
        (
            "Treat soluble barium compounds as toxic and avoid all ingestion.",
            "Wear gloves and splash goggles throughout the procedure.",
            "Collect all barium-containing material as hazardous waste.",
        ),
    ),
    frozenset({"Zn", "HCl"}): _reaction(
        "bubble",
        "Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g)",
        (
            "Zinc displaces hydrogen from hydrochloric acid to form zinc "
            "chloride and hydrogen gas. The bubbles are hydrogen leaving the "
            "solution. Zinc is oxidized while hydrogen ions are reduced in "
            "this single-displacement reaction."
        ),
        (
            "Keep flames and sparks away from the hydrogen produced.",
            "Work in a ventilated area under trained supervision.",
            "Wear acid-resistant gloves and splash goggles.",
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
