import os
import glob

from core.image_loader import load_image
from core.row_detector import get_row_lines, crop_between_lines
from core.color_classifier import detect_row_color
from core.ocr_engine import ocr_image
from core.parser import parse_block_amounts
from core.group_classifier import GroupClassifier
from core.excel_writer import save_excel
from core.debug_writer import save_lines_overlay, save_block_image, save_result_images


def fmt(x):
    return float(f"{x:.2f}")


def process_image(img_path, debug=False):

    img = load_image(img_path)

    lines = get_row_lines(img)
    blocks = crop_between_lines(img, lines)

    print(f"\n{'='*60}")
    print(f"{img_path}: {len(lines)} lines | {len(blocks)} blocks")

    if debug:
        save_lines_overlay(img, lines)

    classifier = GroupClassifier(detect_row_color)

    for i, block in enumerate(blocks):

        roi = block["img"]
        y1 = block["y_start"]
        y2 = block["y_end"]

        color = classifier.process_block(
            img, block,
            ocr_func=ocr_image,
            parser_func=parse_block_amounts
        )

        if debug:
            save_block_image(roi, i, y1, y2, color)

        ocr_text = classifier.last_text.replace("\n", " | ")
        print(f"  BLOCK {i} [{y1}->{y2}] -> {color} | OCR: {ocr_text}")

    result = classifier.get_result()

    red_amount = fmt(result["red"]["amount_total"])
    red_tax = fmt(result["red"]["tax_total"])
    yellow_amount = fmt(result["yellow"]["amount_total"])
    yellow_tax = fmt(result["yellow"]["tax_total"])
    blue_amount = fmt(result["blue"]["amount_total"])
    blue_tax = fmt(result["blue"]["tax_total"])

    total_amount = fmt(red_amount + yellow_amount + blue_amount)
    total_tax = fmt(red_tax + yellow_tax + blue_tax)

    rows = [
        {"颜色": "red", "含税金额": red_amount, "税费": red_tax},
        {"颜色": "yellow", "含税金额": yellow_amount, "税费": yellow_tax},
        {"颜色": "blue", "含税金额": blue_amount, "税费": blue_tax},
        {"颜色": "TOTAL", "含税金额": total_amount, "税费": total_tax},
    ]

    base = os.path.splitext(os.path.basename(img_path))[0]
    out_path = f"output/{base}.xlsx"
    save_excel({"result": {"rows": rows}}, out_path)

    if debug:
        save_result_images(classifier)

    print(f"  Result: red {red_amount}/{red_tax} | yellow {yellow_amount}/{yellow_tax} | blue {blue_amount}/{blue_tax} | TOTAL {total_amount}/{total_tax}")

    return rows


def process_all(debug=False):

    images = glob.glob("data/*.png") + glob.glob("data/*.jpg") + glob.glob("data/*.jpeg")

    if not images:
        print("No images found in data/")
        return

    for path in sorted(images):
        process_image(path, debug=debug)
