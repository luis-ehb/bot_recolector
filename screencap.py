# screencap.py
# Modificado para leer el ROI desde config.yaml

import mss
import numpy as np
import cv2
import yaml # <--- Añadido
import os   # <--- Añadido

# --- Ruta al config.yaml (asumiendo que está en la misma carpeta) ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

# --- Variable global para guardar el ROI y no leer el archivo cada vez ---
_cached_roi = None
_config_mtime = 0 # Para detectar cambios en el config

def load_roi_from_config():
    """
    Carga el ROI desde config.yaml y lo convierte al formato de mss.
    Cachea el resultado para no leer el archivo en cada captura.
    """
    global _cached_roi, _config_mtime
    
    try:
        # Comprobar si el archivo ha sido modificado
        current_mtime = os.path.getmtime(CONFIG_PATH)
        if current_mtime == _config_mtime and _cached_roi is not None:
            return _cached_roi # Devolver el ROI cacheado

        # Si no hay cache o el archivo cambió, leerlo
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if isinstance(config, dict):
                    roi_config = config.get("ROI")
                    # Validar que ROI es un diccionario y tiene las claves
                    if isinstance(roi_config, dict) and all(k in roi_config for k in ('x', 'y', 'w', 'h')):
                        # Convertir a formato mss {'left', 'top', 'width', 'height'}
                        roi_mss = {
                            'left': int(roi_config['x']),
                            'top': int(roi_config['y']),
                            'width': int(roi_config['w']),
                            'height': int(roi_config['h'])
                        }
                        # Validar dimensiones
                        if roi_mss['width'] > 0 and roi_mss['height'] > 0:
                            _cached_roi = roi_mss # Guardar en cache
                            _config_mtime = current_mtime # Actualizar tiempo de modificación
                            # print(f"[DEBUG screencap] ROI cargado desde config: {roi_mss}") # Log de debug opcional
                            return roi_mss
                        else:
                            print(f"Advertencia: ROI en {CONFIG_PATH} tiene dimensiones inválidas (w={roi_mss['width']}, h={roi_mss['height']}). Usando pantalla completa.")
                    else:
                         print(f"Advertencia: ROI no está definido correctamente en {CONFIG_PATH}. Usando pantalla completa.")
                else:
                     print(f"Advertencia: {CONFIG_PATH} está vacío o corrupto. Usando pantalla completa.")
        else:
            print(f"Advertencia: No se encontró {CONFIG_PATH}. Usando pantalla completa.")
    
    except Exception as e:
        print(f"Error al leer ROI desde config.yaml: {e}. Usando pantalla completa.")

    # Fallback si todo falla: cachear "pantalla_completa" para no reintentar
    _cached_roi = "pantalla_completa" 
    _config_mtime = 0 # Resetear mtime para que intente recargar si el archivo aparece
    return "pantalla_completa"


def get_screenshot(region=None):
    """
    region: 
        - None (defecto): Usa el ROI de config.yaml.
        - dict: Usa la región específica pasada (ej. {'left':x,'top':y,'width':w,'height':h}).
        - False: Fuerza la captura de pantalla completa.
    devuelve: imagen BGR (numpy ndarray) o None si hay error
    """
    
    region_to_grab = None

    if region is None:
        # --- Lógica principal: Usar ROI de config.yaml ---
        roi_from_config = load_roi_from_config()
        if roi_from_config == "pantalla_completa":
            region_to_grab = None # Mss usará el monitor principal
        else:
            region_to_grab = roi_from_config # Usar el dict del ROI

    elif isinstance(region, dict):
        # --- Usar región específica pasada como argumento ---
        region_to_grab = region
    
    elif region is False:
        # --- Forzar pantalla completa ---
        region_to_grab = None
        
    
    try:
        with mss.mss() as sct:
            if region_to_grab is None:
                # Capturar monitor principal
                monitor = sct.monitors[1] 
                sct_im = sct.grab(monitor)
            else:
                # Capturar la región específica (del ROI o argumento)
                sct_im = sct.grab(region_to_grab)
                
            img = np.array(sct_im)  # BGRA
            # convertir BGRA -> BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
            
    except mss.ScreenShotError as e:
        print(f"Error de captura de pantalla (MSS): {e}")
        print(f"  Región intentada: {region_to_grab}")
        print("  Asegúrate de que las coordenadas del ROI estén dentro de la pantalla.")
        return None
    except Exception as e:
        print(f"Error inesperado en get_screenshot: {e}")
        return None
