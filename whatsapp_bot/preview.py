import tkinter as tk
from tkinter import scrolledtext


class PreviewWindow:
    def __init__(self, cliente: dict, mensagem: str, idx: int, total: int):
        self.resultado = None
        self.janela = tk.Tk()
        self.janela.title(f"Preview - Cliente {idx}/{total}")
        self.janela.geometry("600x520")
        self.janela.resizable(False, False)

        # Centraliza
        self.janela.update_idletasks()
        x = (self.janela.winfo_screenwidth() // 2) - 300
        y = (self.janela.winfo_screenheight() // 2) - 260
        self.janela.geometry(f"+{x}+{y}")

        self._montar_ui(cliente, mensagem, idx, total)
        self.janela.focus_force()
        self.janela.grab_set()

    def _montar_ui(self, cliente: dict, mensagem: str, idx: int, total: int):
        tk.Label(self.janela, text=f"📋 Cliente {idx}/{total}", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))

        frame_info = tk.Frame(self.janela, relief=tk.GROOVE, bd=1, padx=10, pady=5)
        frame_info.pack(fill=tk.X, padx=20, pady=5)

        for campo in ("nome", "telefone", "tipo_seguro", "vencimento", "valor"):
            val = cliente.get(campo, "")
            if val:
                tk.Label(frame_info, text=f"{campo.capitalize()}: {val}", anchor="w",
                         font=("Segoe UI", 10)).pack(fill=tk.X)

        tk.Label(self.janela, text="✉️ Mensagem a ser enviada:", font=("Segoe UI", 11, "bold")).pack(pady=(10, 5))

        self.txt_mensagem = scrolledtext.ScrolledText(
            self.janela, wrap=tk.WORD, width=65, height=10,
            font=("Segoe UI", 10)
        )
        self.txt_mensagem.insert(tk.END, mensagem)
        self.txt_mensagem.pack(padx=20, pady=(0, 10))

        frame_botoes = tk.Frame(self.janela)
        frame_botoes.pack(pady=10)

        btn_enviar = tk.Button(frame_botoes, text="✅ Enviar", width=14, height=2,
                               bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                               command=self._enviar)
        btn_enviar.pack(side=tk.LEFT, padx=5)

        btn_editar = tk.Button(frame_botoes, text="✏️ Editar", width=12, height=2,
                               bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"),
                               command=self._editar)
        btn_editar.pack(side=tk.LEFT, padx=5)

        btn_pular = tk.Button(frame_botoes, text="⏭️ Pular", width=12, height=2,
                              bg="#FF9800", fg="white", font=("Segoe UI", 10, "bold"),
                              command=self._pular)
        btn_pular.pack(side=tk.LEFT, padx=5)

        btn_sair = tk.Button(frame_botoes, text="❌ Sair", width=12, height=2,
                             bg="#f44336", fg="white", font=("Segoe UI", 10, "bold"),
                             command=self._sair)
        btn_sair.pack(side=tk.LEFT, padx=5)

        self.txt_mensagem.config(state=tk.DISABLED)

    def _enviar(self):
        self.resultado = "enviar"
        self.janela.destroy()

    def _editar(self):
        self.txt_mensagem.config(state=tk.NORMAL)
        self.janela.geometry("600x560")

        msg = self.txt_mensagem.get("1.0", tk.END).strip()

        def confirmar_edicao():
            self.resultado = ("editar", self.txt_mensagem.get("1.0", tk.END).strip())
            self.janela.destroy()

        tk.Button(self.janela, text="✅ Confirmar Edição", width=18, height=1,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                  command=confirmar_edicao).pack(pady=(0, 10))

    def _pular(self):
        self.resultado = "pular"
        self.janela.destroy()

    def _sair(self):
        self.resultado = "sair"
        self.janela.destroy()

    def mostrar(self):
        self.janela.mainloop()
        return self.resultado
