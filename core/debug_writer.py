import os
import cv2


def save_lines_overlay(img, lines, out_dir="debug/blocks"):
    os.makedirs(out_dir, exist_ok=True)
    overlay = img.copy()
    for y in lines:
        cv2.line(overlay, (0, y), (overlay.shape[1], y), (0, 255, 0), 2)
    cv2.imwrite(f"{out_dir}/_lines_overlay.png", overlay)


def save_block_image(roi, index, y1, y2, color, out_dir="debug/blocks"):
    os.makedirs(out_dir, exist_ok=True)
    suffix = color if color else "skipped"
    cv2.imwrite(f"{out_dir}/block_{index:03d}_{suffix}_y{y1}_y{y2}.png", roi)


def save_result_images(classifier, out_dir="temp/final_groups"):
    classifier.save_result_images(out_dir)
