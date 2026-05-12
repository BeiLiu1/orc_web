import cv2
import numpy as np

def detect_row_color(hsv):

    color_map = {
        "red": [
            (np.array([0,80,80]), np.array([15,255,255])),
            (np.array([160,80,80]), np.array([179,255,255]))
        ],
        "yellow": [
            (np.array([15,80,80]), np.array([40,255,255]))
        ],
        "blue": [
            (np.array([90,80,80]), np.array([140,255,255]))
        ]
    }

    best = None
    best_val = 0

    for color, ranges in color_map.items():

        total = 0

        for l, u in ranges:

            mask = cv2.inRange(hsv, l, u)

            total += cv2.countNonZero(mask)

        if total > best_val:
            best_val = total
            best = color

    if best_val < 200:
        return None

    return best