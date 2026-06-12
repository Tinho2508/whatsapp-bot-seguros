import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger("whatsapp_bot.crm")


class CRMIntegracao:
    SUPABASE_URL = "https://mtahebtububylnmauzsa.supabase.co"

    def __init__(self, config: dict):
        self.modo = config.get("modo", "csv")
        self.service_key = config.get("supabase_service_key", "")

    @classmethod
    def from_config(cls):
        from .config import CRM_CONFIG
        return cls(CRM_CONFIG)

    def _gerar_id(self) -> str:
        agora = datetime.now()
        h = hashlib.sha256(f"{agora.isoformat()}{id(self)}".encode()).hexdigest()[:12]
        return agora.strftime("%Y%m%d%H%M%S") + h

    def registrar_envio(self, cliente: dict, status: str, mensagem: str = ""):
        if self.modo == "supabase" and self.service_key:
            return self._supabase_registrar(cliente, status, mensagem)
        else:
            return self._csv_registrar(cliente, status, mensagem)

    def _supabase_registrar(self, cliente: dict, status: str, mensagem: str) -> bool:
        headers = {
            "Authorization": f"Bearer {self.service_key}",
            "apikey": self.service_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        agora = datetime.now(timezone.utc).isoformat()

        # 1. Cria lead na tabela `leads`
        interesse = f"Seguro {cliente.get('tipo_seguro', 'Indefinido').capitalize()}"
        lead_payload = {
            "id": self._gerar_id(),
            "nome_cliente": cliente.get("nome", ""),
            "telefone": cliente.get("telefone", ""),
            "whatsapp": cliente.get("telefone", ""),
            "interesse": interesse,
            "origem": "WhatsApp Bot",
            "status": "Novo",
            "observacoes": (
                f"Enviado via WhatsApp Bot em {agora[:10]}.\n"
                f"Tipo: {cliente.get('tipo_seguro', 'N/A')}\n"
                f"Vencimento: {cliente.get('vencimento', 'N/A')}\n"
                f"Valor: {cliente.get('valor', 'N/A')}\n"
                f"Status envio: {status}\n"
                f"Mensagem: {mensagem[:200]}"
            ),
            "criado_em": agora,
        }

        try:
            resp = requests.post(
                f"{self.SUPABASE_URL}/rest/v1/leads",
                json=lead_payload,
                headers=headers,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Lead criado no Supabase: {cliente['nome']} ({status})")
            else:
                logger.error(f"Erro ao criar lead: {resp.status_code} {resp.text[:200]}")
                self._csv_registrar(cliente, status, mensagem)
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Supabase: conexão recusada")
            self._csv_registrar(cliente, status, mensagem)
            return False
        except Exception as e:
            logger.error(f"Supabase erro: {e}")
            self._csv_registrar(cliente, status, mensagem)
            return False

        # 2. Registra a mensagem enviada
        msg_payload = {
            "id": self._gerar_id(),
            "provider": "whatsapp_bot",
            "telefone": cliente.get("telefone", ""),
            "nome": cliente.get("nome", ""),
            "mensagem": mensagem,
            "tipo": "texto",
            "criado_em": agora,
        }

        try:
            resp = requests.post(
                f"{self.SUPABASE_URL}/rest/v1/whatsapp_messages",
                json=msg_payload,
                headers=headers,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Mensagem registrada no Supabase para {cliente['nome']}")
            else:
                logger.warning(f"Erro ao registrar mensagem: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Não foi possível registrar mensagem: {e}")

        return True

    def _csv_registrar(self, cliente: dict, status: str, mensagem: str) -> bool:
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
                f"\"{mensagem.replace(chr(34), chr(34) + chr(34))}\"\n"
            )
            f.write(linha)
        logger.info(f"Registro salvo em crm_pendentes.csv: {cliente['nome']} ({status})")
        return True
