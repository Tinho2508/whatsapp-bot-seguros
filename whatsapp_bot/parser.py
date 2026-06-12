import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

RE_TELEFONE = re.compile(
    r'(?:55\s*)?'         # código do Brasil opcional
    r'\(?(\d{2})\)?'      # DDD
    r'\s*(\d{4,5})'       # 4 ou 5 dígitos
    r'[-\s]?'
    r'(\d{4})'            # 4 dígitos finais
)

RE_VENCIMENTO = re.compile(r'(\d{2})/(\d{2})(?:/(\d{4}))?')
RE_VALOR = re.compile(r'R?\$?\s*([\d.]+,\d{2})')
RE_TIPO_SEGURO = re.compile(
    r'(auto|residencial|vida|saude|empresarial|viagem|prestamista)',
    re.IGNORECASE
)

TIPOS_NORMALIZADOS = {
    "auto": "auto",
    "residencial": "residencial",
    "vida": "vida",
    "saude": "saude",
    "empresarial": "empresarial",
    "viagem": "viagem",
    "prestamista": "prestamista",
}


def _extrair_telefone(texto: str) -> Optional[str]:
    m = RE_TELEFONE.search(texto)
    if m:
        ddd, p1, p2 = m.groups()
        return f"55{ddd}{p1}{p2}"
    return None


def _extrair_vencimento(texto: str) -> Optional[str]:
    m = RE_VENCIMENTO.search(texto)
    if m:
        d, mes, ano = m.groups()
        if ano:
            return f"{d}/{mes}/{ano}"
        return f"{d}/{mes}"
    return None


def _extrair_valor(texto: str) -> Optional[str]:
    m = RE_VALOR.search(texto)
    if m:
        return f"R$ {m.group(1)}"
    return None


def _extrair_tipo(texto: str) -> Optional[str]:
    m = RE_TIPO_SEGURO.search(texto)
    if m:
        return TIPOS_NORMALIZADOS.get(m.group(1).lower(), m.group(1).lower())
    return None


def _extrair_nome(texto: str, fields: dict) -> str:
    """Pega tudo antes do telefone na linha como nome."""
    m = RE_TELEFONE.search(texto)
    if m:
        before = texto[:m.start()].strip()
    else:
        before = texto
    before = re.sub(r'[^A-Za-zÀ-ÿ\s]', '', before).strip()
    before = re.sub(r'\s+', ' ', before).strip()
    return before if before else "Desconhecido"


def parsear_linha(linha: str) -> Optional[dict]:
    """Tenta extrair um cliente de uma linha de texto OCR."""
    linha = linha.strip()
    if not linha or len(linha) < 5:
        return None

    fields = {}

    telefone = _extrair_telefone(linha)
    if telefone:
        fields["telefone"] = telefone

    tipo = _extrair_tipo(linha)
    if tipo:
        fields["tipo_seguro"] = tipo

    vencimento = _extrair_vencimento(linha)
    if vencimento:
        fields["vencimento"] = vencimento

    valor = _extrair_valor(linha)
    if valor:
        fields["valor"] = valor

    if "telefone" not in fields:
        return None

    nome = _extrair_nome(linha, fields)
    fields["nome"] = nome if nome else "Desconhecido"

    if "tipo_seguro" not in fields:
        fields["tipo_seguro"] = "indefinido"

    return fields


def parsear_texto(texto: str) -> list[dict]:
    """Parseia texto OCR completo em lista de clientes."""
    clientes = []
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]

    for linha in linhas:
        cliente = parsear_linha(linha)
        if cliente:
            clientes.append(cliente)
        else:
            logger.debug(f"Linha não reconhecida: {linha}")

    logger.info(f"OCR: {len(linhas)} linhas lidas, {len(clientes)} clientes identificados")
    return clientes
