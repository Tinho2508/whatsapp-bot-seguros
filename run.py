import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from whatsapp_bot.gui import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
