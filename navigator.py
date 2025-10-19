# navigator.py
# Funciones para moverse entre salidas según un patrón (map_path)

from utils import click_at, random_point_near, human_delay, log
import time

def move_to_next(bot, map_path, idx, config):
    """
    map_path: lista de [x,y]
    idx: índice actual (entras a la sala idx, y quieres hacer click en map_path[idx])
    Devuelve: nuevo índice (idx+1 % len)
    Respeta pausa del bot y espera post-click.
    """

    # Verificar si el bot está pausado antes de moverse
    if bot and not bot.running:
        log("Bot pausado antes de moverse. Abortando movimiento.")
        return idx

    # Coordenadas de la salida actual
    x, y = map_path[idx]
    rx, ry = random_point_near(x, y, radius=4)
    # log(f"Click en salida #{idx+1} en ({rx},{ry})")
    click_at(rx, ry)

    # Delay post-click respetando pausa
    wait = float(config.get("post_move_wait", 2.0))
    total_waited = 0.0
    interval = 0.2
    randomize = config.get("randomize_delays", True)

    while total_waited < wait:
        if bot and not bot.running:
            log("Bot pausado durante espera de movimiento. Abortando espera.")
            return idx
        time.sleep(interval)
        total_waited += interval

    # Calcular siguiente índice cíclico
    new_idx = (idx + 1) % len(map_path)
    return new_idx
