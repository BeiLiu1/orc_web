# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How to run

```
venv/Scripts/python.exe main.py
```

Set `DEBUG = True` in main.py to generate debug images (`debug/blocks/`, `temp/final_groups/`). Requires Tesseract OCR at `D:\Tesseract-OCR\tesseract.exe`. Input: `data/test.png`. Output: `result.xlsx`.

## Architecture

Invoice OCR system that extracts amounts from scanned invoices and groups them by color-coded table rows (red/yellow/blue). The pipeline:

1. **`core/row_detector.py`** — Detects horizontal table border lines via adaptive thresholding + morphological opening (60px wide kernel). Crops the image into row blocks between detected lines (min height 20px).

2. **`core/group_classifier.py`** — Color-aware state machine. For each block, samples a thin 6px strip at the top and bottom edge in HSV space, then calls `color_classifier.py` to determine the edge color. The state machine alternates: when the top edge matches the current group color, the block belongs to the bottom edge's color instead. This handles the invoice's alternating row-color pattern. Accumulates amount/tax per color.

3. **`core/color_classifier.py`** — HSV color detection for red (two hue ranges 0-15 + 160-179), yellow (15-40), blue (90-140). Returns the color with most matching pixels, or None if <200 pixels match.

4. **`core/ocr_engine.py`** — Multi-variant Tesseract OCR. Tries 10 preprocessing combinations (OTSU, grayscale-direct, sharpening, CLAHE; full-block and right-crop; PSM 6 and 7; with/without whitelist). Automatically picks the variant with most non-zero `\d+\.\d{1,2}` decimal matches. The sharpening kernel `[[-1,-1,-1],[-1,9,-1],[-1,-1,-1]]` is critical for faint text. Tesseract config whitelist: `0123456789.VATrated`.

5. **`core/parser.py`** — Extracts (amount, tax) pairs from OCR text. Recognizes "Standard-rated VAT" lines and pairs them with preceding amount lines. Has bare-integer fallback for when OCR drops decimal points (e.g. `504` → 5.04, `030` → 0.30).

6. **`core/debug_writer.py`** — Optional debug image output. `save_lines_overlay`, `save_block_image`, `save_result_images`. Only called when `DEBUG = True` in main.py.

## Key constraints

- In `core/ocr_engine.py`: Tesseract path is hardcoded; OCR uses multi-variant selection (10 preprocessing combos, picks the one with most non-zero decimal matches)

- `parse_block_amounts` requires `"VAT"` substring to identify tax lines; bare integer fallback divides by 100 to recover decimal placement
