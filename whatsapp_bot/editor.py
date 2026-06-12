import tkinter as tk
from tkinter import ttk, messagebox


class EditorTabela:
    CAMPOS = ["nome", "telefone", "tipo_seguro", "vencimento", "valor"]

    def __init__(self, clientes: list[dict]):
        self.clientes = clientes
        self.resultado = None

        self.janela = tk.Tk()
        self.janela.title("Revisar dados extraídos - OCR")
        self.janela.geometry("850x500")
        self.janela.resizable(True, True)

        self.janela.update_idletasks()
        x = (self.janela.winfo_screenwidth() // 2) - 425
        y = (self.janela.winfo_screenheight() // 2) - 250
        self.janela.geometry(f"+{x}+{y}")

        self._montar_ui()

    def _montar_ui(self):
        frame_top = tk.Frame(self.janela)
        frame_top.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(frame_top, text="Dados extraídos via OCR",
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(frame_top, text="Edite os campos se necessário",
                 font=("Segoe UI", 9), fg="gray").pack(side=tk.RIGHT)

        frame_tree = tk.Frame(self.janela)
        frame_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = self.CAMPOS
        self.tree = ttk.Treeview(frame_tree, columns=cols, show="headings", selectmode="browse")

        scroll_y = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame_tree, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scroll_y.set, xscroll=scroll_x.set)

        for col in cols:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=150, minwidth=80, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame_tree.grid_rowconfigure(0, weight=1)
        frame_tree.grid_columnconfigure(0, weight=1)

        # Eventos de edição
        self.tree.bind("<Double-1>", self._editar_celula)
        self.tree.bind("<Return>", lambda e: self._editar_celula(None))

        self._popular_tree()

        frame_botoes = tk.Frame(self.janela)
        frame_botoes.pack(pady=10)

        tk.Button(frame_botoes, text="✅ Confirmar", width=14, height=2,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                  command=self._confirmar).pack(side=tk.LEFT, padx=5)

        tk.Button(frame_botoes, text="🔄 Re-extrair", width=14, height=2,
                  bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"),
                  command=self._reextrair).pack(side=tk.LEFT, padx=5)

        tk.Button(frame_botoes, text="❌ Cancelar", width=14, height=2,
                  bg="#f44336", fg="white", font=("Segoe UI", 10, "bold"),
                  command=self._cancelar).pack(side=tk.LEFT, padx=5)

    def _popular_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for c in self.clientes:
            vals = [c.get(f, "") for f in self.CAMPOS]
            self.tree.insert("", tk.END, values=vals)

    def _editar_celula(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        col_idx = self.tree.identify_column(_event.x if _event else 1)
        if not col_idx:
            return
        col = int(col_idx.replace("#", "")) - 1
        if col < 0 or col >= len(self.CAMPOS):
            return

        campo = self.CAMPOS[col]
        valor_atual = self.tree.item(item, "values")[col]

        # Cria entry sobre a célula
        x, y, w, h = self.tree.bbox(item, column=col_idx)
        entry = tk.Entry(self.tree, font=("Segoe UI", 10))
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, valor_atual)
        entry.select_range(0, tk.END)
        entry.focus()

        def finalizar(ev=None):
            novo_valor = entry.get()
            entry.destroy()
            vals = list(self.tree.item(item, "values"))
            vals[col] = novo_valor
            self.tree.item(item, values=vals)
            idx = self.tree.index(item)
            self.clientes[idx][campo] = novo_valor

        entry.bind("<Return>", finalizar)
        entry.bind("<Escape>", lambda e: entry.destroy())
        entry.bind("<FocusOut>", finalizar)

    def _adicionar_linha(self):
        self.clientes.append({"nome": "", "telefone": "", "tipo_seguro": "",
                              "vencimento": "", "valor": ""})
        self._popular_tree()

    def _confirmar(self):
        # Remove linhas sem telefone
        self.clientes = [c for c in self.clientes if c.get("telefone", "").strip()]
        if not self.clientes:
            messagebox.showwarning("Aviso", "Nenhum cliente com telefone válido.")
            return
        self.resultado = self.clientes
        self.janela.destroy()

    def _reextrair(self):
        self.resultado = "reextrair"
        self.janela.destroy()

    def _cancelar(self):
        self.resultado = None
        self.janela.destroy()

    def mostrar(self):
        self.janela.mainloop()
        return self.resultado
