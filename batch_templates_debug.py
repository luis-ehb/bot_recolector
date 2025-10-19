# src/batch_templates_debug.py
import os
import cv2
import numpy as np

# --- Carpeta de templates ---
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

# --- Carpeta de capturas a procesar ---
CAPTURAS_DIR = os.path.join(os.path.dirname(__file__), "capturas-debug")

# --- Carpeta de salida de debugs ---
DEBUGS_DIR = os.path.join(os.path.dirname(__file__), "debugs")
os.makedirs(DEBUGS_DIR, exist_ok=True)

# --- Cargar todos los templates de recursos automáticamente ---
RESOURCE_TEMPLATES = {}
for fname in os.listdir(TEMPLATE_DIR):
    name, ext = os.path.splitext(fname)
    if ext.lower() not in [".png", ".jpg", ".jpeg"]:
        continue
    template = cv2.imread(os.path.join(TEMPLATE_DIR, fname), cv2.IMREAD_UNCHANGED)
    if template is None:
        continue
    if template.shape[2] == 4:
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
    RESOURCE_TEMPLATES.setdefault(name, []).append(template)

print(f"Templates cargados: {list(RESOURCE_TEMPLATES.keys())}")

# --- Función de template matching ---
def detect_template(img, template, label, conf_thresh=0.8):
    h, w = template.shape[:2]
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= conf_thresh)
    detections = []
    seen = set()
    for pt in zip(*loc[::-1]):  # x,y
        if any(abs(pt[0]-sx)<5 and abs(pt[1]-sy)<5 for sx,sy in seen):
            continue
        seen.add(pt)
        cx = pt[0] + w//2
        cy = pt[1] + h//2
        detections.append({
            "label": label, 
            "cx": cx, 
            "cy": cy, 
            "bbox":[pt[0], pt[1], pt[0]+w, pt[1]+h]
        })
        # dibujar rectángulo
        cv2.rectangle(img, (pt[0], pt[1]), (pt[0]+w, pt[1]+h), (0,255,0), 2)
        cv2.putText(img, label, (pt[0], pt[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    return detections

# --- Procesar todas las imágenes ---
def main():
    if not os.path.exists(CAPTURAS_DIR):
        print(f"[ERROR] No existe la carpeta de capturas: {CAPTURAS_DIR}")
        return

    img_files = [f for f in os.listdir(CAPTURAS_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    if not img_files:
        print(f"[INFO] No hay imágenes en {CAPTURAS_DIR} para procesar.")
        return

    for img_name in img_files:
        img_path = os.path.join(CAPTURAS_DIR, img_name)
        img = cv2.imread(img_path)
        if img is None:
            print(f"[ERROR] No se pudo cargar la imagen {img_path}")
            continue

        detections = []
        for res_name, templates in RESOURCE_TEMPLATES.items():
            for t in templates:
                detections += detect_template(img, t, res_name)

        print(f"[{img_name}] Detectados: {[d['label'] for d in detections]}")

        debug_output_path = os.path.join(DEBUGS_DIR, f"debug_{img_name}")
        cv2.imwrite(debug_output_path, img)
        print(f"[INFO] Imagen de debug guardada en {debug_output_path}")

if __name__ == "__main__":
    main()
