from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from app.services.parser import parse_amount_tax_pairs


TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


@dataclass
class DetectedBox:
    x: int
    y: int
    w: int
    h: int
    color_hex: str
    color_lab: tuple[float, float, float]


def recognize_image(path: Path, image_file_id: str) -> dict:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError("图片读取失败")

    height, width = img.shape[:2]
    boxes = detect_colored_boxes(img)
    groups = cluster_boxes(boxes)

    result_groups = []
    for group_index, group in enumerate(groups, start=1):
        items = []
        for box in group["boxes"]:
            crop = crop_box_content(img, box)
            text = ocr_crop(crop)
            parsed_items = parse_amount_tax_pairs(text)
            for parsed in parsed_items:
                items.append(
                    {
                        "image_file_id": image_file_id,
                        "raw_text": parsed["raw_text"] or text,
                        "amount": parsed["amount"],
                        "tax": parsed["tax"],
                        "bbox_x": box.x,
                        "bbox_y": box.y,
                        "bbox_w": box.w,
                        "bbox_h": box.h,
                        "ocr_confidence": None,
                        "is_manual": False,
                        "is_corrected": False,
                    }
                )

        result_groups.append(
            {
                "group_index": group_index,
                "display_name": f"颜色组 {group_index}",
                "color_hex": group["color_hex"],
                "items": items,
            }
        )

    if not result_groups:
        result_groups.append(
            {
                "group_index": 1,
                "display_name": "未识别颜色组",
                "color_hex": "#888888",
                "items": [
                    {
                        "image_file_id": image_file_id,
                        "raw_text": "",
                        "amount": 0,
                        "tax": 0,
                        "bbox_x": None,
                        "bbox_y": None,
                        "bbox_w": None,
                        "bbox_h": None,
                        "ocr_confidence": None,
                        "is_manual": False,
                        "is_corrected": False,
                    }
                ],
            }
        )

    return {"width": width, "height": height, "groups": result_groups}


def detect_colored_boxes(img: np.ndarray) -> list[DetectedBox]:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    color_mask = cv2.inRange(saturation, 70, 255)
    bright_mask = cv2.inRange(value, 60, 255)
    mask = cv2.bitwise_and(color_mask, bright_mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_h, image_w = img.shape[:2]
    min_area = max(900, int(image_w * image_h * 0.0006))
    boxes: list[DetectedBox] = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < min_area or w < image_w * 0.12 or h < 12:
            continue
        if w > image_w * 0.99 and h > image_h * 0.95:
            continue

        box_mask = mask[y : y + h, x : x + w]
        density = cv2.countNonZero(box_mask) / float(w * h)
        if density < 0.015:
            continue

        border_pixels = sample_border_pixels(img, x, y, w, h)
        if len(border_pixels) == 0:
            continue
        color_bgr = dominant_bgr(border_pixels)
        color_hex = bgr_to_hex(color_bgr)
        color_lab = bgr_to_lab_tuple(color_bgr)
        boxes.append(DetectedBox(x=x, y=y, w=w, h=h, color_hex=color_hex, color_lab=color_lab))

    return dedupe_boxes(sorted(boxes, key=lambda b: (b.y, b.x)))


def sample_border_pixels(img: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    thickness = max(2, min(8, min(w, h) // 8))
    roi = img[y : y + h, x : x + w]
    top = roi[:thickness, :, :]
    bottom = roi[-thickness:, :, :]
    left = roi[:, :thickness, :]
    right = roi[:, -thickness:, :]
    pixels = np.vstack(
        [
            top.reshape(-1, 3),
            bottom.reshape(-1, 3),
            left.reshape(-1, 3),
            right.reshape(-1, 3),
        ]
    )
    hsv = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    colored = pixels[(hsv[:, 1] > 70) & (hsv[:, 2] > 60)]
    return colored


def dominant_bgr(pixels: np.ndarray) -> tuple[int, int, int]:
    if len(pixels) == 0:
        return (136, 136, 136)
    median = np.median(pixels, axis=0)
    return tuple(int(v) for v in median)


def bgr_to_hex(bgr: tuple[int, int, int]) -> str:
    b, g, r = bgr
    return f"#{r:02x}{g:02x}{b:02x}"


def bgr_to_lab_tuple(bgr: tuple[int, int, int]) -> tuple[float, float, float]:
    sample = np.uint8([[list(bgr)]])
    lab = cv2.cvtColor(sample, cv2.COLOR_BGR2LAB)[0, 0]
    return (float(lab[0]), float(lab[1]), float(lab[2]))


def dedupe_boxes(boxes: list[DetectedBox]) -> list[DetectedBox]:
    kept: list[DetectedBox] = []
    for box in boxes:
        duplicate = False
        for existing in kept:
            if intersection_over_union(box, existing) > 0.8:
                duplicate = True
                break
        if not duplicate:
            kept.append(box)
    return kept


def intersection_over_union(a: DetectedBox, b: DetectedBox) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.w, b.x + b.w)
    y2 = min(a.y + a.h, b.y + b.h)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union else 0


def cluster_boxes(boxes: list[DetectedBox]) -> list[dict]:
    clusters: list[dict] = []
    threshold = 28.0

    for box in boxes:
        best_cluster = None
        best_distance = math.inf
        for cluster in clusters:
            distance = lab_distance(box.color_lab, cluster["lab"])
            if distance < best_distance:
                best_distance = distance
                best_cluster = cluster

        if best_cluster is not None and best_distance <= threshold:
            best_cluster["boxes"].append(box)
            best_cluster["lab"] = mean_lab([b.color_lab for b in best_cluster["boxes"]])
            best_cluster["color_hex"] = box.color_hex
        else:
            clusters.append({"lab": box.color_lab, "color_hex": box.color_hex, "boxes": [box]})

    return sorted(clusters, key=lambda c: min(b.y for b in c["boxes"]))


def lab_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def mean_lab(values: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    return tuple(sum(v[i] for v in values) / len(values) for i in range(3))


def crop_box_content(img: np.ndarray, box: DetectedBox) -> np.ndarray:
    pad = 4
    x1 = min(img.shape[1], max(0, box.x + pad))
    y1 = min(img.shape[0], max(0, box.y + pad))
    x2 = min(img.shape[1], max(x1 + 1, box.x + box.w - pad))
    y2 = min(img.shape[0], max(y1 + 1, box.y + box.h - pad))
    return img[y1:y2, x1:x2]


def ocr_crop(img: np.ndarray) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    config = "--psm 6"
    return pytesseract.image_to_string(gray, lang="eng", config=config)
