# controller.py
import yaml
import time
import threading
import random
import pyautogui
import winsound
import os # Importar os
import re # Importar re para el fallback de map_path
from detector import detect, load_model, RESOURCE_TEMPLATES
from screencap import get_screenshot
from bot_collector import collect_one_by_one
from navigator import move_to_next
from utils import log, play_alert
from telegram_notifier import send_telegram

class Bot:
    def __init__(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            if not isinstance(self.config, dict):
                 print(f"Error: {config_path} no es un diccionario válido. Usando config vacía.")
                 self.config = {}
        except FileNotFoundError:
            print(f"Error: No se encontró {config_path}. Usando config vacía.")
            self.config = {}
        except Exception as e:
            print(f"Error CRÍTICO al cargar {config_path}: {e}. Usando config vacía.")
            self.config = {}

        # Cargar configuración con valores por defecto robustos
        defaults = {
            "model_path": None, "map_path": [], "conf_thresh": 0.83, "scan_delay": 0.85,
            "post_move_wait": 1.8, "randomize_delays": True, "auto_pause_on_arena": True,
            "post_move_overrides": {}, "resource_classes": [],
            "toggle_key": "f8", "exit_key": "esc", "bot_token": "", "chat_id": "",
            "ROI": {"x": 0, "y": 0, "w": 1277, "h": 1076},
            "collect_time": 3.5,
            "enable_scan_beep": False,
            "map_specific_templates": {} # *** AÑADIR DEFAULT ***
        }
        for key, value in defaults.items():
            self.config.setdefault(key, value)
        
        if not isinstance(self.config.get("ROI"), dict): self.config["ROI"] = defaults["ROI"].copy()
        if not isinstance(self.config.get("post_move_overrides"), dict): self.config["post_move_overrides"] = defaults["post_move_overrides"].copy()
        if not isinstance(self.config.get("map_specific_templates"), dict): self.config["map_specific_templates"] = defaults["map_specific_templates"].copy() # *** ASEGURAR DICT ***
        if not isinstance(self.config.get("map_path"), (list, str)): self.config["map_path"] = defaults["map_path"][:]


        self.model = load_model(self.config.get("model_path"))
        self.map_path = self.config.get("map_path") # bot_ui asegura que sea lista al final
        self.conf_thresh = float(self.config.get("conf_thresh"))
        self.scan_delay = float(self.config.get("scan_delay"))
        self.post_move_wait = float(self.config.get("post_move_wait"))
        self.randomize = bool(self.config.get("randomize_delays"))
        self.auto_pause_on_arena = bool(self.config.get("auto_pause_on_arena"))
        self.enable_scan_beep = bool(self.config.get("enable_scan_beep", False))
        
        # *** GUARDAR CONFIGURACIÓN DE TEMPLATES ESPECÍFICOS ***
        self.map_specific_templates = self.config.get("map_specific_templates", {})
        # *** LISTA DE TEMPLATES ESPECIALES QUE SIEMPRE SE BUSCAN ***
        self.special_templates = ["boton_retos", "inventario_lleno", "subida_oficio"]


        log(f"Bot INICIALIZADO.")

        self.idx = 0
        self.running = False
        self.stopped = False
        self.lock = threading.Lock()

        # Usar config para clases o fallback a keys de templates
        self.resource_classes = self.config.get("resource_classes")
        if not self.resource_classes: # Fallback si no está en config
            self.resource_classes = [
                c for c in RESOURCE_TEMPLATES.keys()
                if c not in self.special_templates # Usar la lista de especiales aquí
            ]
        # log(f"Recursos a buscar: {self.resource_classes}") # Comentado

    def toggle_running(self):
        with self.lock:
            self.running = not self.running
            state = "EJECUTANDO" if self.running else "PAUSADO"
            log(f"===== ESTADO CAMBIADO A: {state} =====")
            send_telegram(f"🤖 Bot ahora está en estado: {state}")

    def stop(self):
        with self.lock:
            self.stopped = True
            self.running = False
            log("===== DETENIENDO BOT (stop signal) =====")
            send_telegram("🛑 Bot detenido manualmente.")

    def run_loop(self):
        log(">>> Bucle principal del Bot INICIADO en segundo plano <<<")
        scan_start_time = None

        while not self.stopped:
            log_prefix = f"[Sala Idx:{self.idx}] "

            # ... (Medición de tiempo comentada) ...

            if not self.running:
                time.sleep(0.2)
                continue

            time.sleep(0.05) 

            if self.enable_scan_beep:
                try: winsound.Beep(1000, 100)
                except Exception: pass

            img = get_screenshot()
            if img is None:
                 log(f"{log_prefix}Error: Captura fallida. Reintentando...")
                 time.sleep(1)
                 continue

            # *** LÓGICA PARA DECIDIR QUÉ DETECTAR ***
            current_map_idx_str = str(self.idx)
            specific_templates = self.map_specific_templates.get(current_map_idx_str)

            templates_to_scan_now = []
            if specific_templates is None:
                # Caso 1: No hay entrada para este índice. Buscar TODO.
                templates_to_scan_now = list(RESOURCE_TEMPLATES.keys())
                # log(f"{log_prefix}Buscando todos los {len(templates_to_scan_now)} templates.")
            else:
                # Caso 2: Hay entrada (incluso si está vacía).
                # Buscar solo los templates específicos + los especiales.
                templates_to_scan_now = specific_templates + self.special_templates
                # log(f"{log_prefix}Buscando {len(templates_to_scan_now)} templates específicos/especiales.")
            # ****************************************

            # Detección (pasando la lista filtrada)
            dets = detect(self.model, img, conf=self.conf_thresh, classes=templates_to_scan_now)

            # --- Lógica de pausa (sin cambios) ---
            boton = [d for d in dets if d["label"] == "boton_retos"]
            if boton and self.auto_pause_on_arena:
                log(f"{log_prefix}Detectado boton_retos (arena). Pausando...")
                play_alert("boton_retos")
                send_telegram("⚠️ Bot ha detectado <b>BOTÓN RETOS (Arena)</b> y se ha pausado.")
                with self.lock: self.running = False
                continue

            inv_full = [d for d in dets if d["label"] == "inventario_lleno"]
            if inv_full:
                log(f"{log_prefix}Inventario lleno detectado. Pausando...")
                play_alert("inventario_lleno")
                pyautogui.press('h')
                send_telegram("📦 Inventario lleno detectado. Bot pausado automáticamente.")
                with self.lock: self.running = False
                continue
            
            # (Puedes añadir aquí la detección de "subida_oficio" si necesitas que haga algo)

            # --- FASE 1: Recolectar recursos ---
            # Filtrar 'dets' para que solo contenga los recursos reales (no los especiales)
            # self.resource_classes ya excluye los especiales
            resources_detected = [d for d in dets if d["label"] in self.resource_classes]

            if resources_detected:
                # log(f"{log_prefix}Recursos detectados: {[d['label'] for d in resources_detected]}. Recolectando...")
                collect_one_by_one(self, resources_detected, self.config)
                # log(f"{log_prefix}Recolección finalizada.")
                continue

            # --- FASE 2: Mover a la siguiente salida ---
            # log(f"{log_prefix}No hay recursos. Moviendo...")
            
            current_map_path = self.map_path
            if isinstance(current_map_path, str): # Fallback
                log(f"{log_prefix}Advertencia: map_path es un string, convirtiendo...")
                new_fixed_map = []
                coords = re.findall(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', current_map_path)
                for x_str, y_str in coords:
                    try: new_fixed_map.append([int(x_str), int(y_str)])
                    except ValueError: pass
                self.map_path = new_fixed_map
                current_map_path = self.map_path

            if not isinstance(current_map_path, list) or not current_map_path or self.idx >= len(current_map_path):
                log(f"{log_prefix}Error: map_path inválido o índice fuera de rango. Pausando.")
                with self.lock: self.running = False
                continue

            current_exit_index = self.idx
            # log(f"{log_prefix}Haciendo clic en salida índice {current_exit_index}...")

            try:
                self.idx = move_to_next(self, current_map_path, self.idx, self.config)
                # scan_start_time = time.perf_counter() # Comentado
            except IndexError:
                 log(f"{log_prefix}Error Crítico: Índice {current_exit_index} fuera de rango. Reiniciando índice a 0.")
                 self.idx = 0; scan_start_time = None; continue
            except Exception as e:
                 log(f"{log_prefix}Error en move_to_next: {e}. Pausando.");
                 with self.lock: self.running = False; scan_start_time = None; continue

            # --- Delay post-move ---
            overrides = self.config.get("post_move_overrides", {})
            try:
                override_val = overrides.get(str(current_exit_index))
                walk_delay_base = float(override_val) if override_val is not None else self.post_move_wait
                walk_delay = max(0.1, walk_delay_base + random.uniform(-0.15, 0.15)) if self.randomize else walk_delay_base
                if not isinstance(walk_delay, (int, float)) or walk_delay < 0:
                    walk_delay = 0.1
            except (ValueError, TypeError):
                 log(f"{log_prefix}Error convirtiendo delay. Usando 0.1s.")
                 walk_delay = 0.1
            except Exception as e:
                 log(f"{log_prefix}Error calculando walk_delay: {e}. Usando 0.1s.")
                 walk_delay = 0.1

            # log(f"{log_prefix}Esperando {walk_delay:.2f}s post-movimiento...")
            wait_start_perf = time.perf_counter()
            total_waited = 0.0; interval = 0.1
            while total_waited < walk_delay:
                if not self.running: 
                    scan_start_time = None; break
                time.sleep(interval); total_waited += interval
            # if self.running: log(f"{log_prefix}Espera completada en {time.perf_counter() - wait_start_perf:.3f}s.")

        log(">>> Bucle principal del Bot DETENIDO <<<")
        send_telegram("✅ Bucle principal terminado.")
