import time
import random
import pyautogui
import os
from playsound import playsound  # Librería para reproducir sonidos

# --- Funciones de delays humanos ---
def human_delay(base, randomize=True, jitter=0.4):
    """Devuelve un tiempo ligeramente aleatorio alrededor de base (segundos)."""
    if not randomize:
        return base
    return max(0.01, base + random.uniform(-jitter, jitter))

def random_point_near(x, y, radius=6):
    """Devuelve (x+dx, y+dy) con dx,dy pequeños para simular clicks imperfectos."""
    dx = random.randint(-radius, radius)
    dy = random.randint(-radius, radius)
    return x + dx, y + dy

def move_mouse_smooth(x, y, duration_min=0.05, duration_max=0.25):
    """Mueve el mouse con una duración aleatoria para parecer humano."""
    dur = random.uniform(duration_min, duration_max)
    pyautogui.moveTo(x, y, duration=dur, _pause=False)

def click_at(x, y, button='left', move_first=True, humanize=True):
    """
    Mueve y hace click en (x,y). 
    Si humanize=True, se mueve suavemente y añade pequeñas variaciones.
    """
    if humanize:
        x, y = random_point_near(x, y)
        if move_first:
            move_mouse_smooth(x, y)
    pyautogui.click(x=x, y=y, button=button)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# --- Sistema de alertas de sonido por evento ---
ALERT_SOUNDS = {
    "boton_retos": "sounds/boton_retos.mp3",
    "inventario_lleno": "sounds/inventario_lleno.mp3"
}

def play_alert(alert_name):
    """
    Reproduce un sonido de alerta según el nombre del evento.
    alert_name: clave en ALERT_SOUNDS ("boton_retos", "inventario_lleno", etc.)
    """
    path = ALERT_SOUNDS.get(alert_name)
    if path is None:
        log(f"No hay sonido definido para '{alert_name}'")
        return
    if not os.path.exists(path):
        log(f"Alerta de sonido: archivo no encontrado -> {path}")
        return
    try:
        playsound(path)
    except Exception as e:
        log(f"Error reproduciendo sonido {path}: {e}")
