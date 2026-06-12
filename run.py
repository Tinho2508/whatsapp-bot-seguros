import logging
import threading
import webbrowser
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PORT = 5000

def abrir_navegador():
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")

if __name__ == "__main__":
    print(f"\n  🤖 WhatsApp Bot - Seguros")
    print(f"  ─────────────────────────")
    print(f"  Abrindo navegador em http://localhost:{PORT}\n")

    threading.Thread(target=abrir_navegador, daemon=True).start()

    from whatsapp_bot.webapp import app
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
