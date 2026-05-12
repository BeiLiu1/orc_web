import cv2
import numpy as np

def get_row_lines(img):
    """
    只检测横线（保留y坐标）
    """

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        10
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (60, 1))
    detected = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(
        detected,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    lines = []

    h_img, w_img = img.shape[:2]

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)

        if w < 500:
            continue

        # 只记录“横线的y中心点”
        lines.append(y)

    lines = sorted(lines)

    # 去重（防止断裂线重复检测）
    filtered = []
    for y in lines:
        if not filtered or abs(y - filtered[-1]) > 10:
            filtered.append(y)

    return filtered


def crop_between_lines(img, lines):
    """
    用横线y坐标切“区间块”
    """

    h, w = img.shape[:2]

    blocks = []

    # 加边界
    all_lines = [0] + lines + [h]

    for i in range(len(all_lines) - 1):

        y1 = all_lines[i]
        y2 = all_lines[i + 1]

        if y2 - y1 < 20:  # 太小跳过
            continue

        roi = img[y1:y2, 0:w]

        blocks.append({
            "img": roi,
            "index": i,
            "y_start": y1,
            "y_end": y2
        })

    return blocks