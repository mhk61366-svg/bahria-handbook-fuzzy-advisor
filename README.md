# Bahria Handbook Fuzzy Advisor

A Mamdani fuzzy inference system that answers student questions about **academic probation/drop**
and **scholarship retention**, using rules extracted from the Bahria University Student Handbook
(Spring 2026). Every rule is traceable to a handbook section and page.

<!-- TODO: add a screenshot or short GIF of the Tkinter GUI: docs/screenshots/gui.png -->

## Features
- Official handbook verdict (crisp) plus a graded fuzzy risk score and advice
- Fired rules shown with firing strengths and handbook references
- Membership-function and output-surface plots
- Automated evaluation on a 30+ query test set (normal, boundary, invalid inputs)

## Quick start
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m fuzzy_handbook          # launches the desktop GUI
```

## Run the tests
```bash
pip install -r requirements-dev.txt
pytest
python tools/evaluate.py          # writes report/test_results.csv and prints accuracy
```

## Documentation
Design, rationale, rule base and boundary handling: see [DESIGN.md](DESIGN.md).

## Results
<!-- TODO: fill in after evaluation: total queries, accuracy, known failures -->

## Disclaimer
Educational project. Not an official Bahria University tool. The handbook is the only authority
on academic rules; always confirm with your department.

## License
MIT
