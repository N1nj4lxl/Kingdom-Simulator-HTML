"""Core game state models and logic for the Kingdom Simulator.

The module keeps the simulation rules isolated from the user interface so that
the UI can simply invoke high level helpers and refresh its widgets.  While the
simulation is intentionally lightweight compared to a full strategy title, it
captures the major systems requested in the original design brief: kingdom
management, food and population balancing, law making, conquests, army and
weapon progression, and a cheat console for experimentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import random


# ---------------------------------------------------------------------------
# Data models


@dataclass
class PopulationGroup:
    name: str
    size: int
    happiness: float  # range 0-1

    def adjust(self, delta_size: int = 0, delta_happiness: float = 0.0) -> None:
        self.size = max(0, self.size + delta_size)
        self.happiness = min(1.0, max(0.0, self.happiness + delta_happiness))


@dataclass
class Law:
    key: str
    name: str
    description: str
    cost: int
    stability_effect: float = 0.0
    food_modifier: float = 0.0
    gold_modifier: float = 0.0
    happiness_modifier: float = 0.0
    enacted: bool = False


@dataclass
class WeaponTech:
    key: str
    name: str
    description: str
    research_cost: int
    attack_bonus: float
    unlocked: bool = False


@dataclass
class Army:
    name: str
    soldiers: int
    morale: float
    weapon_key: str

    def train(self, recruits: int, morale_boost: float) -> None:
        self.soldiers = max(0, self.soldiers + recruits)
        self.morale = min(1.0, self.morale + morale_boost)


@dataclass
class Region:
    key: str
    name: str
    terrain: str
    food_yield: int
    prestige_reward: int
    conquered: bool = False


# ---------------------------------------------------------------------------
# Game state and logic helpers


class GameState:
    """Container for all mutable simulation data."""

    ERAS: Tuple[str, ...] = (
        "Age of Foundations",
        "Age of Expansion",
        "Age of Discovery",
        "Age of Steam",
        "Age of Revolution",
    )

    def __init__(self) -> None:
        self.ruler_name: str = "Unnamed Sovereign"
        self.ruler_trait: str = "Balanced"
        self.kingdom_name: str = "New Kingdom"

        self.turn: int = 1
        self.era_index: int = 0

        self.gold: int = 500
        self.food: int = 400
        self.prestige: int = 15
        self.stability: float = 0.65

        self.food_focus: float = 0.5  # 0..1: share of resources devoted to food
        self.population: Dict[str, PopulationGroup] = {
            "Peasants": PopulationGroup("Peasants", 850, 0.55),
            "Artisans": PopulationGroup("Artisans", 180, 0.6),
            "Nobles": PopulationGroup("Nobles", 45, 0.7),
            "Soldiers": PopulationGroup("Soldiers", 120, 0.65),
        }

        self.laws: Dict[str, Law] = {law.key: law for law in self._default_laws()}
        self.weapons: Dict[str, WeaponTech] = {
            tech.key: tech for tech in self._default_weapons()
        }

        self.armies: List[Army] = [
            Army("Royal Guard", 160, 0.72, "bronze_weapons"),
            Army("Frontier Watch", 120, 0.6, "bronze_weapons"),
        ]

        self.regions: Dict[str, Region] = {
            region.key: region for region in self._default_regions()
        }
        # Capital starts conquered by default
        self.regions["capital"].conquered = True

        self.notifications: List[str] = [
            "Your reign begins. Maintain stability and guide the realm to glory!"
        ]

    # -- factories ----------------------------------------------------------------

    @staticmethod
    def _default_laws() -> List[Law]:
        return [
            Law(
                key="grain_subsidies",
                name="Grain Subsidies",
                description="Reduce famine risk by purchasing grain reserves.",
                cost=80,
                food_modifier=0.1,
                stability_effect=0.03,
            ),
            Law(
                key="levy_reform",
                name="Levy Reform",
                description="Professionalises the army, increasing upkeep but raising morale.",
                cost=120,
                happiness_modifier=-0.03,
                stability_effect=0.05,
            ),
            Law(
                key="merchant_charters",
                name="Merchant Charters",
                description="Encourage trade guilds, boosting gold income.",
                cost=150,
                gold_modifier=0.12,
            ),
            Law(
                key="codified_laws",
                name="Codified Laws",
                description="Establish a legal code to settle disputes peacefully.",
                cost=100,
                stability_effect=0.07,
                happiness_modifier=0.04,
            ),
        ]

    @staticmethod
    def _default_weapons() -> List[WeaponTech]:
        return [
            WeaponTech(
                key="bronze_weapons",
                name="Bronze Weapons",
                description="Baseline armament for the kingdom's troops.",
                research_cost=0,
                attack_bonus=0.0,
                unlocked=True,
            ),
            WeaponTech(
                key="iron_weapons",
                name="Iron Forging",
                description="Improved metallurgy increases soldier effectiveness.",
                research_cost=200,
                attack_bonus=0.15,
            ),
            WeaponTech(
                key="crossbows",
                name="Crossbows",
                description="Powerful ranged weaponry expands tactical options.",
                research_cost=260,
                attack_bonus=0.22,
            ),
            WeaponTech(
                key="gunpowder",
                name="Gunpowder",
                description="Firearms revolutionise warfare in later eras.",
                research_cost=400,
                attack_bonus=0.35,
            ),
        ]

    @staticmethod
    def _default_regions() -> List[Region]:
        return [
            Region(
                key="capital",
                name="Crownlands",
                terrain="fertile plains",
                food_yield=120,
                prestige_reward=0,
                conquered=True,
            ),
            Region(
                key="stormcoast",
                name="Stormcoast",
                terrain="rocky shoreline",
                food_yield=60,
                prestige_reward=10,
            ),
            Region(
                key="sunvale",
                name="Sunvale",
                terrain="sun-drenched valley",
                food_yield=90,
                prestige_reward=12,
            ),
            Region(
                key="ironridge",
                name="Ironridge",
                terrain="mountain pass",
                food_yield=45,
                prestige_reward=18,
            ),
            Region(
                key="emerald_woods",
                name="Emerald Woods",
                terrain="ancient forest",
                food_yield=70,
                prestige_reward=15,
            ),
        ]

    # -- helper properties ---------------------------------------------------------

    @property
    def era(self) -> str:
        return self.ERAS[self.era_index]

    @property
    def total_population(self) -> int:
        return sum(group.size for group in self.population.values())

    @property
    def conquered_regions(self) -> List[Region]:
        return [region for region in self.regions.values() if region.conquered]

    @property
    def available_regions(self) -> List[Region]:
        return [region for region in self.regions.values() if not region.conquered]

    # -- logging -------------------------------------------------------------------

    def log(self, message: str) -> None:
        self.notifications.insert(0, f"Turn {self.turn}: {message}")
        self.notifications = self.notifications[:20]

    # -- core actions ---------------------------------------------------------------

    def collect_taxes(self) -> None:
        tax_multiplier = 1.0 + sum(
            law.gold_modifier for law in self.laws.values() if law.enacted
        )
        income = int(40 * tax_multiplier)
        self.gold += income
        for group in self.population.values():
            group.adjust(delta_happiness=-0.01)
        self.stability = max(0.0, self.stability - 0.01)
        self.log(f"Collected taxes: +{income} gold. Stability and happiness dip slightly.")

    def hold_festival(self) -> None:
        cost = 60
        if self.gold < cost:
            self.log("Insufficient gold to host a festival.")
            return
        self.gold -= cost
        for group in self.population.values():
            group.adjust(delta_happiness=0.05)
        self.stability = min(1.0, self.stability + 0.04)
        self.log("Hosted a grand festival raising spirits across the realm.")

    def enact_law(self, law_key: str) -> None:
        law = self.laws.get(law_key)
        if not law:
            self.log("Unknown law.")
            return
        if law.enacted:
            self.log(f"{law.name} is already part of the legal code.")
            return
        if self.gold < law.cost:
            self.log("Not enough gold to pass this legislation.")
            return
        self.gold -= law.cost
        law.enacted = True
        self.stability = min(1.0, self.stability + law.stability_effect)
        for group in self.population.values():
            group.adjust(delta_happiness=law.happiness_modifier)
        self.log(f"Enacted the law '{law.name}'.")

    def research_weapon(self, weapon_key: str) -> None:
        weapon = self.weapons.get(weapon_key)
        if not weapon:
            self.log("Unknown weapon technology.")
            return
        if weapon.unlocked:
            self.log(f"{weapon.name} is already researched.")
            return
        if self.gold < weapon.research_cost:
            self.log("Insufficient gold to research this technology.")
            return
        self.gold -= weapon.research_cost
        weapon.unlocked = True
        self.prestige += 5
        self.log(f"Researchers complete studies into {weapon.name} technology!")

    def assign_weapon_to_army(self, army_index: int, weapon_key: str) -> None:
        if weapon_key not in self.weapons or not self.weapons[weapon_key].unlocked:
            self.log("The selected weapon technology is not available.")
            return
        try:
            army = self.armies[army_index]
        except IndexError:
            self.log("Army not found.")
            return
        army.weapon_key = weapon_key
        army.morale = min(1.0, army.morale + 0.05)
        self.log(f"{army.name} reequipped with {self.weapons[weapon_key].name}.")

    def train_army(self, army_index: int) -> None:
        try:
            army = self.armies[army_index]
        except IndexError:
            self.log("Army not found.")
            return
        cost = 45
        if self.gold < cost:
            self.log("Insufficient gold to train this army.")
            return
        self.gold -= cost
        army.train(recruits=20, morale_boost=0.04)
        self.population["Soldiers"].adjust(delta_size=20, delta_happiness=0.02)
        self.log(f"{army.name} drills hard, adding recruits and boosting morale.")

    def set_food_focus(self, value: float) -> None:
        self.food_focus = min(1.0, max(0.0, value))
        self.log(
            f"Adjusted agricultural policy to devote {int(self.food_focus * 100)}% of resources to food production."
        )

    def adjust_population_policy(self, group_name: str, ration_change: float) -> None:
        group = self.population.get(group_name)
        if not group:
            self.log("Population group not found.")
            return
        group.adjust(delta_happiness=ration_change)
        stability_delta = ration_change * 0.5
        self.stability = min(1.0, max(0.0, self.stability + stability_delta))
        trend = "improves" if ration_change > 0 else "declines"
        self.log(f"Ration policy for {group_name} {trend}, altering morale and stability.")

    def attempt_conquest(self, region_key: str) -> None:
        region = self.regions.get(region_key)
        if not region:
            self.log("Target region unknown.")
            return
        if region.conquered:
            self.log("That region already swears fealty to the crown.")
            return
        required_armies = max(1, len(self.conquered_regions) // 2)
        if len(self.armies) < required_armies:
            self.log("You need more armies to project power that far.")
            return

        campaign_cost = 90
        if self.gold < campaign_cost:
            self.log("Insufficient gold to wage a campaign there.")
            return
        self.gold -= campaign_cost

        attack_rating = sum(
            army.soldiers * (1 + self.weapons[army.weapon_key].attack_bonus)
            for army in self.armies
        )
        attack_rating *= self.stability + 0.5
        defense = 250 + region.prestige_reward * 5

        roll = random.uniform(0.8, 1.2) * attack_rating
        if roll > defense:
            region.conquered = True
            self.food += region.food_yield
            self.prestige += region.prestige_reward
            self.log(
                f"Victory! {region.name} is annexed, yielding {region.food_yield} food and {region.prestige_reward} prestige."
            )
        else:
            for army in self.armies:
                army.train(recruits=-15, morale_boost=-0.05)
            self.stability = max(0.0, self.stability - 0.04)
            self.log(
                f"The campaign in {region.name} falters; forces retreat with casualties."
            )

    def advance_era(self) -> None:
        if self.era_index >= len(self.ERAS) - 1:
            self.log("You already stand at the pinnacle of progress.")
            return
        required_prestige = 20 + self.era_index * 15
        if self.prestige < required_prestige:
            self.log("Not enough prestige to usher in a new era.")
            return
        self.era_index += 1
        self.stability = min(1.0, self.stability + 0.05)
        self.log(f"The realm enters the {self.era}! New opportunities unfold.")

    def next_turn(self) -> None:
        base_food_production = int(200 * self.food_focus)
        law_food_bonus = int(
            base_food_production
            * sum(law.food_modifier for law in self.laws.values() if law.enacted)
        )
        region_food = sum(
            region.food_yield for region in self.conquered_regions if region.key != "capital"
        )
        production = base_food_production + law_food_bonus + region_food

        consumption = int(self.total_population * 0.6)
        self.food += production - consumption

        gold_income = 45 + int(self.total_population * 0.05)
        gold_income = int(
            gold_income
            * (1.0 + sum(law.gold_modifier for law in self.laws.values() if law.enacted))
        )
        upkeep = 30 + len(self.armies) * 12
        net_gold = gold_income - upkeep
        self.gold += net_gold

        # Population morale consequences
        if self.food < 0:
            shortage = -self.food
            for group in self.population.values():
                group.adjust(delta_happiness=-0.08)
            self.stability = max(0.0, self.stability - 0.06)
            self.log(
                f"Food stores run dry ({shortage} deficit)! Unrest spreads among the populace."
            )
            self.food = 0
        else:
            for group in self.population.values():
                group.adjust(delta_happiness=0.01)

        # Population growth and attrition
        for group in self.population.values():
            growth_rate = 0.01 + (group.happiness - 0.5) * 0.05
            delta = int(group.size * growth_rate)
            group.adjust(delta_size=delta)

        self.prestige = max(0, self.prestige + len(self.conquered_regions) - 1)

        # Stability drifts toward average happiness
        avg_happiness = sum(g.happiness for g in self.population.values()) / max(
            1, len(self.population)
        )
        self.stability += (avg_happiness - self.stability) * 0.1
        self.stability = min(1.0, max(0.0, self.stability))

        self.turn += 1
        self.log(
            "A new season passes: resources updated, morale shifts, and the court awaits new directives."
        )

    # -- cheats --------------------------------------------------------------------

    def apply_cheat(self, command: str) -> str:
        """Parse and apply a cheat command.

        Supported commands:
            add_gold <amount>
            add_food <amount>
            unlock_weapon <key>
            win_conquest <region_key>
            set_era <index>
        """

        tokens = command.strip().split()
        if not tokens:
            return "No command provided."

        action = tokens[0].lower()
        args = tokens[1:]

        if action == "add_gold" and args:
            amount = int(args[0])
            self.gold += amount
            self.log(f"Cheat: Treasury flooded with {amount} gold coins.")
            return "Gold added."
        if action == "add_food" and args:
            amount = int(args[0])
            self.food += amount
            self.log(f"Cheat: Granaries receive {amount} food reserves.")
            return "Food added."
        if action == "unlock_weapon" and args:
            key = args[0]
            weapon = self.weapons.get(key)
            if not weapon:
                return "Weapon key not recognised."
            weapon.unlocked = True
            self.log(f"Cheat: Weapon technology '{weapon.name}' instantly mastered.")
            return "Weapon unlocked."
        if action == "win_conquest" and args:
            region = self.regions.get(args[0])
            if not region:
                return "Region key not recognised."
            region.conquered = True
            self.food += region.food_yield
            self.prestige += region.prestige_reward
            self.log(f"Cheat: {region.name} swears loyalty without a fight.")
            return "Region conquered."
        if action == "set_era" and args:
            index = max(0, min(len(self.ERAS) - 1, int(args[0])))
            self.era_index = index
            self.log(f"Cheat: Era adjusted to {self.era}.")
            return "Era set."

        return "Unknown or malformed cheat command."


def format_percentage(value: float) -> str:
    return f"{int(value * 100)}%"


def format_happiness(value: float) -> str:
    return f"{int(value * 100)} / 100"

