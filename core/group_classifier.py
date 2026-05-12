import cv2
import numpy as np
import os


def stack_images(img_list):

    if not img_list:
        return None

    w = img_list[0].shape[1]

    resized = [
        cv2.resize(img, (w, img.shape[0]))
        for img in img_list
    ]

    return np.vstack(resized)


def get_edge_color(img, y, detect_func, thickness=3):

    h, w = img.shape[:2]

    y1 = max(0, y - thickness)
    y2 = min(h, y + thickness)

    strip = img[y1:y2, 0:w]

    hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)

    return detect_func(hsv)


class GroupClassifier:

    def __init__(self, detect_color_func):

        self.detect_color = detect_color_func
        self.group_color = None

        # =========================
        # 汇总结果（统一float但强制2位）
        # =========================
        self.result = {
            "red": {"amount_total": 0.0, "tax_total": 0.0},
            "yellow": {"amount_total": 0.0, "tax_total": 0.0},
            "blue": {"amount_total": 0.0, "tax_total": 0.0},
        }

        self.group_images = {
            "red": [],
            "yellow": [],
            "blue": []
        }

        self.debug_log = []

    def process_block(self, img, block, ocr_func, parser_func):

        roi = block["img"]
        y1 = block["y_start"]
        y2 = block["y_end"]

        top_color = get_edge_color(img, y1, self.detect_color)
        bottom_color = get_edge_color(img, y2, self.detect_color)

        # =========================
        # OCR + 解析 (先OCR，保证skipped也能在debug_log看到识别结果)
        # =========================
        text = ocr_func(roi)
        data = parser_func(text)

        # 存下最后一次识别结果，方便外部debug
        self.last_text = text
        self.last_data = data

        if not top_color or not bottom_color:
            return None

        # =========================
        # 状态机
        # =========================
        if self.group_color is None:
            self.group_color = top_color
        else:
            if top_color == self.group_color:
                self.group_color = bottom_color
            else:
                self.group_color = top_color

        amount = round(float(data.get("amount", 0)), 2)
        tax = round(float(data.get("tax", 0)), 2)

        color = self.group_color

        if color in self.result:

            before_amount = self.result[color]["amount_total"]
            before_tax = self.result[color]["tax_total"]

            # =========================
            # ⭐ 核心修复：每一步都 round
            # =========================
            new_amount = round(before_amount + amount, 2)
            new_tax = round(before_tax + tax, 2)

            self.result[color]["amount_total"] = new_amount
            self.result[color]["tax_total"] = new_tax

            # =========================
            # debug trace
            # =========================
            self.debug_log.append({
                "color": color,
                "add_amount": amount,
                "add_tax": tax,
                "before_amount": before_amount,
                "after_amount": new_amount,
                "before_tax": before_tax,
                "after_tax": new_tax,
                "raw_text": text.replace("\n", " | ")
            })

            self.group_images[color].append(roi)

        return color

    def get_result(self):
        return self.result

    def save_result_images(self, out_dir="temp/final_groups"):

        os.makedirs(out_dir, exist_ok=True)

        for color, imgs in self.group_images.items():

            stacked = stack_images(imgs)

            if stacked is None:
                continue

            cv2.imwrite(f"{out_dir}/{color}.png", stacked)