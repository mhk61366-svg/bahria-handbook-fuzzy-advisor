"""Matplotlib figure factories for fuzzy advisor visualization.

Always returns matplotlib.figure.Figure instances; never uses pyplot state.
"""
from typing import Any
import numpy as np
from matplotlib.figure import Figure
import skfuzzy.control as ctrl

from src import config
from src.domains import probation, scholarship
from src.validation import (
    validate_cgpa,
    validate_credit_hours,
    validate_probation_count,
    validate_scholarship_type,
)
from src.variables import (
    cgpa_antecedent,
    credit_load_antecedent,
    probation_count_antecedent,
    risk_consequent,
)


def plot_memberships(domain: str, scholarship_type: str | None = None) -> Figure:
    """Plot membership functions for all input and output variables with handbook thresholds."""
    fig = Figure(figsize=(12, 3.8))

    if domain == "probation":
        threshold = config.PROBATION_MIN_CGPA
        cgpa_var = cgpa_antecedent(threshold)
        pc_var = probation_count_antecedent()
        risk_var = risk_consequent()

        ax1 = fig.add_subplot(131)
        for name, term in cgpa_var.terms.items():
            ax1.plot(cgpa_var.universe, term.mf, label=name)
        ax1.axvline(
            threshold,
            color="red",
            linestyle="--",
            label=f"Min CGPA ({threshold:.2f}, §5.5.1)",
        )
        ax1.set_title("CGPA Antecedent")
        ax1.set_xlabel("CGPA")
        ax1.set_ylabel("Degree")
        ax1.set_ylim(-0.05, 1.05)
        ax1.legend(fontsize=7, loc="upper right")
        ax1.grid(True, linestyle=":", alpha=0.6)

        ax2 = fig.add_subplot(132)
        for name, term in pc_var.terms.items():
            ax2.plot(pc_var.universe, term.mf, label=name)
        ax2.set_title("Probation Count Antecedent")
        ax2.set_xlabel("Probation Count")
        ax2.set_xticks(list(config.PROBATION_COUNTS))
        ax2.set_ylim(-0.05, 1.05)
        ax2.legend(fontsize=7, loc="upper right")
        ax2.grid(True, linestyle=":", alpha=0.6)

        ax3 = fig.add_subplot(133)
        for name, term in risk_var.terms.items():
            ax3.plot(risk_var.universe, term.mf, label=name)
        ax3.set_title("Risk Consequent")
        ax3.set_xlabel("Risk Score")
        ax3.set_ylim(-0.05, 1.05)
        ax3.legend(fontsize=7, loc="upper right")
        ax3.grid(True, linestyle=":", alpha=0.6)

    else:
        stype = scholarship_type or "merit_batch_topper"
        threshold = config.SCHOLARSHIP_THRESHOLDS[stype]
        cgpa_var = cgpa_antecedent(threshold)
        cl_var = credit_load_antecedent()
        risk_var = risk_consequent()

        ax1 = fig.add_subplot(131)
        for name, term in cgpa_var.terms.items():
            ax1.plot(cgpa_var.universe, term.mf, label=name)
        ax1.axvline(
            threshold,
            color="red",
            linestyle="--",
            label=f"Min CGPA ({threshold:.2f})",
        )
        ax1.set_title(f"CGPA ({stype})")
        ax1.set_xlabel("CGPA")
        ax1.set_ylabel("Degree")
        ax1.set_ylim(-0.05, 1.05)
        ax1.legend(fontsize=7, loc="upper right")
        ax1.grid(True, linestyle=":", alpha=0.6)

        ax2 = fig.add_subplot(132)
        for name, term in cl_var.terms.items():
            ax2.plot(cl_var.universe, term.mf, label=name)
        ax2.axvline(
            config.CREDITS_MIN,
            color="red",
            linestyle="--",
            label=f"Min Regular ({config.CREDITS_MIN} cr)",
        )
        ax2.set_title("Credit Load Antecedent")
        ax2.set_xlabel("Credit Hours")
        ax2.set_ylim(-0.05, 1.05)
        ax2.legend(fontsize=7, loc="upper right")
        ax2.grid(True, linestyle=":", alpha=0.6)

        ax3 = fig.add_subplot(133)
        for name, term in risk_var.terms.items():
            ax3.plot(risk_var.universe, term.mf, label=name)
        ax3.set_title("Risk Consequent")
        ax3.set_xlabel("Risk Score")
        ax3.set_ylim(-0.05, 1.05)
        ax3.legend(fontsize=7, loc="upper right")
        ax3.grid(True, linestyle=":", alpha=0.6)

    fig.tight_layout()
    return fig


def plot_aggregation(domain: str, **raw_inputs: Any) -> Figure:
    """Plot clipped consequent sets, aggregated fuzzy output, and centroid defuzzification line."""
    fig = Figure(figsize=(8, 3.8))
    ax = fig.add_subplot(111)

    if domain == "probation":
        cgpa = validate_cgpa(raw_inputs.get("cgpa"))
        probation_count = validate_probation_count(raw_inputs.get("probation_count"))
        system, _ = probation.build_system()
        sim = ctrl.ControlSystemSimulation(system)
        sim.input["cgpa"] = cgpa
        sim.input["probation_count"] = probation_count
        sim.compute()
        title_suffix = f"Probation (CGPA={cgpa}, Count={probation_count})"
    else:
        cgpa = validate_cgpa(raw_inputs.get("cgpa"))
        scholarship_type = validate_scholarship_type(raw_inputs.get("scholarship_type"))
        credit_hours = validate_credit_hours(raw_inputs.get("credit_hours"))
        system, _ = scholarship.build_system(scholarship_type)
        sim = ctrl.ControlSystemSimulation(system)
        sim.input["cgpa"] = cgpa
        sim.input["credit_load"] = credit_hours
        sim.compute()
        title_suffix = f"Scholarship (CGPA={cgpa}, Load={credit_hours})"

    consequents = list(sim.ctrl.consequents)
    risk_var = consequents[0]
    universe = risk_var.universe
    aggregate = np.zeros_like(universe, dtype=float)

    term_colors = {
        "low": "#2ca02c",
        "moderate": "#ff7f0e",
        "high": "#d62728",
        "critical": "#9467bd",
    }

    for name, term in risk_var.terms.items():
        try:
            cuts = list(term.cuts[sim].values())
        except (KeyError, AttributeError):
            cuts = []
        max_cut = max(cuts) if cuts else 0.0
        clipped = np.fmin(max_cut, term.mf)
        aggregate = np.fmax(aggregate, clipped)
        color = term_colors.get(name, "blue")
        ax.plot(universe, term.mf, linestyle=":", color=color, alpha=0.4)
        if max_cut > 0:
            ax.fill_between(
                universe,
                0,
                clipped,
                color=color,
                alpha=0.35,
                label=f"{name} (cut={max_cut:.2f})",
            )

    centroid = float(sim.output["risk"])
    ax.plot(universe, aggregate, "k-", linewidth=2, label="Aggregated set")
    ax.axvline(
        centroid,
        color="black",
        linestyle="--",
        linewidth=1.8,
        label=f"Centroid = {centroid:.1f}",
    )

    ax.set_title(f"Fuzzy Aggregation & Defuzzification: {title_suffix}", fontsize=10)
    ax.set_xlabel("Risk Score (0–100)")
    ax.set_ylabel("Membership Degree")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.6)
    fig.tight_layout()
    return fig


def plot_surface(domain: str, scholarship_type: str | None = None) -> Figure:
    """Plot 3D output surface of risk score across inputs."""
    fig = Figure(figsize=(8, 4.5))
    ax = fig.add_subplot(111, projection="3d")

    if domain == "probation":
        cgpa_vals = np.linspace(config.CGPA_MIN, config.CGPA_MAX, 35)
        count_vals = np.array(config.PROBATION_COUNTS)
        X, Y = np.meshgrid(cgpa_vals, count_vals)
        Z = np.zeros_like(X)

        system, _ = probation.build_system()
        for i in range(len(count_vals)):
            for j in range(len(cgpa_vals)):
                sim = ctrl.ControlSystemSimulation(system)
                sim.input["cgpa"] = float(X[i, j])
                sim.input["probation_count"] = int(Y[i, j])
                sim.compute()
                Z[i, j] = float(sim.output["risk"])

        surf = ax.plot_surface(X, Y, Z, cmap="coolwarm", edgecolor="none", alpha=0.85)
        ax.set_xlabel("CGPA")
        ax.set_ylabel("Probation Count")
        ax.set_zlabel("Risk Score")
        ax.set_yticks(list(config.PROBATION_COUNTS))
        ax.set_title("Domain A: Probation Risk Surface", fontsize=10)
    else:
        stype = scholarship_type or "merit_batch_topper"
        cgpa_vals = np.linspace(config.CGPA_MIN, config.CGPA_MAX, 30)
        load_vals = np.linspace(0.0, float(config.CREDITS_MAX), 25)
        X, Y = np.meshgrid(cgpa_vals, load_vals)
        Z = np.zeros_like(X)

        system, _ = scholarship.build_system(stype)
        for i in range(len(load_vals)):
            for j in range(len(cgpa_vals)):
                sim = ctrl.ControlSystemSimulation(system)
                sim.input["cgpa"] = float(X[i, j])
                sim.input["credit_load"] = float(Y[i, j])
                sim.compute()
                Z[i, j] = float(sim.output["risk"])

        surf = ax.plot_surface(X, Y, Z, cmap="coolwarm", edgecolor="none", alpha=0.85)
        ax.set_xlabel("CGPA")
        ax.set_ylabel("Credit Load (Hours)")
        ax.set_zlabel("Risk Score")
        ax.set_title(f"Domain B: Scholarship Risk Surface ({stype})", fontsize=10)

    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=8)
    fig.tight_layout()
    return fig
