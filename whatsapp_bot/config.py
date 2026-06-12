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

# ── Integração com CRM ──────────────────────────────
# A chave supabase_service_key é lida do arquivo .env (nunca commitado)
# Crie um arquivo .env na raiz do projeto com:
#   SUPABASE_SERVICE_KEY=sua_chave_aqui
import os
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as _f:
        for _linha in _f:
            _linha = _linha.strip()
            if _linha and not _linha.startswith("#") and "=" in _linha:
                _k, _v = _linha.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

CRM_CONFIG = {
    "modo": "supabase",
    "supabase_service_key": os.environ.get("SUPABASE_SERVICE_KEY", ""),
}
