import tkinter as tk
from tkinter import ttk

from src import config
from src.engine import FuzzyAdvisor
from src.gui.panels import InputPanel, PlotFrame, ResultPanel, RulesTable
from src.plots import plot_aggregation, plot_memberships, plot_surface
from src.validation import InputError


class App(tk.Tk):
    """Main desktop application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Bahria University Handbook Fuzzy Advisor (Spring 2026)")
        self.geometry("1180x820")
        self.minsize(980, 700)

        self.advisor = FuzzyAdvisor()

        self._configure_styles()
        self._build_tabs()

    def _configure_styles(self) -> None:
        """Apply ttk styling for a clean desktop presentation."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", tabposition="nw")
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[12, 6])
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", font=("Segoe UI", 9))

    def _build_tabs(self) -> None:
        """Build the top-level notebook tabs."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        tab_probation = ttk.Frame(notebook)
        tab_scholarship = ttk.Frame(notebook)
        tab_mfs = ttk.Frame(notebook)

        notebook.add(tab_probation, text="Probation & Drop")
        notebook.add(tab_scholarship, text="Scholarship Retention")
        notebook.add(tab_mfs, text="Membership Functions")

        self._build_probation_tab(tab_probation)
        self._build_scholarship_tab(tab_scholarship)
        self._build_mfs_tab(tab_mfs)

    def _build_probation_tab(self, parent: ttk.Frame) -> None:
        """Build Domain A: Probation & Drop layout."""
        top_frame = ttk.Frame(parent)
        top_frame.pack(side="top", fill="x", padx=6, pady=4)

        prob_fields = [
            {
                "name": "cgpa",
                "label": "Student CGPA (0.00 – 4.00):",
                "type": "entry",
                "default": "1.99",
            },
            {
                "name": "probation_count",
                "label": "Consecutive Probation Count:",
                "type": "combobox",
                "options": [str(c) for c in config.PROBATION_COUNTS],
                "default": "0",
            },
        ]
        self.prob_input = InputPanel(
            top_frame,
            title="Domain A: Academic Inputs",
            fields=prob_fields,
            on_evaluate=self._on_evaluate_probation,
            on_clear=self._on_clear_probation,
        )
        self.prob_input.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.prob_result = ResultPanel(top_frame)
        self.prob_result.pack(side="right", fill="both", expand=True, padx=4, pady=4)

        self.prob_rules = RulesTable(parent)
        self.prob_rules.pack(side="top", fill="x", padx=10, pady=4)

        self.prob_plot = PlotFrame(parent, title="Fuzzy Inference: Aggregated Consequent & Centroid")
        self.prob_plot.pack(side="bottom", fill="both", expand=True, padx=10, pady=6)

    def _on_evaluate_probation(self) -> None:
        """Handle evaluation callback for Domain A."""
        vals = self.prob_input.get_values()
        try:
            res = self.advisor.evaluate(
                "probation",
                cgpa=vals.get("cgpa", ""),
                probation_count=vals.get("probation_count", ""),
            )
            self.prob_result.display_result(res)
            self.prob_rules.update_rules(res.fired_rules)
            fig = plot_aggregation(
                "probation",
                cgpa=res.inputs["cgpa"],
                probation_count=res.inputs["probation_count"],
            )
            self.prob_plot.update_figure(fig)
        except InputError as err:
            self.prob_result.display_error(str(err))
            self.prob_rules.clear()
            self.prob_plot.clear()

    def _on_clear_probation(self) -> None:
        """Handle clear callback for Domain A."""
        self.prob_input.clear()
        self.prob_result.clear()
        self.prob_rules.clear()
        self.prob_plot.clear()

    def _build_scholarship_tab(self, parent: ttk.Frame) -> None:
        """Build Domain B: Scholarship Retention layout."""
        top_frame = ttk.Frame(parent)
        top_frame.pack(side="top", fill="x", padx=6, pady=4)

        types = list(config.SCHOLARSHIP_THRESHOLDS.keys())
        sch_fields = [
            {
                "name": "scholarship_type",
                "label": "Scholarship Category:",
                "type": "combobox",
                "options": types,
                "default": types[0],
            },
            {
                "name": "cgpa",
                "label": "Current GPA / CGPA (0.00 – 4.00):",
                "type": "entry",
                "default": "3.75",
            },
            {
                "name": "credit_hours",
                "label": "Registered Credit Hours (0 – 18):",
                "type": "entry",
                "default": "12",
            },
        ]
        self.sch_input = InputPanel(
            top_frame,
            title="Domain B: Scholarship Inputs",
            fields=sch_fields,
            on_evaluate=self._on_evaluate_scholarship,
            on_clear=self._on_clear_scholarship,
        )
        self.sch_input.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.sch_result = ResultPanel(top_frame)
        self.sch_result.pack(side="right", fill="both", expand=True, padx=4, pady=4)

        self.sch_rules = RulesTable(parent)
        self.sch_rules.pack(side="top", fill="x", padx=10, pady=4)

        self.sch_plot = PlotFrame(parent, title="Fuzzy Inference: Aggregated Consequent & Centroid")
        self.sch_plot.pack(side="bottom", fill="both", expand=True, padx=10, pady=6)

    def _on_evaluate_scholarship(self) -> None:
        """Handle evaluation callback for Domain B."""
        vals = self.sch_input.get_values()
        try:
            res = self.advisor.evaluate(
                "scholarship",
                cgpa=vals.get("cgpa", ""),
                scholarship_type=vals.get("scholarship_type", ""),
                credit_hours=vals.get("credit_hours", ""),
            )
            self.sch_result.display_result(res)
            self.sch_rules.update_rules(res.fired_rules)
            fig = plot_aggregation(
                "scholarship",
                cgpa=res.inputs["cgpa"],
                scholarship_type=res.inputs["scholarship_type"],
                credit_hours=res.inputs["credit_hours"],
            )
            self.sch_plot.update_figure(fig)
        except InputError as err:
            self.sch_result.display_error(str(err))
            self.sch_rules.clear()
            self.sch_plot.clear()

    def _on_clear_scholarship(self) -> None:
        """Handle clear callback for Domain B."""
        self.sch_input.clear()
        self.sch_result.clear()
        self.sch_rules.clear()
        self.sch_plot.clear()

    def _build_mfs_tab(self, parent: ttk.Frame) -> None:
        """Build Membership Functions & Surface explorer tab."""
        ctrl_bar = ttk.Frame(parent, padding=6)
        ctrl_bar.pack(side="top", fill="x", padx=8, pady=4)

        ttk.Label(ctrl_bar, text="Domain:").pack(side="left", padx=4)
        self.mfs_domain_var = tk.StringVar(value="probation")
        domain_cb = ttk.Combobox(
            ctrl_bar,
            textvariable=self.mfs_domain_var,
            values=["probation", "scholarship"],
            state="readonly",
            width=14,
        )
        domain_cb.pack(side="left", padx=4)

        ttk.Label(ctrl_bar, text="View:").pack(side="left", padx=4)
        self.mfs_view_var = tk.StringVar(value="Membership Functions")
        view_cb = ttk.Combobox(
            ctrl_bar,
            textvariable=self.mfs_view_var,
            values=["Membership Functions", "3D Risk Surface"],
            state="readonly",
            width=22,
        )
        view_cb.pack(side="left", padx=4)

        ttk.Label(ctrl_bar, text="Scholarship Type:").pack(side="left", padx=4)
        types = list(config.SCHOLARSHIP_THRESHOLDS.keys())
        self.mfs_stype_var = tk.StringVar(value=types[0])
        stype_cb = ttk.Combobox(
            ctrl_bar,
            textvariable=self.mfs_stype_var,
            values=types,
            state="readonly",
            width=26,
        )
        stype_cb.pack(side="left", padx=4)

        render_btn = ttk.Button(
            ctrl_bar,
            text="Render Plot",
            command=self._render_mfs_plot,
        )
        render_btn.pack(side="left", padx=10)

        self.mfs_plot_frame = PlotFrame(parent, title="Visual Explorer")
        self.mfs_plot_frame.pack(side="bottom", fill="both", expand=True, padx=8, pady=6)

        # Initial render
        self._render_mfs_plot()

    def _render_mfs_plot(self) -> None:
        """Render the selected visual plot."""
        domain = self.mfs_domain_var.get()
        view = self.mfs_view_var.get()
        stype = self.mfs_stype_var.get()

        if view == "Membership Functions":
            fig = plot_memberships(domain, scholarship_type=stype)
        else:
            fig = plot_surface(domain, scholarship_type=stype)

        self.mfs_plot_frame.update_figure(fig)


def main() -> None:
    """Launch the Tkinter GUI."""
    app = App()
    app.mainloop()
