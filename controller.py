# controller.py
import yaml
import time
import threading
import random
import pyautogui
import winsound # <--- Para el pitido inmediato
from detector import detect, load_model, RESOURCE_TEMPLATES
from screencap import get_screenshot
from bot_collector import collect_one_by_one
from navigator import move_to_next
from utils import log, play_alert
from telegram_notifier import send_telegram # 🔹 import para Telegram

class Bot:
    def __init__(self, config_path):
        try: # Añadir try-except para la carga inicial
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
            "post_move_overrides": {}, "resource_classes": [], # Añadir si falta
            "toggle_key": "f8", "exit_key": "esc", "bot_token": "", "chat_id": "",
            "ROI": {"x": 0, "y": 0, "w": 1277, "h": 1076},
            "collect_time": 3.5
        }
        for key, value in defaults.items():
            self.config.setdefault(key, value)
        # Asegurarse que ROI, overrides y map_path sean tipos correctos
        if not isinstance(self.config.get("ROI"), dict): self.config["ROI"] = defaults["ROI"].copy()
        if not isinstance(self.config.get("post_move_overrides"), dict): self.config["post_move_overrides"] = defaults["post_move_overrides"].copy()
        if not isinstance(self.config.get("map_path"), (list, str)): self.config["map_path"] = defaults["map_path"][:]


        self.model = load_model(self.config.get("model_path"))
        # map_path se convierte a lista en bot_ui al cargar/procesar
        self.map_path = self.config.get("map_path")
        self.conf_thresh = float(self.config.get("conf_thresh"))
        self.scan_delay = float(self.config.get("scan_delay")) # Aunque no se use mucho ahora
        self.post_move_wait = float(self.config.get("post_move_wait"))
        self.randomize = bool(self.config.get("randomize_delays"))
        self.auto_pause_on_arena = bool(self.config.get("auto_pause_on_arena"))

        log(f"Bot INICIALIZADO.") # <-- Log esencial
        # log(f"Bot INICIALIZADO con post_move_wait: {self.post_move_wait}") # <-- Comentado

        self.idx = 0
        self.running = False
        self.stopped = False
        self.lock = threading.Lock()

        # Usar config para clases o fallback a keys de templates
        self.resource_classes = self.config.get("resource_classes")
        if not self.resource_classes: # Fallback si no está en config
            self.resource_classes = [
                c for c in RESOURCE_TEMPLATES.keys()
                if c not in ("boton_retos", "inventario_lleno")
            ]
        # log(f"Recursos a buscar: {self.resource_classes}") # <-- Comentado

    def toggle_running(self):
        with self.lock:
            self.running = not self.running
            state = "EJECUTANDO" if self.running else "PAUSADO"
            log(f"===== ESTADO CAMBIADO A: {state} =====") # <-- Log esencial
            send_telegram(f"🤖 Bot ahora está en estado: {state}")

    def stop(self):
        with self.lock:
            self.stopped = True
            self.running = False
            log("===== DETENIENDO BOT (stop signal) =====") # <-- Log esencial
            send_telegram("🛑 Bot detenido manualmente.")

    def run_loop(self):
        log(">>> Bucle principal del Bot INICIADO en segundo plano <<<") # <-- Log esencial
        scan_start_time = None # Para medir tiempo total

        while not self.stopped:
            log_prefix = f"[Sala Idx:{self.idx}] " # Prefijo para logs

            # --- Medición y Log del Tiempo Total (Comentado) ---
            # if scan_start_time is not None:
            #     scan_end_time = time.perf_counter()
            #     scan_duration_seconds = scan_end_time - scan_start_time
            #     scan_duration_ms = scan_duration_seconds * 1000
            #     log(f"{log_prefix}⏱️ Tiempo (Clic Salida -> Inicio Captura): {scan_duration_seconds:.3f} s ({scan_duration_ms:.1f} ms)")
            #     scan_start_time = None # Reiniciar
            # --- Fin Medición ---

            if not self.running:
                time.sleep(0.2)
                continue

            # Mínima pausa antes de hacer algo
            time.sleep(0.05)

            # *** PITIDO ANTES DE LA CAPTURA ***
            try:
                # Frecuencia en Hz (1000=medio), Duración en ms (100=corto)
                winsound.Beep(1000, 100)
            except Exception as e:
                # Solo imprimir si falla (ej. no Windows)
                # print(f"{log_prefix}DEBUG: Iniciando captura (no beep: {e})") # <-- Comentado
                pass
            # ***********************************

            # Captura de pantalla
            img = get_screenshot()
            if img is None:
                 log(f"{log_prefix}Error: Captura fallida. Reintentando...") # <-- Log de Error esencial
                 time.sleep(1)
                 continue

            # Detección
            classes_to_detect = list(RESOURCE_TEMPLATES.keys()) # Detectar todo
            dets = detect(self.model, img, conf=self.conf_thresh, classes=classes_to_detect)

            # --- Lógica de pausa por 'boton_retos' o 'inventario_lleno' ---
            boton = [d for d in dets if d["label"] == "boton_retos"]
            if boton and self.auto_pause_on_arena:
                log(f"{log_prefix}Detectado boton_retos (arena). Pausando...") # <-- Log esencial
                play_alert("boton_retos")
                send_telegram("⚠️ Bot ha detectado <b>BOTÓN RETOS (Arena)</b> y se ha pausado.")
                with self.lock: self.running = False
                continue

            inv_full = [d for d in dets if d["label"] == "inventario_lleno"]
            if inv_full:
                log(f"{log_prefix}Inventario lleno detectado. Pausando...") # <-- Log esencial
                play_alert("inventario_lleno")
                pyautogui.press('h')
                send_telegram("📦 Inventario lleno detectado. Bot pausado automáticamente.")
                with self.lock: self.running = False
                continue

            # --- FASE 1: Recolectar recursos ---
            resources_detected = [d for d in dets if d["label"] in self.resource_classes]
            if resources_detected:
                # log(f"{log_prefix}Recursos detectados: {[d['label'] for d in resources_detected]}. Recolectando...") # <-- Comentado
                collect_one_by_one(self, resources_detected, self.config)
                # log(f"{log_prefix}Recolección finalizada.") # <-- Comentado
                continue # Volver a escanear tras recolectar

            # --- FASE 2: Mover a la siguiente salida ---
            # log(f"{log_prefix}No hay recursos. Moviendo...") # <-- Comentado
            
            # Asegurarse que map_path sea una lista válida y el índice esté dentro
            # (Comprobación movida desde __init__ para asegurar que sea una lista al usar)
            current_map_path = self.map_path
            if isinstance(current_map_path, str): # Fallback si sigue siendo string
                log(f"{log_prefix}Advertencia: map_path es un string, convirtiendo...")
                new_fixed_map = []
                coords = re.findall(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', current_map_path)
                for x_str, y_str in coords:
                    try: new_fixed_map.append([int(x_str), int(y_str)])
                    except ValueError: pass
                self.map_path = new_fixed_map # Actualizar el atributo de clase
                current_map_path = self.map_path # Usar la nueva lista

            if not isinstance(current_map_path, list) or not current_map_path or self.idx >= len(current_map_path):
                log(f"{log_prefix}Error: map_path inválido ({current_map_path}) o índice ({self.idx}) fuera de rango ({len(current_map_path)}). Pausando.") # <-- Log de Error esencial
                with self.lock: self.running = False
                continue

            current_exit_index = self.idx
            # log(f"{log_prefix}Haciendo clic en salida índice {current_exit_index}...") # <-- Comentado

            try:
                self.idx = move_to_next(self, current_map_path, self.idx, self.config)
                # *** INICIAR TEMPORIZADOR DESPUÉS DEL CLIC ***
                # scan_start_time = time.perf_counter() # <-- Comentado (para medición)
                # ------------------------------------------

            except IndexError:
                 log(f"{log_prefix}Error Crítico: Índice {current_exit_index} fuera de rango. Reiniciando índice a 0.") # <-- Log de Error esencial
                 self.idx = 0; scan_start_time = None; continue
            except Exception as e:
                 log(f"{log_prefix}Error en move_to_next: {e}. Pausando."); # <-- Log de Error esencial
                 with self.lock: self.running = False; scan_start_time = None; continue

            # --- Delay post-move ---
            overrides = self.config.get("post_move_overrides", {})
            try:
                override_val = overrides.get(str(current_exit_index))
                walk_delay_base = float(override_val) if override_val is not None else self.post_move_wait
                walk_delay = max(0.1, walk_delay_base + random.uniform(-0.15, 0.15)) if self.randomize else walk_delay_base
                if not isinstance(walk_delay, (int, float)) or walk_delay < 0:
                    # log(f"Advertencia: walk_delay calculado inválido ({walk_delay}). Usando 0.1s.") # <-- Comentado
                    walk_delay = 0.1
            except (ValueError, TypeError):
                 log(f"{log_prefix}Error convirtiendo delay (override:'{override_val}', global:'{self.post_move_wait}'). Usando 0.1s.") # <-- Log de Error esencial
                 walk_delay = 0.1
            except Exception as e:
                 log(f"{log_prefix}Error inesperado calculando walk_delay: {e}. Usando 0.1s.") # <-- Log de Error esencial
                 walk_delay = 0.1

            # log(f"{log_prefix}Esperando {walk_delay:.2f}s post-movimiento...") # <-- Comentado
            wait_start_perf = time.perf_counter()
            total_waited = 0.0; interval = 0.1 # Intervalo más corto
            while total_waited < walk_delay:
                if not self.running: 
                    # log(f"{log_prefix}Pausa durante espera."); # <-- Comentado
                    scan_start_time = None; break
                time.sleep(interval); total_waited += interval
            # wait_end_perf = time.perf_counter()
            # if self.running: log(f"{log_prefix}Espera completada en {wait_end_perf - wait_start_perf:.3f}s.") # <-- Comentado

        log(">>> Bucle principal del Bot DETENIDO <<<") # <-- Log esencial
        send_telegram("✅ Bucle principal terminado.") # <-- Mantener si usas Telegram