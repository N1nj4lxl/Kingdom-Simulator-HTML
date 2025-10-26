"""Tkinter-based single window experience for the Kingdom Simulator."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from functools import partial

from game_state import GameState, format_percentage


class BaseView(ttk.Frame):
    """Common frame features shared by all screens."""

    title: str = ""

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, padding=12, **kwargs)
        self.app = app
        self.state = app.state
        if self.title:
            header = ttk.Label(self, text=self.title, style="ViewHeading.TLabel")
            header.pack(anchor="w", pady=(0, 12))

    def refresh(self) -> None:  # pragma: no cover - UI only
        """Called whenever the global state changes."""


class CharacterCreationView(BaseView):
    title = "Character Creation"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)

        self.ruler_var = tk.StringVar(value=self.state.ruler_name)
        self.kingdom_var = tk.StringVar(value=self.state.kingdom_name)
        self.trait_var = tk.StringVar(value=self.state.ruler_trait)

        ttk.Label(self, text="Define your monarch and the fledgling kingdom.").pack(
            anchor="w"
        )

        form = ttk.Frame(self)
        form.pack(anchor="w", pady=16)

        ttk.Label(form, text="Ruler Name:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.ruler_var, width=24).grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(form, text="Signature Trait:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.OptionMenu(
            form,
            self.trait_var,
            self.trait_var.get(),
            "Balanced",
            "Just",
            "Ambitious",
            "Merciful",
            "Strategist",
        ).grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="Kingdom Name:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.kingdom_var, width=24).grid(
            row=2, column=1, sticky="w"
        )

        ttk.Button(self, text="Begin Reign", command=self._apply_changes).pack(
            anchor="w", pady=(12, 0)
        )

        self.summary = ttk.Label(self, text="", style="Summary.TLabel", wraplength=380)
        self.summary.pack(anchor="w", pady=(16, 0))

    def _apply_changes(self) -> None:
        self.state.ruler_name = self.ruler_var.get() or "Unnamed Sovereign"
        self.state.kingdom_name = self.kingdom_var.get() or "New Kingdom"
        self.state.ruler_trait = self.trait_var.get()
        self.state.log(
            f"{self.state.ruler_name} ascends as ruler of {self.state.kingdom_name} with a {self.state.ruler_trait.lower()} outlook."
        )
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        trait = self.state.ruler_trait
        message = (
            f"Ruler: {self.state.ruler_name}\n"
            f"Kingdom: {self.state.kingdom_name}\n"
            f"Trait: {trait}"
        )
        self.summary.config(text=message)


class DashboardView(BaseView):
    title = "Kingdom Management"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)

        self.gold_var = tk.StringVar()
        self.food_var = tk.StringVar()
        self.prestige_var = tk.StringVar()
        self.stability_var = tk.StringVar()
        self.population_var = tk.StringVar()
        self.era_var = tk.StringVar()

        metrics = ttk.Frame(self)
        metrics.pack(fill="x")
        for row, (label, var) in enumerate(
            (
                ("Era", self.era_var),
                ("Treasury", self.gold_var),
                ("Food Stores", self.food_var),
                ("Prestige", self.prestige_var),
                ("Stability", self.stability_var),
                ("Population", self.population_var),
            )
        ):
            ttk.Label(metrics, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Label(metrics, textvariable=var).grid(row=row, column=1, sticky="w", pady=2)

        actions = ttk.Frame(self)
        actions.pack(anchor="w", pady=(16, 0))
        ttk.Button(actions, text="Collect Taxes", command=self._collect_taxes).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(actions, text="Hold Festival", command=self._hold_festival).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(actions, text="Advance Turn", command=self._advance_turn).grid(
            row=0, column=2
        )

        ttk.Label(self, text="Recent Events:").pack(anchor="w", pady=(16, 4))
        self.events_box = tk.Listbox(self, height=8)
        self.events_box.pack(fill="both", expand=True)

    def _collect_taxes(self) -> None:
        self.state.collect_taxes()
        self.app.refresh_all()

    def _hold_festival(self) -> None:
        self.state.hold_festival()
        self.app.refresh_all()

    def _advance_turn(self) -> None:
        self.state.next_turn()
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self.gold_var.set(f"{self.state.gold} gold")
        self.food_var.set(f"{self.state.food} food")
        self.prestige_var.set(str(self.state.prestige))
        self.stability_var.set(format_percentage(self.state.stability))
        self.population_var.set(f"{self.state.total_population}")
        self.era_var.set(self.state.era)

        self.events_box.delete(0, tk.END)
        for event in self.state.notifications:
            self.events_box.insert(tk.END, event)


class LawCouncilView(BaseView):
    title = "Law Council"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)
        self.cards: Dict[str, ttk.Label] = {}

        ttk.Label(
            self,
            text="Draft and enact laws to guide the realm. Each law applies unique modifiers.",
            wraplength=420,
        ).pack(anchor="w", pady=(0, 12))

        self.cards_frame = ttk.Frame(self)
        self.cards_frame.pack(fill="both", expand=True)
        self.refresh()

    def _render_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        for row, law in enumerate(self.state.laws.values()):
            frame = ttk.Frame(self.cards_frame, padding=8, relief="ridge")
            frame.grid(row=row, column=0, sticky="ew", pady=4)
            frame.columnconfigure(0, weight=1)
            title = f"{law.name} ({'Enacted' if law.enacted else 'Pending'})"
            ttk.Label(frame, text=title, style="Summary.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(frame, text=law.description, wraplength=360).grid(
                row=1, column=0, sticky="w", pady=(4, 6)
            )
            details = f"Cost: {law.cost} gold | Stability {law.stability_effect:+.2f} | Food {law.food_modifier:+.2f} | Gold {law.gold_modifier:+.2f}"
            ttk.Label(frame, text=details, style="Details.TLabel").grid(
                row=2, column=0, sticky="w"
            )
            ttk.Button(
                frame,
                text="Enact" if not law.enacted else "Already Law",
                command=partial(self._enact_law, law.key),
                state=tk.NORMAL if not law.enacted else tk.DISABLED,
            ).grid(row=0, column=1, rowspan=3, padx=(12, 0))

    def _enact_law(self, key: str) -> None:
        self.state.enact_law(key)
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self._render_cards()


class FoodManagementView(BaseView):
    title = "Food Management"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)

        ttk.Label(
            self,
            text="Balance agricultural focus to feed your population.",
        ).pack(anchor="w")

        self.slider = ttk.Scale(
            self,
            from_=0.1,
            to=0.9,
            value=self.state.food_focus,
            command=self._on_slider,
        )
        self.slider.pack(fill="x", pady=12)

        self.focus_var = tk.StringVar()
        ttk.Label(self, textvariable=self.focus_var, style="Summary.TLabel").pack(
            anchor="w"
        )

        self.production_var = tk.StringVar()
        self.consumption_var = tk.StringVar()
        info = ttk.Frame(self)
        info.pack(anchor="w", pady=(16, 0))
        ttk.Label(info, text="Expected Production:").grid(row=0, column=0, sticky="w")
        ttk.Label(info, textvariable=self.production_var).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(info, text="Population Consumption:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Label(info, textvariable=self.consumption_var).grid(
            row=1, column=1, sticky="w"
        )

        ttk.Button(self, text="Commit Policy", command=self._commit_policy).pack(
            anchor="w", pady=(20, 0)
        )

    def _on_slider(self, _value: str) -> None:
        self._update_preview(float(_value))

    def _update_preview(self, focus: float) -> None:
        production = int(200 * focus)
        modifiers = sum(law.food_modifier for law in self.state.laws.values() if law.enacted)
        production += int(production * modifiers)
        production += sum(
            region.food_yield for region in self.state.conquered_regions if region.key != "capital"
        )
        consumption = int(self.state.total_population * 0.6)
        self.focus_var.set(f"Food focus at {format_percentage(focus)}")
        self.production_var.set(f"{production} units")
        self.consumption_var.set(f"{consumption} units")

    def _commit_policy(self) -> None:
        focus = float(self.slider.get())
        self.state.set_food_focus(focus)
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self.slider.set(self.state.food_focus)
        self._update_preview(self.state.food_focus)


class PopulationView(BaseView):
    title = "Population Management"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)
        ttk.Label(
            self,
            text="Adjust rationing and monitor the satisfaction of each social class.",
            wraplength=420,
        ).pack(anchor="w")

        self.group_frames: Dict[str, ttk.Frame] = {}
        self.refresh()

    def _render_groups(self) -> None:
        for child in self.winfo_children()[1:]:
            if isinstance(child, ttk.Frame):
                child.destroy()
        for group in self.state.population.values():
            frame = ttk.Frame(self, padding=8, relief="solid")
            frame.pack(fill="x", pady=6)
            ttk.Label(frame, text=group.name, style="Summary.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(
                frame,
                text=f"Size: {group.size} | Happiness: {format_percentage(group.happiness)}",
            ).grid(row=1, column=0, sticky="w", pady=(4, 8))
            ttk.Button(
                frame,
                text="Increase Rations",
                command=partial(self._adjust, group.name, 0.05),
            ).grid(row=0, column=1, padx=6)
            ttk.Button(
                frame,
                text="Reduce Rations",
                command=partial(self._adjust, group.name, -0.05),
            ).grid(row=1, column=1, padx=6)

    def _adjust(self, name: str, delta: float) -> None:
        self.state.adjust_population_policy(name, delta)
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self._render_groups()


class ArmyView(BaseView):
    title = "Army Management"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)
        self.tree = ttk.Treeview(
            self,
            columns=("soldiers", "morale", "weapon"),
            show="headings",
            height=6,
        )
        self.tree.heading("soldiers", text="Soldiers")
        self.tree.heading("morale", text="Morale")
        self.tree.heading("weapon", text="Weapon")
        self.tree.pack(fill="x", pady=12)

        controls = ttk.Frame(self)
        controls.pack(anchor="w", pady=8)
        ttk.Button(controls, text="Train Selected", command=self._train).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Label(controls, text="Equip with:").grid(row=0, column=1, padx=(0, 6))
        self.weapon_var = tk.StringVar(value="bronze_weapons")
        weapon_choices = [tech.key for tech in self.state.weapons.values()]
        self.weapon_menu = ttk.OptionMenu(
            controls, self.weapon_var, self.weapon_var.get(), *weapon_choices
        )
        self.weapon_menu.grid(row=0, column=2, padx=(0, 8))
        ttk.Button(controls, text="Assign Weapon", command=self._assign_weapon).grid(
            row=0, column=3
        )

    def _selected_index(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def _train(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        self.state.train_army(index)
        self.app.refresh_all()

    def _assign_weapon(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        self.state.assign_weapon_to_army(index, self.weapon_var.get())
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, army in enumerate(self.state.armies):
            weapon_name = self.state.weapons[army.weapon_key].name
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(army.soldiers, format_percentage(army.morale), weapon_name),
            )
        unlocked = [tech.key for tech in self.state.weapons.values() if tech.unlocked]
        menu = self.weapon_menu["menu"]
        menu.delete(0, "end")
        for option in unlocked:
            menu.add_command(
                label=option,
                command=lambda value=option: self.weapon_var.set(value),
            )
        if self.weapon_var.get() not in unlocked and unlocked:
            self.weapon_var.set(unlocked[0])


class WeaponsView(BaseView):
    title = "Weapons Workshop"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)
        ttk.Label(
            self,
            text="Invest in research to unlock superior weaponry.",
        ).pack(anchor="w")

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, pady=12)
        self.refresh()

    def _render(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()
        for row, tech in enumerate(self.state.weapons.values()):
            frame = ttk.Frame(self.container, padding=6, relief="groove")
            frame.grid(row=row, column=0, sticky="ew", pady=4)
            ttk.Label(frame, text=tech.name, style="Summary.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            status = "Unlocked" if tech.unlocked else f"Cost: {tech.research_cost}"
            ttk.Label(frame, text=status).grid(row=0, column=1, sticky="w", padx=8)
            ttk.Label(frame, text=tech.description, wraplength=360).grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(4, 6)
            )
            ttk.Button(
                frame,
                text="Research" if not tech.unlocked else "Available",
                state=tk.NORMAL if not tech.unlocked else tk.DISABLED,
                command=partial(self._research, tech.key),
            ).grid(row=0, column=2, rowspan=2, padx=(12, 0))

    def _research(self, key: str) -> None:
        self.state.research_weapon(key)
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self._render()


class ConquestView(BaseView):
    title = "Conquest Planner"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)
        ttk.Label(
            self,
            text="Select neighbouring regions to expand your realm. Campaign outcomes depend on stability and army strength.",
            wraplength=420,
        ).pack(anchor="w")

        self.listbox = tk.Listbox(self, height=8)
        self.listbox.pack(fill="x", pady=12)

        ttk.Button(self, text="Launch Campaign", command=self._attack).pack(anchor="w")

    def _attack(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        region_key = self.listbox.get(selection[0]).split(" | ")[0]
        self.state.attempt_conquest(region_key)
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self.listbox.delete(0, tk.END)
        for region in self.state.available_regions:
            self.listbox.insert(
                tk.END,
                f"{region.key} | {region.name} | Terrain: {region.terrain} | Food: {region.food_yield}",
            )
        if not self.state.available_regions:
            self.listbox.insert(tk.END, "All known regions pledge allegiance.")


class EraView(BaseView):
    title = "Era Progression"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)

        self.current_var = tk.StringVar()
        self.next_var = tk.StringVar()
        self.requirement_var = tk.StringVar()

        ttk.Label(self, textvariable=self.current_var, style="Summary.TLabel").pack(
            anchor="w"
        )
        ttk.Label(self, textvariable=self.next_var).pack(anchor="w", pady=(8, 4))
        ttk.Label(self, textvariable=self.requirement_var, style="Details.TLabel").pack(
            anchor="w"
        )
        ttk.Button(self, text="Advance Era", command=self._advance).pack(
            anchor="w", pady=(12, 0)
        )

    def _advance(self) -> None:
        self.state.advance_era()
        self.app.refresh_all()

    def refresh(self) -> None:  # pragma: no cover - UI only
        self.current_var.set(f"Current Era: {self.state.era}")
        if self.state.era_index < len(self.state.ERAS) - 1:
            next_era = self.state.ERAS[self.state.era_index + 1]
            required = 20 + self.state.era_index * 15
            self.next_var.set(f"Next Era: {next_era}")
            self.requirement_var.set(
                f"Requires prestige {required} (current {self.state.prestige})."
            )
        else:
            self.next_var.set("You have reached the final era.")
            self.requirement_var.set("")


class CheatConsoleView(BaseView):
    title = "Cheat Console"

    def __init__(self, master: tk.Misc, app: "MainApplication", **kwargs) -> None:
        super().__init__(master, app, **kwargs)
        ttk.Label(
            self,
            text="Enter developer commands to experiment. Example: 'add_gold 200'.",
            wraplength=420,
        ).pack(anchor="w")

        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill="x", pady=12)
        self.command_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.command_var).pack(side="left", fill="x", expand=True)
        ttk.Button(entry_frame, text="Execute", command=self._run).pack(side="left", padx=(8, 0))

        self.result_var = tk.StringVar()
        ttk.Label(self, textvariable=self.result_var, style="Summary.TLabel").pack(
            anchor="w"
        )

    def _run(self) -> None:
        response = self.state.apply_cheat(self.command_var.get())
        self.result_var.set(response)
        self.command_var.set("")
        self.app.refresh_all()


class MainApplication(tk.Tk):
    """Top-level Tkinter window hosting all subsystems."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Kingdom Simulator")
        self.geometry("960x640")
        self.minsize(920, 580)

        style = ttk.Style(self)
        style.configure("ViewHeading.TLabel", font=("Georgia", 16, "bold"))
        style.configure("Summary.TLabel", font=("Georgia", 12, "bold"))
        style.configure("Details.TLabel", foreground="#555")

        self.state = GameState()

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    # -- layout -----------------------------------------------------------------

    def _build_sidebar(self) -> None:
        sidebar = ttk.Frame(self, padding=12, relief="ridge")
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.rowconfigure(10, weight=1)

        ttk.Label(sidebar, textvariable=self._kingdom_label(), style="Summary.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        buttons = [
            ("Character", "character"),
            ("Dashboard", "dashboard"),
            ("Laws", "laws"),
            ("Food", "food"),
            ("Population", "population"),
            ("Armies", "armies"),
            ("Weapons", "weapons"),
            ("Conquest", "conquest"),
            ("Eras", "eras"),
            ("Cheats", "cheats"),
        ]
        for row, (label, key) in enumerate(buttons, start=1):
            ttk.Button(sidebar, text=label, width=18, command=partial(self.show_view, key)).grid(
                row=row, column=0, pady=2, sticky="ew"
            )

    def _build_main_area(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.grid(row=0, column=1, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.view_container = ttk.Frame(container)
        self.view_container.grid(row=0, column=0, sticky="nsew")

        self.views: Dict[str, BaseView] = {
            "character": CharacterCreationView(self.view_container, self),
            "dashboard": DashboardView(self.view_container, self),
            "laws": LawCouncilView(self.view_container, self),
            "food": FoodManagementView(self.view_container, self),
            "population": PopulationView(self.view_container, self),
            "armies": ArmyView(self.view_container, self),
            "weapons": WeaponsView(self.view_container, self),
            "conquest": ConquestView(self.view_container, self),
            "eras": EraView(self.view_container, self),
            "cheats": CheatConsoleView(self.view_container, self),
        }

        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

        self.current_view = "character"
        self.show_view("character")

    # -- helpers -----------------------------------------------------------------

    def _kingdom_label(self) -> tk.StringVar:
        self.kingdom_var = tk.StringVar()
        self.kingdom_var.set(f"{self.state.kingdom_name}\nEra: {self.state.era}")
        return self.kingdom_var

    def show_view(self, key: str) -> None:
        self.current_view = key
        view = self.views[key]
        view.tkraise()
        view.refresh()

    def refresh_all(self) -> None:
        self.kingdom_var.set(f"{self.state.kingdom_name}\nEra: {self.state.era}")
        for view in self.views.values():
            view.refresh()


def main() -> None:  # pragma: no cover - convenience entry point
    app = MainApplication()
    app.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()

