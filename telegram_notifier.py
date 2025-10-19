# telegram_notifier.py
import requests
import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

def load_telegram_config():
    """Carga bot_token y chat_id desde config.yaml."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            bot_token = cfg.get("bot_token", "")
            chat_id = cfg.get("chat_id", "")
            return bot_token, chat_id
    return "", ""

def send_telegram(message: str, bot_token: str = None, chat_id: str = None):
    """Envía un mensaje de texto a Telegram usando bot_token y chat_id del config si no se pasan."""
    if bot_token is None or chat_id is None:
        bot_token_cfg, chat_id_cfg = load_telegram_config()
        bot_token = bot_token or bot_token_cfg
        chat_id = chat_id or chat_id_cfg

    if not bot_token or not chat_id:
        print("[Telegram Error] Bot token o Chat ID no configurados")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=2)
    except Exception as e:
        print(f"[Telegram Error] {e}")
