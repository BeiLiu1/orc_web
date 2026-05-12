import cv2

def load_image(path):

    img = cv2.imread(path)

    if img is None:
        raise Exception("图片读取失败")

    return img