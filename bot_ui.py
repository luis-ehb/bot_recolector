# bot_ui.py
import os
import cv2
import yaml
import re
import tkinter as tk
from tkinter import ttk, messagebox # Importar ttk
import threading
import time
import keyboard
# --- Importación robusta de controller.Bot ---
try:
    from controller import Bot
except ImportError:
    import sys
    project_root = os.path.dirname(os.path.dirname(__file__))
    if project_root not in sys.path: sys.path.append(project_root)
    try: from src.controller import Bot
    except ImportError as e:
        print(f"Error CRÍTICO: No se pudo importar la clase Bot desde controller.py: {e}")
        messagebox.showerror("Error Crítico", "No se pudo encontrar 'controller.py'. El bot no funcionará.")
        class Bot: # Dummy Bot
            def __init__(self, config_path): self.running = False; self.config = {}
            def toggle_running(self): messagebox.showwarning("Bot", "Bot no inicializado (Falta controller.py).")
            def stop(self): messagebox.showwarning("Bot", "Bot no inicializado.")
            def run_loop(self): print("Bucle Bot (dummy).")
# --- Fin Importación ---

# --- Rutas ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
CAPTURAS_DIR = os.path.join(os.path.dirname(__file__), "..", "capturas-debug")
DEBUGS_DIR = os.path.join(os.path.dirname(__file__), "..", "debugs")
SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "sounds") # Ruta a sonidos
os.makedirs(DEBUGS_DIR, exist_ok=True)
os.makedirs(CAPTURAS_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(SOUNDS_DIR, exist_ok=True)

# --- Cargar templates ---
RESOURCE_TEMPLATES = {}
# (El código de carga de templates permanece igual)
if os.path.isdir(TEMPLATE_DIR):
    for fname in os.listdir(TEMPLATE_DIR):
        name, ext = os.path.splitext(fname)
        if ext.lower() not in [".png", ".jpg", ".jpeg"]: continue
        try:
            template = cv2.imread(os.path.join(TEMPLATE_DIR, fname), cv2.IMREAD_UNCHANGED)
            if template is None: continue
            if len(template.shape) == 3 and template.shape[2] == 4:
                template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
            RESOURCE_TEMPLATES.setdefault(name, []).append(template)
        except Exception as e: print(f"Error cargando template {fname}: {e}")
else: print(f"Advertencia: Directorio de templates '{TEMPLATE_DIR}' no existe.")
print(f"Templates cargados: {list(RESOURCE_TEMPLATES.keys())}")


# --- detect_template (sin cambios visuales) ---
def detect_template(img, template, label, conf_thresh=0.8):
    if img is None or template is None: return []
    if len(img.shape) == 3 and img.shape[2] == 4: img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    if len(template.shape) == 3 and template.shape[2] == 4: template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

    import numpy as np
    target_img = img
    target_tpl = template
    if len(img.shape) != len(template.shape):
         if len(img.shape) == 3: img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
         else: img_gray = img
         if len(template.shape) == 3: tpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
         else: tpl_gray = template
         target_img = img_gray
         target_tpl = tpl_gray

    try:
        h, w = target_tpl.shape[:2]
        res = cv2.matchTemplate(target_img, target_tpl, cv2.TM_CCOEFF_NORMED)
    except cv2.error as e: return []

    loc = np.where(res >= conf_thresh)
    detections = []
    seen_bboxes = []
    for pt in zip(*loc[::-1]):
        x1, y1 = pt
        x2, y2 = x1 + w, y1 + h
        cx, cy = x1 + w // 2, y1 + h // 2
        confidence = float(res[y1, x1])
        is_duplicate = False
        current_area = w * h
        if current_area == 0: continue
        for (sx1, sy1, sx2, sy2) in seen_bboxes:
            inter_x1, inter_y1 = max(x1, sx1), max(y1, sy1)
            inter_x2, inter_y2 = min(x2, sx2), min(y2, sy2)
            inter_w, inter_h = max(0, inter_x2 - inter_x1), max(0, inter_y2 - inter_y1)
            inter_area = inter_w * inter_h
            box1_area, box2_area = current_area, (sx2 - sx1) * (sy2 - sy1)
            union_area = box1_area + box2_area - inter_area
            if union_area == 0: continue
            iou = inter_area / union_area
            if iou > 0.5: is_duplicate = True; break
        if not is_duplicate:
            seen_bboxes.append((x1, y1, x2, y2))
            detections.append({"label": label, "cx": cx, "cy": cy})
            draw_img = img if len(img.shape) == 3 else cv2.cvtColor(target_img, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(draw_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(draw_img, f"{label} ({confidence:.2f})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (36,255,12), 1)
    return detections

# --- Clase BotUI ---
class BotUI:
    def __init__(self, master):
        self.master = master
        master.title("Bot Personal V1.0.0")
        master.geometry("650x600") # Ajustado tamaño
        master.configure(bg="#2E2E2E") # Fondo ligeramente más claro

        # --- Estilo TTK ---
        self.style = ttk.Style()
        try:
             self.style.theme_use('clam')
        except tk.TclError:
             print("Tema 'clam' no disponible, usando default.")
             self.style.theme_use('default')

        self.style.configure('.', background='#2E2E2E', foreground='#EAEAEA', font=('Segoe UI', 9))
        self.style.configure('TLabel', background='#2E2E2E', foreground='#EAEAEA', font=('Segoe UI', 10, 'bold'))
        self.style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        self.style.configure('TEntry', fieldbackground='#3C3C3C', foreground='#EAEAEA', insertcolor='white')
        self.style.map('TButton', background=[('active', '#5A5A5A')], foreground=[('active', '#FFFFFF')])
        self.style.configure('Play.TButton', background='#43B581', foreground='white')
        self.style.map('Play.TButton', background=[('active', '#368a65')])
        self.style.configure('Pause.TButton', background='#F1C40F', foreground='black')
        self.style.map('Pause.TButton', background=[('active', '#c8a00c')])
        self.style.configure('Stop.TButton', background='#F04747', foreground='white')
        self.style.map('Stop.TButton', background=[('active', '#c03a3a')])
        self.style.configure('Special.TButton', background='#7289DA', foreground='white')
        self.style.map('Special.TButton', background=[('active', '#5b6eae')])
        self.style.configure('Accent.TButton', background='#FAA61A', foreground='white')
        self.style.map('Accent.TButton', background=[('active', '#c78515')])
        self.style.configure('Save.TButton', background='#99AAB5', foreground='white')
        self.style.map('Save.TButton', background=[('active', '#7a8894')])
        # --- Fin Estilo TTK ---


        # Inicialización del Bot (manejo de errores mejorado)
        try: self.bot = Bot(CONFIG_PATH)
        except FileNotFoundError:
            messagebox.showerror("Error", f"No se encontró {CONFIG_PATH}. Se usarán defaults.")
            self.config = {}
            class DummyBot: # Define clase Dummy dentro del except
                def __init__(self, config_path): self.running = False; self.config = {}
                def toggle_running(self): messagebox.showwarning("Bot", "Bot no inicializado.")
                def stop(self): messagebox.showwarning("Bot", "Bot no inicializado.")
                def run_loop(self): print("Bucle Bot (dummy).")
            self.bot = DummyBot(CONFIG_PATH)
        except Exception as e:
            messagebox.showerror("Error", f"Error inicializando Bot (¿config.yaml?): {e}")
            self.config = {}
            class DummyBot: # Define clase Dummy dentro del except
                def __init__(self, config_path): self.running = False; self.config = {}
                def toggle_running(self): messagebox.showwarning("Bot", "Bot no inicializado.")
                def stop(self): messagebox.showwarning("Bot", "Bot no inicializado.")
                def run_loop(self): print("Bucle Bot (dummy).")
            self.bot = DummyBot(CONFIG_PATH)

        self.load_config()

        # --- Lógica de carga de map_path (sin cambios) ---
        map_path_data = self.config.get("map_path", [])
        fixed_map = []
        if isinstance(map_path_data, str):
            coords = re.findall(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', map_path_data)
            for x_str, y_str in coords:
                try: fixed_map.append([int(x_str), int(y_str)])
                except ValueError: continue
        elif isinstance(map_path_data, list):
            for item in map_path_data:
                if isinstance(item, list) and len(item) == 2:
                    try: fixed_map.append([int(item[0]), int(item[1])])
                    except (ValueError, TypeError): continue
                elif isinstance(item, str):
                    parts = item.replace("[", "").replace("]", "").split(",")
                    if len(parts) == 2:
                        try: fixed_map.append([int(parts[0].strip()), int(parts[1].strip())])
                        except ValueError: continue
        self.config["map_path"] = fixed_map
        # --- Fin Carga Map Path ---

        # Frames principales (ahora ttk.Frame)
        self.main_frame = ttk.Frame(master, padding="10 10 10 10")
        self.overrides_frame = ttk.Frame(master, padding="10 10 10 10")

        self.create_main_panel()
        # No crear panel overrides aquí, se crea al mostrar
        self.show_main_panel()

        # Iniciar hilos
        threading.Thread(target=self.keyboard_listener, daemon=True).start()
        threading.Thread(target=self.bot.run_loop, daemon=True).start()

    # --- keyboard_listener (sin cambios visuales) ---
    def keyboard_listener(self):
        try:
            self.load_config() # Cargar teclas desde config
            toggle_key = self.config.get("toggle_key", "f8")
            exit_key = self.config.get("exit_key", "esc")
            print(f"Listener teclado OK. Toggle: '{toggle_key}', Exit: '{exit_key}'")
            while True:
                if keyboard.is_pressed(toggle_key):
                    self.master.after(0, self.toggle_play)
                    while keyboard.is_pressed(toggle_key): time.sleep(0.05)
                if keyboard.is_pressed(exit_key):
                    print("Tecla salida presionada...")
                    self.bot.stop()
                    self.master.after(0, self.master.quit)
                    break
                time.sleep(0.1)
        except Exception as e:
            print(f"Error listener teclado: {e}")

    # --- load_config (sin cambios visuales, mejoras internas) ---
    def load_config(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded_config = yaml.safe_load(f)
                    if isinstance(loaded_config, dict): self.config = loaded_config
                    else:
                        if not hasattr(self, 'config') or not self.config: self.config = {}
            elif not hasattr(self, 'config') or not self.config: self.config = {}
        except yaml.YAMLError as e:
            print(f"Error leyendo {CONFIG_PATH}: {e}.")
            if not hasattr(self, 'config') or not self.config: self.config = {}
        except Exception as e:
            print(f"Error inesperado cargando config: {e}")
            if not hasattr(self, 'config') or not self.config: self.config = {}

        defaults = {
            "bot_token": "", "chat_id": "", "collect_time": 3.5, "post_move_wait": 2.2,
            "ROI": {"x": 0, "y": 0, "w": 1277, "h": 1076}, "post_move_overrides": {},
            "map_path": [], "toggle_key": "f8", "exit_key": "esc", "conf_thresh": 0.83,
            "scan_delay": 0.85, "randomize_delays": True, "auto_pause_on_arena": True,
            "model_path": None, "classes": []
        }
        for key, value in defaults.items(): self.config.setdefault(key, value)
        if not isinstance(self.config.get("ROI"), dict): self.config["ROI"] = defaults["ROI"].copy()
        if not isinstance(self.config.get("post_move_overrides"), dict): self.config["post_move_overrides"] = defaults["post_move_overrides"].copy()
        # Asegurar map_path sea lista internamente tras carga inicial
        if isinstance(self.config.get("map_path"), str):
            # Convertir string a lista ahora que tenemos defaults definidos
             map_str = self.config["map_path"]
             coords_list = []
             coords = re.findall(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', map_str)
             for x_str, y_str in coords:
                 try: coords_list.append([int(x_str), int(y_str)])
                 except ValueError: pass # Ignorar si hay algo mal formateado en el string
             self.config["map_path"] = coords_list
        elif not isinstance(self.config.get("map_path"), list):
             self.config["map_path"] = defaults["map_path"][:]


    # --- save_config (Función GENÉRICA para guardar self.config) ---
    def save_config(self, show_success_message=True):
        """Guarda el diccionario self.config actual en config.yaml."""
        try:
            yaml.SafeDumper.ignore_aliases = lambda *args: True
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    self.config, f, sort_keys=False, allow_unicode=True
                )
            if show_success_message:
                messagebox.showinfo("Configuración", "Guardado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")
            raise # Relanzar para que se sepa que falló

    # --- NUEVA FUNCIÓN: update_main_config ---
    def update_main_config(self):
        """Actualiza self.config SOLO con los valores del panel principal."""
        try:
            self.config["bot_token"] = self.bot_token_var.get()
            self.config["chat_id"] = self.chat_id_var.get()
            self.config["collect_time"] = float(self.collect_time_var.get())
            self.config["post_move_wait"] = float(self.post_move_wait_var.get())
            self.config["ROI"] = {
                "x": int(self.roi_x_var.get()), "y": int(self.roi_y_var.get()),
                "w": int(self.roi_w_var.get()), "h": int(self.roi_h_var.get()),
            }
            # NO TOCAMOS map_path ni post_move_overrides aquí
            return True # Indicar éxito
        except ValueError as e:
            messagebox.showerror("Error de Validación", f"Valor numérico inválido: {e}")
            return False # Indicar fallo

    # --- NUEVA FUNCIÓN: update_map_config ---
    def update_map_config(self):
        """Actualiza self.config SOLO con map_path y overrides del panel MAP."""
        new_overrides = {}
        if hasattr(self, 'override_vars'):
            for idx, override_var in self.override_vars.items():
                val = override_var.get().strip()
                if val:
                    try: new_overrides[str(idx)] = float(val)
                    except ValueError:
                        messagebox.showerror("Error de Validación", f"Override para {idx} debe ser número.")
                        return False # Indicar fallo
        self.config["post_move_overrides"] = new_overrides

        new_map = []
        if hasattr(self, 'map_path_vars'):
             for idx, (x_var, y_var) in self.map_path_vars.items():
                 try:
                     x_str, y_str = x_var.get().strip(), y_var.get().strip()
                     if x_str and y_str: new_map.append([int(x_str), int(y_str)])
                 except ValueError: continue # Ignorar filas inválidas
        self.config["map_path"] = new_map
        print(f"[DEBUG update_map_config] Actualizado self.config['map_path'] a: {new_map}")
        return True # Indicar éxito

    # --- NUEVA FUNCIÓN: save_main_config_action ---
    def save_main_config_action(self):
        """Acción del botón Guardar del panel principal."""
        if self.update_main_config(): # Si la validación pasa
            try:
                self.save_config() # Llama a la función genérica de guardado
            except:
                pass # El error ya se mostró en save_config

    # --- NUEVA FUNCIÓN: save_map_config_action ---
    def save_map_config_action(self):
        """Acción del botón Guardar Cambios del panel MAP."""
        if self.update_map_config(): # Si la validación pasa
            try:
                self.save_config() # Llama a la función genérica de guardado
            except:
                 pass # El error ya se mostró en save_config

    # --- create_main_panel (Ajustar comando del botón Guardar) ---
    def create_main_panel(self):
        frame = self.main_frame
        frame.columnconfigure(0, weight=1)

        tg_frame = ttk.LabelFrame(frame, text="Configuración Telegram", padding="10 10 10 10")
        tg_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 10))
        tg_frame.columnconfigure(1, weight=1)
        ttk.Label(tg_frame, text="Bot Token:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.bot_token_var = tk.StringVar(value=self.config.get("bot_token", ""))
        ttk.Entry(tg_frame, textvariable=self.bot_token_var, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(tg_frame, text="Chat ID:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.chat_id_var = tk.StringVar(value=self.config.get("chat_id", ""))
        ttk.Entry(tg_frame, textvariable=self.chat_id_var, width=50).grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        time_frame = ttk.LabelFrame(frame, text="Tiempos (segundos)", padding="10 10 10 10")
        time_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        time_frame.columnconfigure(1, weight=1)
        ttk.Label(time_frame, text="Tiempo Recolección:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.collect_time_var = tk.StringVar(value=str(self.config.get("collect_time", 3.5)))
        ttk.Entry(time_frame, textvariable=self.collect_time_var, width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(time_frame, text="Espera Post-Movimiento:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.post_move_wait_var = tk.StringVar(value=str(self.config.get("post_move_wait", 2.2)))
        ttk.Entry(time_frame, textvariable=self.post_move_wait_var, width=10).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        roi_frame = ttk.LabelFrame(frame, text="Región de Interés (ROI)", padding="10 5 10 5")
        roi_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 20))
        roi_defaults = {"x": 0, "y": 0, "w": 1277, "h": 1076}
        roi_config = self.config.get("ROI", roi_defaults)
        if not isinstance(roi_config, dict): roi_config = roi_defaults
        ttk.Label(roi_frame, text="X:").grid(row=0, column=0, sticky="w", padx=(0,2))
        self.roi_x_var = tk.StringVar(value=str(roi_config.get("x", roi_defaults["x"])))
        ttk.Entry(roi_frame, textvariable=self.roi_x_var, width=6).grid(row=0, column=1, padx=(0, 10))
        ttk.Label(roi_frame, text="Y:").grid(row=0, column=2, sticky="w", padx=(0,2))
        self.roi_y_var = tk.StringVar(value=str(roi_config.get("y", roi_defaults["y"])))
        ttk.Entry(roi_frame, textvariable=self.roi_y_var, width=6).grid(row=0, column=3, padx=(0, 10))
        ttk.Label(roi_frame, text="W:").grid(row=0, column=4, sticky="w", padx=(0,2))
        self.roi_w_var = tk.StringVar(value=str(roi_config.get("w", roi_defaults["w"])))
        ttk.Entry(roi_frame, textvariable=self.roi_w_var, width=6).grid(row=0, column=5, padx=(0, 10))
        ttk.Label(roi_frame, text="H:").grid(row=0, column=6, sticky="w", padx=(0,2))
        self.roi_h_var = tk.StringVar(value=str(roi_config.get("h", roi_defaults["h"])))
        ttk.Entry(roi_frame, textvariable=self.roi_h_var, width=6).grid(row=0, column=7, padx=(0, 0))

        button_frame = ttk.Frame(frame, padding="10 0 0 0")
        button_frame.grid(row=3, column=0, pady=(10, 0))
        button_frame.columnconfigure(0, weight=1); button_frame.columnconfigure(1, weight=1); button_frame.columnconfigure(2, weight=1)
        initial_style = 'Pause.TButton' if self.bot.running else 'Play.TButton'
        initial_text = 'Pause (F8)' if self.bot.running else 'Play (F8)'
        self.play_btn = ttk.Button(button_frame, text=initial_text, command=self.toggle_play, style=initial_style, width=15)
        self.play_btn.grid(row=0, column=0, columnspan=3, pady=(0, 15), ipady=5)
        ttk.Button(button_frame, text="TEST Templates", command=self.run_test, style='Special.TButton', width=18).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Editar MAP PATH", command=self.show_overrides_panel, style='Accent.TButton', width=18).grid(row=1, column=1, padx=5, pady=5, columnspan=2)
        # *** CAMBIO AQUÍ: Usar save_main_config_action ***
        ttk.Button(button_frame, text="Guardar Config", command=self.save_main_config_action, style='Save.TButton', width=18).grid(row=2, column=0, padx=5, pady=5)
        # *************************************************
        ttk.Button(button_frame, text="Cerrar App", command=self.stop_and_quit, style='Stop.TButton', width=18).grid(row=2, column=1, padx=5, pady=5, columnspan=2)

    # --- create_overrides_panel (Ajustar comando del botón Guardar) ---
    def create_overrides_panel(self):
        container = self.overrides_frame
        container.columnconfigure(0, weight=1); container.rowconfigure(0, weight=1)
        canvas = tk.Canvas(container, bg="#2E2E2E", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.grid(row=0, column=0, sticky='nsew'); scrollbar.grid(row=0, column=1, sticky='ns')

        frame = scrollable_frame
        frame.columnconfigure((1,2,3), weight=1)
        ttk.Label(frame, text="MAP PATH (Coordenadas X, Y) y Overrides de Espera (s)", anchor='center').grid(row=0, column=0, columnspan=4, pady=(10, 15), padx=10, sticky='ew')
        self.map_path_vars = {}; self.override_vars = {}
        ttk.Label(frame, text="#", anchor='center').grid(row=1, column=0, padx=2, pady=(0,5))
        ttk.Label(frame, text="X", anchor='center').grid(row=1, column=1, padx=2, pady=(0,5))
        ttk.Label(frame, text="Y", anchor='center').grid(row=1, column=2, padx=2, pady=(0,5))
        ttk.Label(frame, text="Espera(s)", anchor='center').grid(row=1, column=3, padx=(2,10), pady=(0,5))
        map_path_list = self.config.get("map_path", []); last_row = 1
        for idx, coords in enumerate(map_path_list):
            if not isinstance(coords, list) or len(coords) != 2: coords = [0, 0]
            x_var = tk.StringVar(value=str(coords[0])); y_var = tk.StringVar(value=str(coords[1]))
            ov_val = self.config.get("post_move_overrides", {}).get(str(idx), "")
            ov_var = tk.StringVar(value=str(ov_val))
            self.map_path_vars[idx] = (x_var, y_var); self.override_vars[idx] = ov_var
            base_row = idx + 2; last_row = base_row
            ttk.Label(frame, text=f"{idx}").grid(row=base_row, column=0, padx=(5,2), pady=2, sticky="e")
            ttk.Entry(frame, textvariable=x_var, width=7, justify='center').grid(row=base_row, column=1, pady=1, padx=2)
            ttk.Entry(frame, textvariable=y_var, width=7, justify='center').grid(row=base_row, column=2, pady=1, padx=2)
            ttk.Entry(frame, textvariable=ov_var, width=7, justify='center').grid(row=base_row, column=3, padx=(2, 10), pady=1)

        # --- Función interna add_map_coord_ui ---
        # **CORRECCIÓN:** Mover nonlocal al inicio de la función
        def add_map_coord_ui():
            nonlocal last_row # <<--- MOVIDO AQUÍ
            idx = len(self.map_path_vars)
            x_var = tk.StringVar(value="0"); y_var = tk.StringVar(value="0"); ov_var = tk.StringVar(value="")
            self.map_path_vars[idx] = (x_var, y_var); self.override_vars[idx] = ov_var
            new_row = last_row + 1
            ttk.Label(frame, text=f"{idx}").grid(row=new_row, column=0, padx=(5,2), pady=2, sticky="e")
            ttk.Entry(frame, textvariable=x_var, width=7, justify='center').grid(row=new_row, column=1, pady=1, padx=2)
            ttk.Entry(frame, textvariable=y_var, width=7, justify='center').grid(row=new_row, column=2, pady=1, padx=2)
            ttk.Entry(frame, textvariable=ov_var, width=7, justify='center').grid(row=new_row, column=3, padx=(2, 10), pady=1)
            button_row = new_row + 1
            add_button.grid(row=button_row, column=0, columnspan=4, pady=(20, 5))
            save_button.grid(row=button_row + 1, column=0, columnspan=2, pady=5, padx=5, sticky='ew')
            back_button.grid(row=button_row + 1, column=2, columnspan=2, pady=5, padx=5, sticky='ew')
            last_row = new_row # Actualizar last_row al final
        # --- Fin función interna ---

        button_row = last_row + 1
        add_button = ttk.Button(frame, text="+ Añadir Coordenada", command=add_map_coord_ui, style='Special.TButton')
        add_button.grid(row=button_row, column=0, columnspan=4, pady=(20, 5))

        # *** CAMBIO AQUÍ: Usar save_map_config_action ***
        save_button = ttk.Button(frame, text="Guardar Cambios", command=self.save_map_config_action, style='Save.TButton')
        # ************************************************
        save_button.grid(row=button_row + 1, column=0, columnspan=2, pady=5, padx=5, sticky='ew')

        back_button = ttk.Button(frame, text="Volver al Panel", command=self.show_main_panel, style='Accent.TButton')
        back_button.grid(row=button_row + 1, column=2, columnspan=2, pady=5, padx=5, sticky='ew')

    # --- show_main_panel ---
    def show_main_panel(self):
        try:
            self.load_config()
            if hasattr(self, 'bot_token_var'): self.bot_token_var.set(self.config.get("bot_token", ""))
            if hasattr(self, 'chat_id_var'): self.chat_id_var.set(self.config.get("chat_id", ""))
            if hasattr(self, 'collect_time_var'): self.collect_time_var.set(str(self.config.get("collect_time", 3.5)))
            if hasattr(self, 'post_move_wait_var'): self.post_move_wait_var.set(str(self.config.get("post_move_wait", 2.2)))
            roi_conf = self.config.get("ROI", {"x":0,"y":0,"w":1277,"h":1076})
            if not isinstance(roi_conf, dict): roi_conf = {"x":0,"y":0,"w":1277,"h":1076}
            for key in ["x", "y", "w", "h"]:
                 if hasattr(self, f"roi_{key}_var"): getattr(self, f"roi_{key}_var").set(str(roi_conf.get(key, 0)))
        except Exception as e: print(f"Error actualizando UI: {e}")
        self.overrides_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    # --- show_overrides_panel ---
    def show_overrides_panel(self):
        self.main_frame.pack_forget()
        for widget in self.overrides_frame.winfo_children(): widget.destroy()
        self.create_overrides_panel()
        self.overrides_frame.pack(fill="both", expand=True)

    # --- toggle_play ---
    def toggle_play(self):
        if hasattr(self.bot, 'toggle_running'):
             self.bot.toggle_running()
             if self.bot.running: self.play_btn.config(text="Pause (F8)", style='Pause.TButton')
             else: self.play_btn.config(text="Play (F8)", style='Play.TButton')
        else: messagebox.showerror("Error", "Bot no inicializado.")

    # --- stop_and_quit ---
    def stop_and_quit(self):
        print("Deteniendo bot...")
        if hasattr(self.bot, 'stop'): self.bot.stop()
        print("Cerrando interfaz...")
        self.master.after(100, self.master.quit)

    # --- run_test ---
    def run_test(self):
        print("Ejecutando Test de Templates...")
        if not os.path.exists(CAPTURAS_DIR): messagebox.showerror("Error", f"No existe '{CAPTURAS_DIR}'."); return
        img_files = [f for f in os.listdir(CAPTURAS_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        if not img_files: messagebox.showinfo("Info", f"No hay imágenes en '{CAPTURAS_DIR}'."); return
        conf_thresh_test = self.config.get('conf_thresh', 0.8)
        print(f"Usando umbral: {conf_thresh_test}"); detections_found = False
        for img_name in img_files:
            img_path = os.path.join(CAPTURAS_DIR, img_name); img_orig = cv2.imread(img_path)
            if img_orig is None: continue
            img_to_detect = img_orig.copy(); print(f"--- Procesando {img_name} ---"); found_in_img = False
            for res_name, templates in RESOURCE_TEMPLATES.items():
                for i, t in enumerate(templates):
                    if t is None: continue
                    dets = detect_template(img_to_detect, t, res_name, conf_thresh=conf_thresh_test)
                    if dets: found_in_img = True; detections_found = True
            if found_in_img:
                 debug_filename = f"debug_{os.path.splitext(img_name)[0]}.png"
                 debug_path = os.path.join(DEBUGS_DIR, debug_filename)
                 try: cv2.imwrite(debug_path, img_to_detect); print(f"  Resultado: {debug_path}")
                 except Exception as e: print(f"  Error guardando debug: {e}")
            else: print(f"  Sin coincidencias.")
        if detections_found: messagebox.showinfo("TEST", f"Test finalizado. Revisa '{DEBUGS_DIR}'.")
        else: messagebox.showwarning("TEST", f"No se encontró nada con umbral {conf_thresh_test}.")


# --- Punto de entrada ---
if __name__ == "__main__":
    root = tk.Tk()
    app = BotUI(root)
    root.protocol("WM_DELETE_WINDOW", app.stop_and_quit)
    root.mainloop()