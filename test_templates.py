# src/test_templates_debug.py
import os
import cv2
import numpy as np
from screencap import get_screenshot

# Rutas a templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
template_hierro = cv2.imread(os.path.join(TEMPLATE_DIR, "hierro.png"), cv2.IMREAD_UNCHANGED)
template_boton = cv2.imread(os.path.join(TEMPLATE_DIR, "boton_retos.png"), cv2.IMREAD_UNCHANGED)

print("Hierro cargado:", template_hierro is not None)
print("Boton cargado:", template_boton is not None)

# Tomar screenshot
img = get_screenshot()

# Función simple de detección con template matching
def detect_template(img, template, label, conf_thresh=0.8):
    detections = []
    if template is None:
        return detections
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= conf_thresh)
    w, h = template.shape[1], template.shape[0]
    seen = set()
    for pt in zip(*loc[::-1]):
        if any(abs(pt[0]-sx)<5 and abs(pt[1]-sy)<5 for sx,sy in seen):
            continue
        seen.add(pt)
        cx = pt[0] + w//2
        cy = pt[1] + h//2
        detections.append({"label": label, "cx": cx, "cy": cy, "bbox":[pt[0], pt[1], pt[0]+w, pt[1]+h]})
        cv2.rectangle(img, (pt[0], pt[1]), (pt[0]+w, pt[1]+h), (0,255,0), 2)
        cv2.putText(img, label, (pt[0], pt[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    return detections

# Detectar ambos templates
detect_template(img, template_hierro, "hierro")
detect_template(img, template_boton, "boton_retos")

# Guardar imagen de debug
debug_path = os.path.join(os.path.dirname(__file__), "..", "debug_templates.png")
cv2.imwrite(debug_path, img)
print(f"[INFO] Imagen de detecciones guardada como {debug_path}")
