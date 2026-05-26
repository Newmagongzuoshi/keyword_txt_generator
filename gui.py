import os
import sys
import tkinter as tk
from tkinter import ttk

from txt_generator_page import TxtGeneratorPage
from video_mover_page import VideoMoverPage


def _resource_path(relative_path):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


class App:
    def __init__(self, extractor):
        self.root = tk.Tk()
        self.root.title("关键词同名TXT生成工具 v1.2.0")
        self.root.geometry("920x760")
        self.root.minsize(800, 600)

        # 设置窗口图标
        icon_path = _resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.extractor_ref = {"extractor": extractor}

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.txt_page = TxtGeneratorPage(self.notebook, self.extractor_ref)
        self.video_page = VideoMoverPage(self.notebook)

        self.notebook.add(self.txt_page, text="同名 TXT 生成")
        self.notebook.add(self.video_page, text="视频批量移动")

    def run(self):
        self.root.mainloop()
