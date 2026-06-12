import logging
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox
import tkinter as tk

from .config import TEMPLATES, TEMPLATE_PADRAO
from .reader import ler_clientes, validar_clientes
from .scanner import capturar_regiao, ocr
from .parser import parsear_texto
from .editor import EditorTabela
from .sender import WhatsAppSender

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
    except KeyError:
        return TEMPLATE_PADRAO.format(
            nome=cliente.get("nome", "").strip(),
            vencimento=cliente.get("vencimento", "em breve").strip(),
        )


class LogHandler(logging.Handler):
    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + "\n"
        self.text_widget.after(0, self._append, msg)

    def _append(self, msg):
        self.text_widget.insert(tk.END, msg)
        self.text_widget.see(tk.END)


class App(tk.Tk):
    CAMPOS = ["nome", "telefone", "tipo_seguro", "vencimento", "valor"]

    def __init__(self):
        super().__init__()
        self.title("WhatsApp Bot - Seguros")
        self.geometry("1050x700")
        self.minsize(900, 600)

        self.clientes: list[dict] = []
        self.mensagens: dict[int, str] = {}
        self.sender: WhatsAppSender | None = None
        self.send_queue = queue.Queue()
        self._send_active = False
        self._cliente_atual_idx: int | None = None

        self._centralizar()
        self._montar_ui()
        self._configurar_log()

        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _centralizar(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1050) // 2
        y = (self.winfo_screenheight() - 700) // 2
        self.geometry(f"+{x}+{y}")

    def _montar_ui(self):
        # === Topo ===
        frame_top = tk.Frame(self)
        frame_top.pack(fill=tk.X, padx=15, pady=(10, 5))
        tk.Label(frame_top, text="WhatsApp Bot - Seguros",
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        # === Importação ===
        frame_import = tk.Frame(self)
        frame_import.pack(fill=tk.X, padx=15, pady=5)

        tk.Button(frame_import, text=" Importar CSV / Excel",
                  font=("Segoe UI", 10), bg="#4CAF50", fg="white",
                  command=self._importar_arquivo).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(frame_import, text=" Capturar Tela (OCR)",
                  font=("Segoe UI", 10), bg="#2196F3", fg="white",
                  command=self._importar_ocr).pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_status = tk.Label(frame_import, text="Nenhum cliente carregado",
                                   font=("Segoe UI", 9), fg="gray")
        self.lbl_status.pack(side=tk.RIGHT)

        # === Painel principal ===
        frame_principal = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # --- Esquerda: Tabela de clientes ---
        frame_tabela = tk.Frame(frame_principal)
        frame_principal.add(frame_tabela, width=580, minsize=400)

        tk.Label(frame_tabela, text="Clientes", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)

        frame_tree_top = tk.Frame(frame_tabela)
        frame_tree_top.pack(fill=tk.X)
        tk.Button(frame_tree_top, text="Marcar Todos", command=self._marcar_todos).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(frame_tree_top, text="Desmarcar Todos", command=self._desmarcar_todos).pack(side=tk.LEFT)

        frame_tree = tk.Frame(frame_tabela)
        frame_tree.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        cols = ["sel"] + self.CAMPOS
        self.tree = ttk.Treeview(frame_tree, columns=cols, show="headings", selectmode="browse", height=12)
        scroll_y = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame_tree, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scroll_y.set, xscroll=scroll_x.set)

        self.tree.heading("sel", text="")
        self.tree.column("sel", width=30, anchor="center", stretch=False)
        for col in self.CAMPOS:
            label = col.replace("_", " ").capitalize()
            self.tree.heading(col, text=label)
            self.tree.column(col, width=120, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame_tree.grid_rowconfigure(0, weight=1)
        frame_tree.grid_columnconfigure(0, weight=1)

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # --- Direita: Preview da mensagem ---
        frame_msg = tk.Frame(frame_principal)
        frame_principal.add(frame_msg, width=400, minsize=300)

        tk.Label(frame_msg, text="Mensagem", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)

        self.txt_mensagem = tk.Text(frame_msg, wrap=tk.WORD, font=("Segoe UI", 10), height=10)
        scroll_msg = ttk.Scrollbar(frame_msg, orient=tk.VERTICAL, command=self.txt_mensagem.yview)
        self.txt_mensagem.configure(yscrollcommand=scroll_msg.set)
        self.txt_mensagem.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll_msg.pack(fill=tk.Y, side=tk.RIGHT)

        self.lbl_cliente_msg = tk.Label(frame_msg, text="Clique em um cliente para ver a mensagem",
                                        font=("Segoe UI", 9), fg="gray")
        self.lbl_cliente_msg.pack(anchor=tk.W, pady=(5, 0))

        # === Controles de envio ===
        frame_controles = tk.Frame(self)
        frame_controles.pack(fill=tk.X, padx=15, pady=5)

        self.btn_conectar = tk.Button(frame_controles, text=" Conectar WhatsApp",
                                       font=("Segoe UI", 10), bg="#FF9800", fg="white",
                                       command=self._conectar_whatsapp)
        self.btn_conectar.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_enviar = tk.Button(frame_controles, text=" Enviar Selecionados",
                                     font=("Segoe UI", 10), bg="#f44336", fg="white",
                                     state=tk.DISABLED, command=self._iniciar_envio)
        self.btn_enviar.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_conexao = tk.Label(frame_controles, text="Desconectado", fg="red", font=("Segoe UI", 9))
        self.lbl_conexao.pack(side=tk.RIGHT)

        # === Progresso ===
        frame_progresso = tk.Frame(self)
        frame_progresso.pack(fill=tk.X, padx=15, pady=(0, 5))

        self.lbl_progresso = tk.Label(frame_progresso, text="", font=("Segoe UI", 9))
        self.lbl_progresso.pack(anchor=tk.W)

        self.progresso = ttk.Progressbar(frame_progresso, mode="determinate")
        self.progresso.pack(fill=tk.X, pady=(2, 0))

        # === Log ===
        frame_log = tk.Frame(self)
        frame_log.pack(fill=tk.BOTH, padx=15, pady=(0, 10))

        tk.Label(frame_log, text="Log", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_log = tk.Text(frame_log, wrap=tk.WORD, font=("Consolas", 9), height=7, bg="#1e1e1e", fg="#d4d4d4")
        scroll_log = ttk.Scrollbar(frame_log, orient=tk.VERTICAL, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=scroll_log.set)
        self.txt_log.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll_log.pack(fill=tk.Y, side=tk.RIGHT)

    def _configurar_log(self):
        handler = LogHandler(self.txt_log)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger("whatsapp_bot").addHandler(handler)
        logging.getLogger("whatsapp_bot").setLevel(logging.INFO)

    # ── Importação ──────────────────────────────

    def _importar_arquivo(self):
        caminho = tk.filedialog.askopenfilename(
            title="Selecionar arquivo de clientes",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xls *.xlsx"), ("Todos", "*.*")],
        )
        if not caminho:
            return

        try:
            clientes = ler_clientes(caminho)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler arquivo:\n{e}")
            return

        if not clientes:
            messagebox.showwarning("Aviso", "Nenhum cliente encontrado.")
            return

        erros = validar_clientes(clientes)
        if erros:
            msg = "Erros no arquivo:\n" + "\n".join(erros[:10])
            if len(erros) > 10:
                msg += f"\n... e mais {len(erros) - 10}"
            messagebox.showerror("Validação", msg)
            return

        self._carregar_clientes(clientes)
        logger.info(f"{len(clientes)} clientes importados de: {caminho}")

    def _importar_ocr(self):
        messagebox.showinfo(
            "Captura de Tela",
            "Posicione a planilha na tela.\n\n"
            "Após OK, clique e arraste para selecionar a região.\n"
            "ESC para cancelar."
        )

        for tentativa in range(1, 4):
            imagem = capturar_regiao()
            if imagem is None:
                return

            texto = ocr(imagem)
            if not texto.strip():
                messagebox.showwarning("OCR", "Nenhum texto encontrado. Tente novamente.")
                continue

            clientes = parsear_texto(texto)
            if not clientes:
                messagebox.showwarning("OCR", "Nenhum cliente identificado. Tente novamente.")
                continue

            editor = EditorTabela(clientes)
            resultado = editor.mostrar()
            if resultado is None:
                return
            if resultado == "reextrair":
                continue

            self._carregar_clientes(resultado)
            logger.info(f"{len(resultado)} clientes importados via OCR")
            return

        messagebox.showerror("Erro", "Falha após 3 tentativas de OCR.")

    def _carregar_clientes(self, clientes: list[dict]):
        self.clientes = clientes
        self.mensagens = {}
        self._cliente_atual_idx = None
        self._atualizar_tabela()
        self.lbl_status.config(text=f"{len(clientes)} cliente(s) carregados")
        self.btn_enviar.config(state=tk.NORMAL if self.sender else tk.DISABLED)
        self.txt_mensagem.delete("1.0", tk.END)
        self.lbl_cliente_msg.config(text="Clique em um cliente para ver a mensagem")

    def _atualizar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, c in enumerate(self.clientes):
            vals = ["☐"] + [c.get(f, "") for f in self.CAMPOS]
            self.tree.insert("", tk.END, iid=str(i), values=vals)

    # ── Interação com a tabela ──────────────────

    def _on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or col != "#0" and int(col.replace("#", "")) != 1:
            return
        vals = list(self.tree.item(item, "values"))
        vals[0] = "☑" if vals[0] == "☐" else "☐"
        self.tree.item(item, values=vals)

    def _on_tree_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._cliente_atual_idx = idx
        cliente = self.clientes[idx]
        self.lbl_cliente_msg.config(text=f"Cliente: {cliente['nome']} ({cliente.get('tipo_seguro', 'N/A')})")

        if idx not in self.mensagens:
            self.mensagens[idx] = gerar_mensagem(cliente)

        self.txt_mensagem.delete("1.0", tk.END)
        self.txt_mensagem.insert("1.0", self.mensagens[idx])

    def _marcar_todos(self):
        for item in self.tree.get_children():
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☑"
            self.tree.item(item, values=vals)

    def _desmarcar_todos(self):
        for item in self.tree.get_children():
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☐"
            self.tree.item(item, values=vals)

    def _obter_selecionados(self) -> list[int]:
        indices = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if vals and vals[0] == "☑":
                indices.append(int(item))
        return indices

    # ── WhatsApp ────────────────────────────────

    def _conectar_whatsapp(self):
        if self.sender:
            try:
                self.sender.fechar()
            except Exception:
                pass
            self.sender = None

        self.btn_conectar.config(state=tk.DISABLED, text=" Conectando...")
        self.lbl_conexao.config(text="Conectando...", fg="orange")
        self.update()

        def conectar():
            try:
                s = WhatsAppSender()
                s.conectar()
                self.sender = s
                self.after(0, self._conexao_ok)
            except Exception as e:
                self.after(0, self._conexao_erro, str(e))

        threading.Thread(target=conectar, daemon=True).start()

    def _conexao_ok(self):
        self.btn_conectar.config(state=tk.NORMAL, text=" Conectar WhatsApp")
        self.lbl_conexao.config(text="Conectado", fg="green")
        self.btn_enviar.config(state=tk.NORMAL if self.clientes else tk.DISABLED)
        logger.info("WhatsApp Web conectado!")

    def _conexao_erro(self, erro: str):
        self.btn_conectar.config(state=tk.NORMAL, text=" Conectar WhatsApp")
        self.lbl_conexao.config(text="Falha na conexão", fg="red")
        messagebox.showerror("WhatsApp", f"Falha ao conectar:\n{erro}")
        logger.error(f"Falha conexão WhatsApp: {erro}")

    def _iniciar_envio(self):
        if self._send_active:
            return

        indices = self._obter_selecionados()
        if not indices:
            messagebox.showwarning("Aviso", "Nenhum cliente selecionado.")
            return

        if not self.sender:
            messagebox.showwarning("Aviso", "Conecte ao WhatsApp primeiro.")
            return

        # Salva mensagens editadas
        if self._cliente_atual_idx is not None:
            msg = self.txt_mensagem.get("1.0", tk.END).strip()
            self.mensagens[self._cliente_atual_idx] = msg

        self._send_active = True
        self.btn_enviar.config(state=tk.DISABLED, text=" Enviando...")
        self.lbl_progresso.config(text=f"Enviando 0/{len(indices)}...")
        self.progresso["maximum"] = len(indices)
        self.progresso["value"] = 0

        logger.info(f"Iniciando envio para {len(indices)} cliente(s)...")

        def enviar():
            for pos, idx in enumerate(indices, start=1):
                if not self._send_active:
                    break
                cliente = self.clientes[idx]
                msg = self.mensagens.get(idx, gerar_mensagem(cliente))
                tel_raw = str(cliente.get("telefone", "")).strip()
                tel = tel_raw if tel_raw.startswith("55") else f"55{tel_raw}"

                logger.info(f"[{pos}/{len(indices)}] Enviando para {cliente['nome']}...")
                ok = self.sender.enviar_mensagem(tel, msg)

                self.after(0, self._atualizar_progresso, pos, len(indices), cliente["nome"], ok)

                if ok and pos < len(indices):
                    time.sleep(45)

            self.after(0, self._finalizar_envio)

        threading.Thread(target=enviar, daemon=True).start()

    def _atualizar_progresso(self, pos: int, total: int, nome: str, ok: bool):
        self.progresso["value"] = pos
        status = "✅" if ok else "❌"
        self.lbl_progresso.config(text=f"Enviando {pos}/{total} - {nome} {status}")

    def _finalizar_envio(self):
        self._send_active = False
        self.btn_enviar.config(state=tk.NORMAL, text=" Enviar Selecionados")
        logger.info("Envio concluído!")
        self.lbl_progresso.config(text="Envio concluído")
        messagebox.showinfo("Concluído", "Processo de envio finalizado!")

    # ── Fechamento ──────────────────────────────

    def _fechar(self):
        if self._send_active:
            if not messagebox.askyesno("Aviso", "Envio em andamento. Deseja realmente sair?"):
                return
            self._send_active = False

        if self.sender:
            try:
                self.sender.fechar()
            except Exception:
                pass
        self.destroy()
