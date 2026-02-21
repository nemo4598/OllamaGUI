import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import json
import time
from threading import Thread

BUFFER_DURATION = 30      
SMOOTH_DELAY = 0.02       

class ModernChat:
    def __init__(self, root):
        self.root = root
        root.title("ModernChat GUI")
        root.geometry("800x600")
        root.configure(bg="#1e1e1e")
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self.api_url = "http://127.0.0.1:11434"
        self.chat_history = []

        self.create_header()
        self.create_chat_area()
        self.create_input_area()
        self.create_progressbar()

        self.models = []
        self.update_models_list()

    def create_header(self):
        frame = tk.Frame(self.root, bg="#1e1e1e")
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        frame.grid_columnconfigure(2, weight=1)

        tk.Label(frame, text="Host URL:", fg="white", bg="#1e1e1e").grid(row=0, column=0, padx=(0,5))
        self.api_url_var = tk.StringVar(value=self.api_url)
        tk.Entry(frame, textvariable=self.api_url_var, width=30).grid(row=0, column=1, padx=(0,10))
        self.model_var = tk.StringVar()
        self.model_menu = ttk.Combobox(frame, textvariable=self.model_var, state="readonly")
        self.model_menu.grid(row=0, column=2, sticky="ew")
        ttk.Button(frame, text="Refresh Models", command=self.update_models_list).grid(row=0,column=3,padx=5)

    def create_chat_area(self):
        frame = tk.Frame(self.root, bg="#1e1e1e")
        frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(frame, bg="#1e1e1e", highlightthickness=0)
        self.chat_canvas.grid(row=0,column=0,sticky="nsew")
        self.scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.chat_canvas.yview)
        self.scrollbar.grid(row=0,column=1,sticky="ns")
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.chat_frame = tk.Frame(self.chat_canvas, bg="#1e1e1e")
        self.chat_canvas.create_window((0,0), window=self.chat_frame, anchor="nw")
        self.chat_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))

    def create_input_area(self):
        frame = tk.Frame(self.root, bg="#1e1e1e")
        frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        frame.grid_columnconfigure(0, weight=1)

        self.input_text = tk.Text(frame, height=4, bg="#2e2e2e", fg="white", insertbackground="white")
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.input_text.bind("<Return>", self.on_enter)

        self.send_button = ttk.Button(frame, text="Send", command=self.on_send)
        self.send_button.grid(row=0,column=1)

    def create_progressbar(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Blue.Horizontal.TProgressbar", foreground="#48a4f2", background="#48a4f2")
        self.typing_progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", style="Blue.Horizontal.TProgressbar")
        self.typing_progress.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))
        self.typing_progress["maximum"] = 100
        self.typing_progress["value"] = 0

    def add_bubble(self, text, is_user=True):
        bg = "#0d6efd" if is_user else "#3a3a3a"
        fg = "white"
        bubble = tk.Label(self.chat_frame, text=text, bg=bg, fg=fg, wraplength=500, justify="left",
                          padx=10, pady=6, anchor="w")
        bubble.pack(anchor="e" if is_user else "w", pady=2, padx=5, ipadx=5, ipady=5)
        bubble.configure(borderwidth=0, relief="ridge", highlightbackground=bg, highlightthickness=1)
        
        bubble.bind("<Button-3>", lambda e, b=bubble: self.copy_bubble(b))
        return bubble

    def copy_bubble(self, bubble):
        self.root.clipboard_clear()
        self.root.clipboard_append(bubble.cget("text"))
        messagebox.showinfo("Copied", "Text copied to clipboard!")

    def on_enter(self, event):
        self.on_send()
        return "break"

    def on_send(self):
        msg = self.input_text.get("1.0","end-1c").strip()
        if not msg: return
        self.input_text.delete("1.0","end")
        self.add_bubble(msg, True)
        self.chat_history.append({"role":"user","content":msg})
        Thread(target=self.generate_response_buffered, daemon=True).start()

    def generate_response_buffered(self):
        self.api_url = self.api_url_var.get()
        model_name = self.model_var.get()
        buffer = ""

        
        try:
            req = urllib.request.Request(
                urllib.parse.urljoin(self.api_url,"/api/chat"),
                data=json.dumps({"model":model_name,"messages":self.chat_history,"stream":True}).encode("utf-8"),
                headers={"Content-Type":"application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                for line in resp:
                    data = json.loads(line.decode("utf-8"))
                    if "message" in data:
                        buffer += data["message"]["content"]
        except Exception as e:
            buffer = f"Error: {e}"

        self.chat_history.append({"role":"assistant","content":buffer})
        bubble = self.add_bubble("", False)

        def loading_timer():
            steps = int(BUFFER_DURATION/0.05)
            for i in range(steps):
                self.typing_progress["value"] = (i+1)/steps*100
                self.root.update_idletasks()
                time.sleep(0.05)
            self.smooth_write(bubble, buffer)

        Thread(target=loading_timer, daemon=True).start()

    def smooth_write(self, bubble, text):
        self.typing_progress["maximum"] = len(text)
        self.typing_progress["value"] = 0
        for i, ch in enumerate(text):
            self.root.after(int(i*SMOOTH_DELAY*1000), lambda c=ch, idx=i: self.update_bubble(bubble, text[:idx+1]))

    def update_bubble(self, bubble, text):
        bubble.config(text=text)
        self.chat_canvas.yview_moveto(1.0)

    def update_models_list(self):
        self.models = []
        try:
            url = urllib.parse.urljoin(self.api_url_var.get(), "/api/tags")
            with urllib.request.urlopen(url) as resp:
                data = json.load(resp)
                self.models = [m["name"] for m in data.get("models",[])]
        except Exception:
            pass
        self.model_menu["values"] = self.models
        if self.models: self.model_var.set(self.models[0])

def main():
    root = tk.Tk()
    app = ModernChat(root)
    root.mainloop()

if __name__ == "__main__":
    main()
