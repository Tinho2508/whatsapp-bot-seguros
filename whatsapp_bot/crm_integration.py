import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("whatsapp_bot.crm")


class CRMIntegracao:
    def __init__(self, config: dict):
        self.modo = config.get("modo", "csv")
        self.api_url = config.get("api_url", "").rstrip("/")
        self.api_token = config.get("api_token", "")
        self.crm_url = config.get("crm_url", "")
        self.crm_usuario = config.get("crm_usuario", "")
        self.crm_senha = config.get("crm_senha", "")

    @classmethod
    def from_config(cls):
        from .config import CRM_CONFIG
        return cls(CRM_CONFIG)

    def registrar_envio(self, cliente: dict, status: str, mensagem: str = ""):
        if self.modo == "api":
            return self._api_registrar(cliente, status, mensagem)
        elif self.modo == "automacao":
            logger.info(f"Modo automação: registro pendente para {cliente['nome']}")
            self._salvar_pendente(cliente, status, mensagem)
            return True
        else:
            return self._csv_registrar(cliente, status, mensagem)

    def _api_registrar(self, cliente: dict, status: str, mensagem: str):
        if not self.api_url or not self.api_token:
            logger.warning("API não configurada. Salvando como CSV.")
            return self._csv_registrar(cliente, status, mensagem)

        try:
            payload = {
                "nome": cliente.get("nome", ""),
                "telefone": cliente.get("telefone", ""),
                "tipo_seguro": cliente.get("tipo_seguro", ""),
                "vencimento": cliente.get("vencimento", ""),
                "valor": cliente.get("valor", ""),
                "status_envio": status,
                "mensagem": mensagem,
                "data_envio": datetime.now().isoformat(),
                "origem": "whatsapp-bot",
            }

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            resp = requests.post(
                f"{self.api_url}/leads",
                json=payload,
                headers=headers,
                timeout=15,
            )

            if resp.status_code in (200, 201):
                logger.info(f"Lead criado no CRM: {cliente['nome']} ({status})")
                return True
            else:
                logger.error(f"CRM API erro {resp.status_code}: {resp.text[:200]}")
                self._salvar_pendente(cliente, status, mensagem)
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"CRM API: conexão recusada em {self.api_url}")
            self._salvar_pendente(cliente, status, mensagem)
            return False
        except Exception as e:
            logger.error(f"CRM API erro: {e}")
            self._salvar_pendente(cliente, status, mensagem)
            return False

    def _csv_registrar(self, cliente: dict, status: str, mensagem: str) -> bool:
        return self._salvar_pendente(cliente, status, mensagem)

    def _salvar_pendente(self, cliente: dict, status: str, mensagem: str) -> bool:
        caminho = Path("crm_pendentes.csv")
        existe = caminho.exists()
        with open(caminho, "a", encoding="utf-8") as f:
            if not existe:
                f.write("data_hora,nome,telefone,tipo_seguro,vencimento,valor,status_envio,mensagem\n")
            linha = (
                f"{datetime.now().isoformat()},"
                f"{cliente.get('nome','')},"
                f"{cliente.get('telefone','')},"
                f"{cliente.get('tipo_seguro','')},"
                f"{cliente.get('vencimento','')},"
                f"{cliente.get('valor','')},"
                f"{status},"
                f"\"{mensagem.replace(chr(34),chr(34)+chr(34))}\"\n"
            )
            f.write(linha)
        logger.info(f"Registro salvo em crm_pendentes.csv: {cliente['nome']} ({status})")
        return True
