# detector.py
import cv2
import numpy as np
import os

# --- Templates ---
RESOURCE_TEMPLATES = {}
# Asumiendo que TEMPLATE_DIR está en la carpeta raíz, un nivel arriba de 'src'
# Si detector.py está en 'src', necesitamos subir un nivel
base_dir = os.path.dirname(os.path.dirname(__file__)) # Carpeta raíz (bot-recolector)
TEMPLATE_DIR = os.path.join(base_dir, "templates")

# Cargar todos los templates
if os.path.isdir(TEMPLATE_DIR):
    for f in os.listdir(TEMPLATE_DIR):
        if f.lower().endswith((".png", ".jpg", ".jpeg")):
            name = os.path.splitext(f)[0] # nombre sin extensión
            try:
                # Leer directamente en escala de grises es más eficiente
                img_gray = cv2.imread(os.path.join(TEMPLATE_DIR, f), cv2.IMREAD_GRAYSCALE)
                if img_gray is not None:
                    # Guardamos la versión en escala de grises directamente
                    RESOURCE_TEMPLATES.setdefault(name, []).append(img_gray)
                else:
                    print(f"Advertencia: No se pudo cargar template {f}")
            except Exception as e:
                print(f"Error cargando template {f}: {e}")
else:
    print(f"Advertencia: Directorio de templates '{TEMPLATE_DIR}' no encontrado.")


# --- Función de compatibilidad ---
def load_model(path):
    """
    Función dummy para compatibilidad. No se carga modelo YOLO.
    """
    print("[INFO] Usando template matching (escala de grises), no se carga modelo YOLO.")
    return None

# --- Detect ---
def detect(model, img, conf=0.88, classes=None):
    """
    Detecta objetos en la imagen usando template matching robusto en escala de grises.

    Args:
        model: ignorado (compatibilidad)
        img: imagen a analizar (se convertirá a escala de grises)
        conf: umbral de confianza
        classes: lista de nombres de recursos/templates a detectar

    Returns:
        List[dict]: cada dict tiene 'label', 'conf', 'cx', 'cy', 'bbox'
    """
    detections = []
    if img is None: # Chequeo extra
         print("Error en detect: Imagen de entrada es None.")
         return detections

    if classes is None:
        classes = RESOURCE_TEMPLATES.keys()

    # --- Convertir imagen de entrada a escala de grises ---
    try:
        # Si ya es gris, no hacer nada. Si tiene 4 canales (BGRA), convertir a BGR primero.
        if len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # Convertir a escala de grises si tiene 3 canales (BGR)
        if len(img.shape) == 3:
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img # Asumir que ya es gris si no tiene 3 canales
    except cv2.error as e:
         print(f"Error convirtiendo imagen a escala de grises: {e}")
         return detections
    # -----------------------------------------------------

    for cls_name in classes:
        templates_gray = RESOURCE_TEMPLATES.get(cls_name) # Ya están en escala de grises
        if not templates_gray:
            continue

        for tpl_gray in templates_gray: # Iterar sobre los templates en gris
            if tpl_gray is None:
                continue

            # --- Ya no se necesita convertir el template aquí ---
            # tpl = template
            # if len(tpl.shape) > 2 and tpl.shape[2] == 4: ...
            # tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
            # --------------------------------------------------

            try:
                # --- Usar las imágenes en escala de grises ---
                res = cv2.matchTemplate(img_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
                # ------------------------------------------

                loc = np.where(res >= conf)
                # Obtener dimensiones del template en escala de grises
                h, w = tpl_gray.shape[:2] # h, w para gris

                # Usar lista para filtrar duplicados cercanos (más eficiente que set para pocos puntos)
                seen_centers = []
                threshold_distance_sq = 20**2 # Distancia al cuadrado (evita raíz cuadrada)

                for pt in zip(*loc[::-1]): # pt es (x, y) de esquina superior izquierda
                    cx = pt[0] + w // 2
                    cy = pt[1] + h // 2

                    # Evitar duplicados cercanos usando distancia euclidiana al cuadrado
                    is_duplicate = False
                    for dx, dy in seen_centers:
                        dist_sq = (cx - dx)**2 + (cy - dy)**2
                        if dist_sq < threshold_distance_sq:
                            is_duplicate = True
                            break
                    if is_duplicate:
                        continue

                    seen_centers.append((cx, cy)) # Añadir centro a la lista de vistos

                    detections.append({
                        "label": cls_name,
                        "conf": float(res[pt[1], pt[0]]), # Confianza en la esquina detectada
                        "cx": cx,
                        "cy": cy,
                        "bbox": [pt[0], pt[1], pt[0]+w, pt[1]+h] # Bbox basado en w, h del template gris
                    })
            except cv2.error as e:
                print(f"Error en matchTemplate para {cls_name}: {e}. ¿Template/Imagen inválidos?")
                continue # Saltar al siguiente template si hay error
            except Exception as e:
                print(f"Error inesperado procesando template {cls_name}: {e}")
                continue


    return detections