import time
import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

from .config import CHROME_USER_DIR

logger = logging.getLogger(__name__)


class WhatsAppSender:
    URL = "https://web.whatsapp.com"
    TIMEOUT_BUSCA = 20
    TIMEOUT_QR = 120

    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None

    def _criar_driver(self):
        user_dir = Path(CHROME_USER_DIR).resolve()
        user_dir.mkdir(exist_ok=True)

        opts = Options()
        opts.add_argument(f"--user-data-dir={user_dir}")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        if self.headless:
            opts.add_argument("--headless=new")

        self.driver = webdriver.Chrome(options=opts)

    def conectar(self):
        logger.info("Abrindo WhatsApp Web...")
        self._criar_driver()
        self.driver.get(self.URL)

        try:
            WebDriverWait(self.driver, self.TIMEOUT_QR).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
            )
            logger.info("WhatsApp Web logado com sucesso!")
        except TimeoutException:
            logger.warning("QR Code pode ser necessário. Escaneie o QR Code na tela.")
            try:
                WebDriverWait(self.driver, self.TIMEOUT_QR).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
                )
            except TimeoutException:
                raise RuntimeError("Não foi possível conectar ao WhatsApp Web (QR expirou ou timeout).")

    def enviar_mensagem(self, telefone: str, mensagem: str) -> bool:
        if not self.driver:
            raise RuntimeError("WhatsApp não conectado. Chame conectar() primeiro.")

        try:
            logger.info(f"Enviando mensagem para {telefone}...")

            # Abre conversa com o número
            link = f"https://web.whatsapp.com/send?phone={telefone}"
            self.driver.get(link)

            # Aguarda a caixa de mensagem carregar
            caixa_msg = WebDriverWait(self.driver, self.TIMEOUT_BUSCA).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
            )
            time.sleep(2)

            # Digita a mensagem caractere por caractere (parece humano)
            for linha in mensagem.split("\n"):
                caixa_msg.send_keys(linha)
                caixa_msg.send_keys(Keys.SHIFT + Keys.ENTER)
                time.sleep(0.1)

            time.sleep(0.5)

            # Envia
            caixa_msg.send_keys(Keys.ENTER)
            time.sleep(3)

            logger.info(f"Mensagem enviada para {telefone}")
            return True

        except TimeoutException:
            logger.error(f"Timeout ao enviar para {telefone}. Número inválido?")
            return False
        except WebDriverException as e:
            logger.error(f"Erro WebDriver ao enviar para {telefone}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar para {telefone}: {e}")
            return False

    def fechar(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
