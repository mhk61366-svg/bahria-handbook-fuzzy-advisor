"""Fired-rule extraction: the 'rules fired with firing strengths' requirement.

Contents to write:
  fired_rules(sim, rules, meta) -> list[FiredRule]
      read rule.aggregate_firing[sim] IMMEDIATELY after sim.compute(); keep strength > 0; sort descending.
      This attribute is not documented public API: this is the ONLY place allowed to touch it.
  independent_strengths(inputs, rules) -> dict[rule_id, float]
      recompute min/max firing with skfuzzy.interp_membership; used by tests as a cross-check
      and as a fallback if aggregate_firing ever breaks.
  load_rule_meta(csv_path) -> dict[rule_id, {text, source}]   # reads data/traceability.csv
"""
