# screencap.py
# Toma una captura completa de pantalla y la devuelve como ndarray BGR

import mss
import numpy as np
import cv2

def get_screenshot(region=None):
    """
    region: None para pantalla completa o dict {'left':x,'top':y,'width':w,'height':h}
    devuelve: imagen BGR (numpy ndarray)
    """
    with mss.mss() as sct:
        if region is None:
            monitor = sct.monitors[1]  # monitor principal
            sct_im = sct.grab(monitor)
        else:
            sct_im = sct.grab(region)
        img = np.array(sct_im)  # BGRA
        # convertir BGRA -> BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img
