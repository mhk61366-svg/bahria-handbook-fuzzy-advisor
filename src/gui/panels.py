import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.models import AdvisorResult, FiredRule


class InputPanel(ttk.LabelFrame):
    """Input form with labelled entry/combobox fields and action buttons."""

    def __init__(
        self,
        master: tk.Widget,
        title: str,
        fields: list[dict[str, Any]],
        on_evaluate: Callable[[], None],
        on_clear: Callable[[], None],
    ) -> None:
        super().__init__(master, text=title, padding=10)
        self.on_evaluate = on_evaluate
        self.on_clear = on_clear
        self._entries: dict[str, tk.StringVar] = {}

        for row_idx, field in enumerate(fields):
            name = field["name"]
            label_text = field["label"]
            var = tk.StringVar(value=str(field.get("default", "")))
            self._entries[name] = var

            lbl = ttk.Label(self, text=label_text)
            lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=4)

            if field.get("type") == "combobox":
                values = field.get("options", [])
                widget: ttk.Widget = ttk.Combobox(
                    self,
                    textvariable=var,
                    values=values,
                    state="readonly",
                    width=28,
                )
            else:
                widget = ttk.Entry(self, textvariable=var, width=30)
                widget.bind("<Return>", lambda _e: self.on_evaluate())

            widget.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=4)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="e",
            padx=5,
            pady=10,
        )

        eval_btn = ttk.Button(
            btn_frame,
            text="Evaluate",
            command=self.on_evaluate,
        )
        eval_btn.pack(side="left", padx=4)

        clear_btn = ttk.Button(
            btn_frame,
            text="Clear",
            command=self.on_clear,
        )
        clear_btn.pack(side="left", padx=4)

    def get_values(self) -> dict[str, str]:
        """Return dict of current string values keyed by field name."""
        return {k: v.get() for k, v in self._entries.items()}

    def set_values(self, **values: Any) -> None:
        """Set specific field values."""
        for k, v in values.items():
            if k in self._entries:
                self._entries[k].set(str(v))

    def clear(self) -> None:
        """Reset fields to empty."""
        for var in self._entries.values():
            var.set("")


class ResultPanel(ttk.LabelFrame):
    """Result card displaying official verdict, risk score, linguistic label, advice, and errors."""

    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master, text="Evaluation Result", padding=10)

        self.error_var = tk.StringVar(value="")
        self.error_label = tk.Label(
            self,
            textvariable=self.error_var,
            fg="#900C3F",
            bg="#FDEDEC",
            font=("Segoe UI", 9, "bold"),
            wraplength=480,
            justify="left",
            padx=6,
            pady=4,
            relief="solid",
            bd=1,
        )

        self.verdict_var = tk.StringVar(value="—")
        self.lbl_verdict_title = ttk.Label(
            self,
            text="Official Verdict:",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_verdict_title.grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.lbl_verdict_val = ttk.Label(
            self,
            textvariable=self.verdict_var,
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_verdict_val.grid(row=1, column=1, sticky="w", padx=4, pady=2)

        self.risk_var = tk.StringVar(value="—")
        self.lbl_risk_title = ttk.Label(
            self,
            text="Fuzzy Risk:",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_risk_title.grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.lbl_risk_val = ttk.Label(
            self,
            textvariable=self.risk_var,
            font=("Segoe UI", 9),
        )
        self.lbl_risk_val.grid(row=2, column=1, sticky="w", padx=4, pady=2)

        self.advice_var = tk.StringVar(value="Enter inputs and click Evaluate.")
        self.lbl_advice_title = ttk.Label(
            self,
            text="Advisor Guidance:",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_advice_title.grid(row=3, column=0, sticky="nw", padx=4, pady=4)
        self.lbl_advice_val = ttk.Label(
            self,
            textvariable=self.advice_var,
            wraplength=480,
            justify="left",
        )
        self.lbl_advice_val.grid(row=3, column=1, sticky="w", padx=4, pady=4)

    def display_result(self, result: AdvisorResult) -> None:
        """Display an AdvisorResult in the result card."""
        self.error_label.grid_forget()
        self.error_var.set("")

        clauses_str = ", ".join(result.verdict.clauses)
        self.verdict_var.set(f"{result.verdict.label} ({clauses_str})")
        self.risk_var.set(
            f"{result.risk_score:.1f} / 100  —  Band: {result.risk_label.upper()}"
        )
        self.advice_var.set(result.advice)

    def display_error(self, message: str) -> None:
        """Display an error banner for invalid input."""
        self.verdict_var.set("—")
        self.risk_var.set("—")
        self.advice_var.set("Please correct the invalid input highlighted above.")
        self.error_var.set(f"Input Error: {message}")
        self.error_label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=4)

    def clear(self) -> None:
        """Reset result card to initial state."""
        self.error_label.grid_forget()
        self.error_var.set("")
        self.verdict_var.set("—")
        self.risk_var.set("—")
        self.advice_var.set("Enter inputs and click Evaluate.")


class RulesTable(ttk.LabelFrame):
    """Table showing fuzzy rules fired with positive firing strength."""

    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master, text="Rules Fired (Strength > 0)", padding=6)

        columns = ("rule_id", "text", "strength", "source")
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            height=5,
        )

        self.tree.heading("rule_id", text="Rule ID")
        self.tree.heading("text", text="IF-THEN Rule")
        self.tree.heading("strength", text="Strength")
        self.tree.heading("source", text="Handbook Ref")

        self.tree.column("rule_id", width=65, anchor="center")
        self.tree.column("text", width=330, anchor="w")
        self.tree.column("strength", width=75, anchor="center")
        self.tree.column("source", width=160, anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def update_rules(self, fired_rules: list[FiredRule]) -> None:
        """Populate the table with fired rules."""
        self.clear()
        for rule in fired_rules:
            self.tree.insert(
                "",
                "end",
                values=(
                    rule.rule_id,
                    rule.text,
                    f"{rule.strength:.3f}",
                    rule.source,
                ),
            )

    def clear(self) -> None:
        """Clear all rows from the table."""
        for item in self.tree.get_children():
            self.tree.delete(item)


class PlotFrame(ttk.LabelFrame):
    """Embedded Matplotlib canvas inside a Tkinter Frame."""

    def __init__(self, master: tk.Widget, title: str = "Visualization") -> None:
        super().__init__(master, text=title, padding=4)
        self.canvas: FigureCanvasTkAgg | None = None

    def update_figure(self, figure: Figure) -> None:
        """Render the given Figure inside this frame."""
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(figure, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def clear(self) -> None:
        """Clear the current plot."""
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
