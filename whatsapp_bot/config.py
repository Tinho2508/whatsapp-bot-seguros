TEMPLATES = {
    "auto": "Olá {nome}! 👋 Seu seguro *Auto* vence em *{vencimento}*.\n"
            "Valor da renovação: *{valor}*.\n"
            "Gostaria de renovar? Posso ajudar com isso agora! 🚗✅",

    "residencial": "Olá {nome}! 👋 Seu seguro *Residencial* vence em *{vencimento}*.\n"
                   "Valor da renovação: *{valor}*.\n"
                   "Gostaria de renovar? Posso ajudar com isso agora! 🏠✅",

    "vida": "Olá {nome}! 👋 Seu seguro *Vida* vence em *{vencimento}*.\n"
            "Valor da renovação: *{valor}*.\n"
            "Gostaria de renovar? Posso ajudar com isso agora! 🙏✅",

    "saude": "Olá {nome}! 👋 Seu seguro *Saúde* vence em *{vencimento}*.\n"
             "Valor da renovação: *{valor}*.\n"
             "Gostaria de renovar? Posso ajudar com isso agora! 🏥✅",
}

TEMPLATE_PADRAO = "Olá {nome}! 👋 Tudo bem? Seu seguro vence em {vencimento}. Gostaria de renovar?"

COLUNAS_OBRIGATORIAS = ["nome", "telefone", "tipo_seguro"]
COLUNAS_OPCIONAIS = ["vencimento", "valor"]

CHROME_USER_DIR = "chrome_profile"

# Caminho do executável do Tesseract OCR (Windows)
# Deixe como None se o tesseract estiver no PATH do sistema
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
