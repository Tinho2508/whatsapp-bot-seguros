import csv
import pandas as pd
from pathlib import Path


def ler_clientes(caminho: str) -> list[dict]:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    ext = caminho.suffix.lower()

    if ext == ".csv":
        return _ler_csv(caminho)
    elif ext in (".xls", ".xlsx"):
        return _ler_excel(caminho)
    else:
        raise ValueError(f"Formato não suportado: {ext}. Use .csv, .xls ou .xlsx")


def _ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _ler_excel(caminho: Path) -> list[dict]:
    df = pd.read_excel(caminho, dtype=str)
    df = df.fillna("")
    return df.to_dict(orient="records")


def validar_clientes(clientes: list[dict]) -> list[str]:
    erros = []
    for i, c in enumerate(clientes, start=2):
        if not c.get("nome", "").strip():
            erros.append(f"Linha {i}: 'nome' vazio")
        tel = str(c.get("telefone", "")).strip()
        if not tel:
            erros.append(f"Linha {i}: 'telefone' vazio")
        elif not tel.startswith("55"):
            erros.append(f"Linha {i}: telefone '{tel}' deve começar com 55 (código do Brasil)")
    return erros
