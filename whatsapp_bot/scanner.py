import logging

import mss
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

from .config import TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

logger = logging.getLogger(__name__)


def capturar_regiao() -> Image.Image | None:
    """Janela transparente para selecionar região da tela com o mouse."""
    import tkinter as tk

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.configure(bg="gray")
    root.cursor("crosshair")

    canvas = tk.Canvas(root, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    rect = None
    start_x = start_y = 0
    captured = [None]

    def on_press(ev):
        nonlocal start_x, start_y, rect
        start_x, start_y = ev.x, ev.y
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y,
                                       outline="red", width=3, fill="white",
                                       stipple="gray25")

    def on_drag(ev):
        if rect:
            canvas.coords(rect, start_x, start_y, ev.x, ev.y)

    def on_release(ev):
        x1, y1, x2, y2 = start_x, start_y, ev.x, ev.y
        left, top = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)

        if w < 20 or h < 20:
            return

        root.withdraw()
        root.update()

        with mss.mss() as sct:
            monitor = {"left": left, "top": top, "width": w, "height": h}
            sct_img = sct.grab(monitor)
            captured[0] = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda e: root.destroy())

    root.mainloop()
    return captured[0]


def _preprocessar(imagem: Image.Image) -> Image.Image:
    """Melhora contraste e converte para escala de cinza para melhor OCR."""
    img = imagem.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def ocr(imagem: Image.Image, lang: str = "por") -> str:
    """Extrai texto da imagem usando Tesseract OCR."""
    img = _preprocessar(imagem)
    config = "--oem 3 --psm 6"
    texto = pytesseract.image_to_string(img, lang=lang, config=config)
    return texto.strip()
