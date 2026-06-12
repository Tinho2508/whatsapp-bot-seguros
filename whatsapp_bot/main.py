import logging
import sys
import time
from pathlib import Path
from datetime import datetime

from .config import TEMPLATES, TEMPLATE_PADRAO
from .reader import ler_clientes, validar_clientes
from .preview import PreviewWindow
from .sender import WhatsAppSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("whatsapp_bot")


def gerar_mensagem(cliente: dict) -> str:
    tipo = cliente.get("tipo_seguro", "").strip().lower()
    template = TEMPLATES.get(tipo, TEMPLATE_PADRAO)
    try:
        return template.format(
            nome=cliente.get("nome", "").strip(),
            vencimento=cliente.get("vencimento", "em breve").strip(),
            valor=cliente.get("valor", "a consultar").strip(),
        )
    except KeyError as e:
        logger.warning(f"Template para '{tipo}' requer campo {e}, usando template padrão")
        return TEMPLATE_PADRAO.format(
            nome=cliente.get("nome", "").strip(),
            vencimento=cliente.get("vencimento", "em breve").strip(),
        )


def _menu_principal() -> str:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("WhatsApp Bot - Origem dos dados")
    root.geometry("500x280")
    root.resizable(False, False)

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 250
    y = (root.winfo_screenheight() // 2) - 140
    root.geometry(f"+{x}+{y}")

    resultado = [None]

    tk.Label(root, text="Selecione a origem dos dados",
             font=("Segoe UI", 14, "bold")).pack(pady=(30, 10))
    tk.Label(root, text="Como deseja importar os clientes?",
             font=("Segoe UI", 10), fg="gray").pack(pady=(0, 20))

    def escolher(opt: str):
        resultado[0] = opt
        root.destroy()

    tk.Button(root, text="📄 Arquivo CSV / Excel", width=30, height=2,
              font=("Segoe UI", 11),
              command=lambda: escolher("arquivo")).pack(pady=5)

    tk.Button(root, text="📸 Capturar Tela (OCR)", width=30, height=2,
              font=("Segoe UI", 11),
              command=lambda: escolher("ocr")).pack(pady=5)

    tk.Button(root, text="❌ Sair", width=30, height=1,
              font=("Segoe UI", 10),
              command=lambda: escolher("sair")).pack(pady=10)

    root.mainloop()
    return resultado[0]


def _fluxo_arquivo() -> list[dict] | None:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()

    logger.info("Selecione o arquivo CSV ou Excel com os clientes")
    caminho = filedialog.askopenfilename(
        title="Selecionar arquivo de clientes",
        filetypes=[
            ("CSV", "*.csv"),
            ("Excel", "*.xls *.xlsx"),
            ("Todos", "*.*"),
        ],
    )
    if not caminho:
        logger.info("Nenhum arquivo selecionado.")
        return None

    try:
        clientes = ler_clientes(caminho)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao ler arquivo:\n{e}")
        logger.error(f"Erro ao ler arquivo: {e}")
        return None

    if not clientes:
        messagebox.showwarning("Aviso", "Nenhum cliente encontrado no arquivo.")
        return None

    erros = validar_clientes(clientes)
    if erros:
        msg = "Erros encontrados no arquivo:\n" + "\n".join(erros[:10])
        if len(erros) > 10:
            msg += f"\n... e mais {len(erros) - 10} erro(s)"
        messagebox.showerror("Validação", msg)
        logger.error(f"Erros de validação ({len(erros)})")
        return None

    logger.info(f"Total de clientes: {len(clientes)}")
    return clientes


def _fluxo_ocr() -> list[dict] | None:
    import tkinter as tk
    from tkinter import messagebox

    from .scanner import capturar_regiao, ocr
    from .parser import parsear_texto
    from .editor import EditorTabela

    root = tk.Tk()
    root.withdraw()

    logger.info("Posicione a janela com os dados dos clientes e clique OK")
    messagebox.showinfo(
        "Captura de Tela",
        "Posicione na tela a janela/planilha com os dados dos clientes.\n\n"
        "Após clicar em OK, use o mouse para selecionar a região\n"
        "da tela que contém os dados (clique e arraste).\n\n"
        "Pressione ESC para cancelar."
    )

    tentativas = 0
    while tentativas < 3:
        tentativas += 1
        logger.info(f"Captura de tela #{tentativas}...")
        imagem = capturar_regiao()

        if imagem is None:
            logger.info("Captura cancelada.")
            return None

        logger.info(f"Imagem capturada: {imagem.size}")
        texto = ocr(imagem)
        logger.info(f"Texto extraído:\n{texto[:500]}")

        if not texto.strip():
            logger.warning("Nenhum texto encontrado na região selecionada.")
            messagebox.showwarning(
                "OCR",
                "Nenhum texto foi encontrado na região selecionada.\n"
                "Tente novamente com uma região mais nítida."
            )
            continue

        clientes = parsear_texto(texto)

        if not clientes:
            logger.warning("Nenhum cliente identificado no OCR.")
            messagebox.showwarning(
                "OCR",
                "Não foi possível identificar clientes no texto.\n"
                "Tente capturar novamente com melhor resolução."
            )
            continue

        editor = EditorTabela(clientes)
        resultado = editor.mostrar()

        if resultado is None:
            return None
        if resultado == "reextrair":
            continue

        return resultado

    messagebox.showerror("Erro", "Não foi possível extrair dados após 3 tentativas.")
    return None


def main():
    import tkinter as tk
    from tkinter import messagebox

    origem = _menu_principal()
    if origem == "sair" or origem is None:
        logger.info("Programa encerrado pelo usuário.")
        return

    if origem == "arquivo":
        clientes = _fluxo_arquivo()
    elif origem == "ocr":
        clientes = _fluxo_ocr()
    else:
        return

    if not clientes:
        return

    logger.info(f"Processando {len(clientes)} cliente(s)")

    sender = WhatsAppSender()
    try:
        sender.conectar()
    except Exception as e:
        messagebox.showerror("WhatsApp", f"Falha ao conectar ao WhatsApp Web:\n{e}")
        logger.error(f"Falha na conexão WhatsApp: {e}")
        return

    log_path = Path(f"envio_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    enviados = []
    pulados = []
    erros_envio = []

    try:
        for i, cliente in enumerate(clientes, start=1):
            mensagem = gerar_mensagem(cliente)
            total = len(clientes)

            logger.info(f"\n{'='*50}")
            logger.info(f"Cliente {i}/{total}: {cliente['nome']} ({cliente.get('tipo_seguro', 'N/A')})")

            preview = PreviewWindow(cliente, mensagem, i, total)
            resultado = preview.mostrar()

            if resultado == "sair":
                logger.info("Usuário saiu do programa.")
                break

            elif resultado == "pular":
                logger.info(f"Pulando cliente: {cliente['nome']}")
                pulados.append(cliente)
                continue

            elif isinstance(resultado, tuple) and resultado[0] == "editar":
                mensagem = resultado[1]
                logger.info("Mensagem editada pelo usuário.")

            tel_raw = str(cliente.get("telefone", "")).strip()
            tel = tel_raw if tel_raw.startswith("55") else f"55{tel_raw}"

            ok = sender.enviar_mensagem(tel, mensagem)
            if ok:
                enviados.append({**cliente, "mensagem": mensagem})
                logger.info(f"✅ Enviado para {cliente['nome']}")
            else:
                erros_envio.append({**cliente, "mensagem": mensagem})
                logger.warning(f"❌ Falha ao enviar para {cliente['nome']}")

            if i < total and ok:
                pausa = 45
                logger.info(f"Aguardando {pausa}s para evitar bloqueio...")
                time.sleep(pausa)

    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário.")
    finally:
        sender.fechar()

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("tipo,cliente,telefone,status\n")
            for c in enviados:
                f.write(f"enviado,{c['nome']},{c['telefone']}\n")
            for c in pulados:
                f.write(f"pulado,{c['nome']},{c['telefone']}\n")
            for c in erros_envio:
                f.write(f"erro,{c['nome']},{c['telefone']}\n")

        logger.info(f"\n📊 Relatório salvo em: {log_path}")
        logger.info(f"✅ Enviados: {len(enviados)}")
        logger.info(f"⏭️  Pulados: {len(pulados)}")
        logger.info(f"❌ Erros:    {len(erros_envio)}")

        messagebox.showinfo(
            "Concluído",
            f"✅ Enviados: {len(enviados)}\n"
            f"⏭️  Pulados: {len(pulados)}\n"
            f"❌ Erros: {len(erros_envio)}"
        )


if __name__ == "__main__":
    main()
