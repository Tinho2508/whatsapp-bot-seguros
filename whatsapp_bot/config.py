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
# modo: "csv" (salva arquivo), "api" (envia para API), "automacao" (via Selenium)
CRM_CONFIG = {
    "modo": "supabase",
    "supabase_service_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im10YWhlYnR1YnVieWxubWF1enNhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjgxNzc2NCwiZXhwIjoyMDkyMzkzNzY0fQ.dBGUOKySuq5SIKO47WMaVrV3hGLMOjbF87Eqs9NQ1Mc",
}
