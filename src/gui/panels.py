"""Reusable ttk frames (no business logic; call FuzzyAdvisor via callbacks).

Contents to write:
  class InputPanel(ttk.Frame)    # labelled entries/comboboxes + Evaluate and Clear buttons
  class ResultPanel(ttk.Frame)   # official verdict, risk score, linguistic label, advice text, error banner
  class RulesTable(ttk.Frame)    # ttk.Treeview: rule ID | IF-THEN | strength | handbook ref (strength > 0 only)
  class PlotFrame(ttk.Frame)     # embeds a matplotlib Figure via FigureCanvasTkAgg
"""
