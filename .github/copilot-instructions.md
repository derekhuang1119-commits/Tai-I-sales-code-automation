# Repository instructions

This repository contains an offline Windows application for converting
reinforcement-bar order sheets from PDF or images into an Excel template.

## Privacy

- Never upload document content to external APIs.
- Never add cloud OCR or telemetry.
- Never commit real customer PDFs, images, spreadsheets, names, or project data.
- Use synthetic fixtures for tests.

## Architecture

- Keep business logic independent from PySide6.
- Use typed data models.
- Keep PDF, OCR, parsing, shape analysis, rules, Excel writing, GUI, and batch
  processing in separate modules.
- Use dependency injection for OCR implementations.
- Do not hide uncertain OCR values. Return confidence and warnings.

## Business rules

- Remove `#` from bar number.
- PDF length maps to Excel total length.
- Straight-bar dimension maps to the middle/top field.
- Crossed-out rows are skipped.
- Bird-mouth is populated only for applicable stirrup shapes.
- Steel grade remains blank unless explicitly configured.
- Page number is the value after the dash in the bottom-right page marker,
  such as `3-1` becoming `1`.
- Region must be populated.
- Quantity and total weight are required.
- Handwritten corrections take priority only when confidence is sufficient;
  otherwise require user review.

## Development

- Use Python 3.11+.
- Add type hints and docstrings to public interfaces.
- Add tests for all parsing and Excel-mapping rules.
- Run tests before completing a task.
- Update README when behavior or setup changes.
