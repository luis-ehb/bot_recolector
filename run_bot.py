# run_bot.py
# Archivo que ejecutas: python src/run_bot.py
# Registra la tecla F8 para play/pause y ESC para salir

import os
import threading
import time
from controller import Bot
from utils import log

try:
    import keyboard
except Exception as e:
    keyboard = None
    print("Advertencia: módulo 'keyboard' no disponible o sin permisos. Puede requerir privilegios de administrador en Linux.")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

def main():
    bot = Bot(CONFIG_PATH)

    # thread del bucle principal
    t = threading.Thread(target=bot.run_loop, daemon=True)
    t.start()

    # hotkeys (F8 para play/pause, ESC para stop)
    toggle_key = bot.config.get("toggle_key", "f8")
    exit_key = bot.config.get("exit_key", "esc")

    if keyboard:
        log(f"Hotkeys: {toggle_key.upper()} = Play/Pause, {exit_key.upper()} = Stop/Exit")
        keyboard.add_hotkey(toggle_key, bot.toggle_running)
        keyboard.add_hotkey(exit_key, bot.stop)
        # bloquear aquí hasta que se pulse exit_key
        try:
            keyboard.wait(exit_key)
        except KeyboardInterrupt:
            pass
    else:
        # fallback sin hotkeys: usar entrada por consola
        log("keyboard no disponible. Usar consola: escribe 'start' luego ENTER, 'stop' para terminar.")
        while not bot.stopped:
            cmd = input("Comando (start/stop/toggle): ").strip().lower()
            if cmd in ("start", "s"):
                if not bot.running:
                    bot.toggle_running()
            elif cmd in ("toggle", "t"):
                bot.toggle_running()
            elif cmd in ("stop", "exit", "q"):
                bot.stop()
                break
            else:
                log("Comando no reconocido.")

    # esperar que el hilo termine
    t.join(timeout=1.0)
    log("Proceso finalizado.")

if __name__ == "__main__":
    main()
