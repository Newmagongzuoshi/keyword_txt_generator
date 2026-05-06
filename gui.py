import tkinter as tk
from tkinter import ttk

from txt_generator_page import TxtGeneratorPage
from video_mover_page import VideoMoverPage


class App:
    def __init__(self, extractor):
        self.root = tk.Tk()
        self.root.title("关键词同名TXT生成工具")
        self.root.geometry("920x760")
        self.root.minsize(800, 600)

        self.extractor_ref = {"extractor": extractor}

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.txt_page = TxtGeneratorPage(self.notebook, self.extractor_ref)
        self.video_page = VideoMoverPage(self.notebook)

        self.notebook.add(self.txt_page, text="同名 TXT 生成")
        self.notebook.add(self.video_page, text="视频批量移动")

    def run(self):
        self.root.mainloop()
