import time
from utils import click_at, log

def collect_one_by_one(bot, detected_list, config):
    """
    Hace clic en todos los recursos detectados de manera seguida usando
    la lista de detecciones ya calculadas desde run_loop().
    Evita clics duplicados de templates muy similares.
    """
    collect_time = float(config.get("collect_time", 3.5))
    click_delay = 0.7

    if not detected_list:
        return

    # Extraer solo coordenadas, evitando duplicados cercanos
    detected_points = []
    for d in detected_list:
        cx, cy = d["cx"], d["cy"]
        if any(abs(cx - dx) < 45 and abs(cy - dy) < 45 for dx, dy in detected_points):
            continue
        detected_points.append((cx, cy))

    # log(f"Recursos filtrados: {len(detected_points)}. Haciendo clic en todos con delay humano.")

    # Clic en todos los recursos con delay humano y chequeo de pausa
    for i, (cx, cy) in enumerate(detected_points, start=1):
        if bot and not bot.running:
            log("Bot pausado. Abortando colecta.")
            return
        click_at(cx, cy)
        # log(f"Clic en recurso {i}/{len(detected_points)}.")

        # Delay entre clics respetando pausa
        if i < len(detected_points):
            for _ in range(int(click_delay*10)):
                if bot and not bot.running:
                    log("Bot pausado durante delay entre clics. Abortando colecta.")
                    return
                time.sleep(0.1)

    # Calcular estancia total en la sala
    total_wait = 5.8
    if len(detected_points) > 1:
        total_wait += collect_time * (len(detected_points) - 1)
    if len(detected_points) >= 4:
        total_wait += 1.5
        # log("4 o más recursos detectados, sumando 1.5s extra a la estancia.")

    # log(f"Esperando {total_wait}s en la sala por {len(detected_points)} recursos")
    # Espera total respetando pausa
    waited = 0.0
    interval = 0.2
    while waited < total_wait:
        if bot and not bot.running:
            log("Bot pausado durante espera final. Abortando espera.")
            return
        time.sleep(interval)
        waited += interval
