import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue

import flask
from flask import Flask, request, jsonify, render_template

from .config import TEMPLATES, TEMPLATE_PADRAO
from .reader import ler_clientes, validar_clientes
from .scanner import capturar_regiao, ocr
from .parser import parsear_texto
from .sender import WhatsAppSender

logger = logging.getLogger("whatsapp_bot.web")

app = Flask(__name__, template_folder="templates")

_state = {
    "clientes": [],
    "mensagens": {},
    "sender": None,
    "send_running": False,
    "send_progress": {"total": 0, "current": 0, "status": "", "done": False},
}


def _gerar_mensagem(cliente: dict) -> str:
    tipo = cliente.get("tipo_seguro", "").strip().lower()
    template = TEMPLATES.get(tipo, TEMPLATE_PADRAO)
    try:
        return template.format(
            nome=cliente.get("nome", "").strip(),
            vencimento=cliente.get("vencimento", "em breve").strip(),
            valor=cliente.get("valor", "a consultar").strip(),
        )
    except KeyError:
        return TEMPLATE_PADRAO.format(
            nome=cliente.get("nome", "").strip(),
            vencimento=cliente.get("vencimento", "em breve").strip(),
        )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/clientes")
def listar_clientes():
    clientes = []
    for i, c in enumerate(_state["clientes"]):
        msg = _state["mensagens"].get(i, _gerar_mensagem(c))
        clientes.append({**c, "idx": i, "mensagem": msg})
    return jsonify(clientes)


@app.route("/api/cliente/<int:idx>/mensagem", methods=["POST"])
def atualizar_mensagem(idx):
    data = request.get_json()
    if data and "mensagem" in data:
        _state["mensagens"][idx] = data["mensagem"]
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 400


@app.route("/api/importar/arquivo", methods=["POST"])
def importar_arquivo():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400

    tmp = Path("_temp_import" + Path(f.filename).suffix)
    f.save(tmp)

    try:
        clientes = ler_clientes(str(tmp))
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return jsonify({"error": str(e)}), 400
    finally:
        tmp.unlink(missing_ok=True)

    if not clientes:
        return jsonify({"error": "Nenhum cliente encontrado"}), 400

    erros = validar_clientes(clientes)
    if erros:
        return jsonify({"error": erros[0] if len(erros) == 1 else f"{len(erros)} erro(s): {erros[0]}"}), 400

    _state["clientes"] = clientes
    _state["mensagens"] = {}
    logger.info(f"{len(clientes)} clientes importados de {f.filename}")
    return jsonify({"ok": True, "total": len(clientes)})


@app.route("/api/importar/ocr")
def importar_ocr():
    logger.info("OCR: captura de tela iniciada...")
    imagem = capturar_regiao()
    if imagem is None:
        return jsonify({"error": "Captura cancelada"}), 400

    texto = ocr(imagem)
    if not texto.strip():
        return jsonify({"error": "Nenhum texto encontrado na imagem"}), 400

    clientes = parsear_texto(texto)
    if not clientes:
        return jsonify({"error": "Nenhum cliente identificado no texto"}), 400

    _state["clientes"] = clientes
    _state["mensagens"] = {}
    logger.info(f"{len(clientes)} clientes importados via OCR")
    return jsonify({"ok": True, "total": len(clientes)})


@app.route("/api/whatsapp/conectar", methods=["POST"])
def conectar_whatsapp():
    if _state["sender"]:
        try:
            _state["sender"].fechar()
        except Exception:
            pass
        _state["sender"] = None

    try:
        sender = WhatsAppSender()
        sender.conectar()
        _state["sender"] = sender
        logger.info("WhatsApp Web conectado!")
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Falha conexão WhatsApp: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/whatsapp/status")
def status_whatsapp():
    return jsonify({
        "conectado": _state["sender"] is not None,
    })


@app.route("/api/enviar", methods=["POST"])
def iniciar_envio():
    if _state["send_running"]:
        return jsonify({"error": "Envio já em andamento"}), 400
    if not _state["sender"]:
        return jsonify({"error": "WhatsApp não conectado"}), 400

    data = request.get_json()
    indices = data.get("indices", [])
    if not indices:
        return jsonify({"error": "Nenhum cliente selecionado"}), 400

    _state["send_running"] = True
    _state["send_progress"] = {"total": len(indices), "current": 0, "status": "iniciando", "done": False}

    def enviar():
        sender = _state["sender"]
        for pos, idx in enumerate(indices, start=1):
            if not _state["send_running"]:
                break
            cliente = _state["clientes"][idx]
            msg = _state["mensagens"].get(idx, _gerar_mensagem(cliente))
            tel = str(cliente.get("telefone", "")).strip()
            if not tel.startswith("55"):
                tel = f"55{tel}"

            _state["send_progress"]["current"] = pos
            _state["send_progress"]["status"] = f"enviando {cliente['nome']}"

            try:
                ok = sender.enviar_mensagem(tel, msg)
                status = "ok" if ok else "erro"
                _state["send_progress"]["status"] = f"{'✅' if ok else '❌'} {cliente['nome']}"
                logger.info(f"[{pos}/{len(indices)}] {status.upper()} - {cliente['nome']}")
            except Exception as e:
                _state["send_progress"]["status"] = f"❌ {cliente['nome']} - {e}"
                logger.error(f"[{pos}/{len(indices)}] ERRO - {cliente['nome']}: {e}")

            if pos < len(indices):
                time.sleep(45)

        _state["send_running"] = False
        _state["send_progress"]["done"] = True
        _state["send_progress"]["status"] = "concluido"
        logger.info("Envio concluído!")

    threading.Thread(target=enviar, daemon=True).start()
    return jsonify({"ok": True, "total": len(indices)})


@app.route("/api/enviar/progresso")
def progresso_envio():
    return jsonify(_state["send_progress"])


@app.route("/api/enviar/parar", methods=["POST"])
def parar_envio():
    _state["send_running"] = False
    _state["send_progress"]["status"] = "parado"
    logger.info("Envio interrompido pelo usuário.")
    return jsonify({"ok": True})
