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


def set_app_icon(window, icon_rel_path="assets/app.ico"):
    """同时设置窗口左上角图标和任务栏图标。
    参数 icon_rel_path 为相对于项目根目录的 .ico 文件路径。
    Windows 上 iconbitmap() 同时设置窗口图标和任务栏图标。
    iconphoto() 作为备用方案（跨平台兼容）。
    """
    ico = _resource_path(icon_rel_path)
    if not os.path.exists(ico):
        print("WARNING: icon not found: %s" % ico)
        return

    # 主方案：Windows 上设置窗口图标 + 任务栏图标
    window.tk.call("wm", "iconbitmap", window._w, ico)

    # 备用方案：iconphoto 兼容部分 Linux 桌面
    try:
        photo = tk.PhotoImage(file=ico)
        window.iconphoto(True, photo)
        window._icon_photo = photo  # 保持引用防止被 GC
    except Exception:
        pass  # .ico 不能被 PhotoImage 直接读取时忽略


class App:
    def __init__(self, extractor):
        self.root = tk.Tk()
        self.root.title("关键词同名TXT生成工具 v1.2.0")
        self.root.geometry("920x760")
        self.root.minsize(800, 600)

        # 设置应用图标（窗口左上角 + 任务栏）
        set_app_icon(self.root)

        self.extractor_ref = {"extractor": extractor}

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.txt_page = TxtGeneratorPage(self.notebook, self.extractor_ref)
        self.video_page = VideoMoverPage(self.notebook)

        self.notebook.add(self.txt_page, text="同名 TXT 生成")
        self.notebook.add(self.video_page, text="视频批量移动")

    def run(self):
        self.root.mainloop()
