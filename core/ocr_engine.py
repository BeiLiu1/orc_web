import pytesseract
import cv2
import numpy as np
import re
import os

_default_path = r"D:\Tesseract-OCR\tesseract.exe"
if os.path.exists(_default_path):
    pytesseract.pytesseract.tesseract_cmd = _default_path



def _ocr(gray, config):
    return pytesseract.image_to_string(gray, lang="eng", config=config)


def _score(text):
    nums = re.findall(r"\d+\.\d{1,2}", text)
    return sum(1 for x in nums if float(x) > 0)


def ocr_image(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

    h, w = gray.shape
    half_w = w // 2
    third2_w = w * 2 // 3

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray)

    # Sharpening
    sharpen_kernel = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]])
    gray_sharp = cv2.filter2D(gray, -1, sharpen_kernel)

    cfg_wl = r'--psm 6 -c tessedit_char_whitelist=0123456789.VATrated'
    cfg_psm7 = r'--psm 7'
    cfg_psm7_wl = r'--psm 7 -c tessedit_char_whitelist=0123456789.VATrated'

    best = ""
    best_score = -1

    variants = [
        ("A", cv2.threshold(cv2.GaussianBlur(gray, (3, 3), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], cfg_wl),
        ("B", gray, cfg_wl),
        ("C", gray_sharp, cfg_wl),
        ("D", gray_clahe, cfg_wl),
        ("E", gray, cfg_psm7),
        ("F", gray[:, third2_w:], cfg_psm7_wl),
        ("G", gray_sharp[:, third2_w:], cfg_psm7_wl),
        ("H", gray_clahe[:, third2_w:], cfg_psm7_wl),
        ("I", gray_sharp, cfg_psm7_wl),
        ("J", gray_sharp[:, half_w:], cfg_psm7),
    ]

    for tag, img_input, config in variants:
        text = _ocr(img_input, config)
        s = _score(text)
        if s > best_score:
            best_score = s
            best = text

    return best
