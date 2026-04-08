# widgets.py
# Paylaşılan UI bileşenleri — log paneli, ilerleme çubuğu, durum çubuğu.

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    """Kaydırılabilir log mesaj paneli."""

    def __init__(self, master, height=200, **kwargs):
        super().__init__(master, **kwargs)

        self.label = ctk.CTkLabel(self, text="📋 İşlem Günlüğü", anchor="w",
                                  font=ctk.CTkFont(size=13, weight="bold"))
        self.label.pack(fill="x", padx=8, pady=(4, 0))

        self.textbox = ctk.CTkTextbox(self, height=height, font=ctk.CTkFont(family="Consolas", size=12),
                                      state="disabled", wrap="word")
        self.textbox.pack(fill="both", expand=True, padx=4, pady=4)

    def log(self, message):
        """Mesaj ekle ve en alta kaydır."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class ProgressFrame(ctk.CTkFrame):
    """İlerleme çubuğu + yüzde etiketi."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.progress_bar = ctk.CTkProgressBar(self, height=16)
        self.progress_bar.pack(fill="x", padx=8, pady=(4, 2))
        self.progress_bar.set(0)

        self.label = ctk.CTkLabel(self, text="Hazır", anchor="w",
                                  font=ctk.CTkFont(size=12))
        self.label.pack(fill="x", padx=8, pady=(0, 4))

    def update_progress(self, current, total, text=""):
        ratio = current / max(total, 1)
        self.progress_bar.set(ratio)
        pct = int(ratio * 100)
        self.label.configure(text=f"%{pct} — {text}")

    def reset(self, text="Hazır"):
        self.progress_bar.set(0)
        self.label.configure(text=text)


class StatusBar(ctk.CTkFrame):
    """Alt durum çubuğu."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=28, **kwargs)
        from config_manager import VERSION, APP_NAME

        self.label = ctk.CTkLabel(self, text=f"{APP_NAME} v{VERSION} — Hazır",
                                  font=ctk.CTkFont(size=11), anchor="w")
        self.label.pack(fill="x", padx=10, pady=2)

    def set_text(self, text):
        self.label.configure(text=text)

