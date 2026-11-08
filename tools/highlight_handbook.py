"""Create the colour-highlighted handbook pages for the submission.

Contents to write:
  read data/traceability.csv; open handbook/Student_Handbook_Spring_2026.pdf with `import pymupdf`
  for each row: page = doc[pdf_page - 1]; rects = page.search_for(highlight_anchor);
      add a highlight annotation coloured colour_hex; print a WARNING when the anchor is not found.
  NOTE: the PDF text layer has OCR artefacts ('f ollowing', 'qualif y'). Copy anchors from
  `pdftotext` output, keep them short and distinctive; fall back to a manual rectangle if search fails.
  write report/handbook_highlighted.pdf containing only the pages used.
"""
