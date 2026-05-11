import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

from video_mover import (
    build_move_preview,
    build_rename_only_preview,
    execute_tasks,
)


class VideoMoverPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.root_folder = tk.StringVar()
        self.remove_text = tk.StringVar()
        self.folder_prefix = tk.StringVar(value="_文件夹")
        self.start_number = tk.StringVar(value="1")
        self.example_text = tk.StringVar(value="示例：_文件夹1")
        self.current_mode = None
        self.preview_tasks = []
        self._setup_ui()
        self._bind_suffix_trace()

    def _setup_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main, text="视频批量移动",
                          font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=(0, 10))

        row1 = ttk.Frame(main)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text="总文件夹：", width=18).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.root_folder).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row1, text="选择文件夹", command=self._select_folder).pack(side=tk.LEFT)

        row2 = ttk.Frame(main)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text="删除文件名中的指定内容：").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.remove_text, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="例如：_副本", foreground="gray").pack(side=tk.LEFT)

        row3 = ttk.Frame(main)
        row3.pack(fill=tk.X, pady=3)
        ttk.Label(row3, text="文件夹后缀：", width=18).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.folder_prefix, width=10).pack(side=tk.LEFT)
        ttk.Label(row3, text=" 起始编号：").pack(side=tk.LEFT)
        vcmd = (self.register(self._validate_start_number), "%P")
        ttk.Entry(row3, textvariable=self.start_number, width=6, validate="key",
                  validatecommand=vcmd).pack(side=tk.LEFT)
        ttk.Label(row3, textvariable=self.example_text, foreground="gray").pack(side=tk.LEFT, padx=5)

        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=10)
        ttk.Button(btn_row, text="生成移动预览", command=self._build_move_preview).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_row, text="预览：只删除文件名指定内容",
                  command=self._build_rename_preview,
                  fg="red", bg="black", relief="groove",
                  font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="确认执行当前预览",
                   command=self._confirm_execute).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="清空预览",
                   command=self._clear_preview).pack(side=tk.LEFT, padx=3)

        columns = ("操作", "来源文件夹序号", "文件夹标识", "原文件", "目标文件")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", height=12)
        self.tree.heading("操作", text="操作")
        self.tree.heading("来源文件夹序号", text="来源文件夹序号")
        self.tree.heading("文件夹标识", text="文件夹标识")
        self.tree.heading("原文件", text="原文件")
        self.tree.heading("目标文件", text="目标文件")
        self.tree.column("操作", width=100)
        self.tree.column("来源文件夹序号", width=100)
        self.tree.column("文件夹标识", width=80)
        self.tree.column("原文件", width=300)
        self.tree.column("目标文件", width=300)
        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        log_frame = ttk.LabelFrame(main, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, width=80, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _select_folder(self):
        folder = filedialog.askdirectory(title="选择总文件夹")
        if folder:
            self.root_folder.set(folder)

    def _bind_suffix_trace(self):
        def on_change(*_):
            self._update_example()
        self.folder_prefix.trace_add("write", on_change)
        self.start_number.trace_add("write", on_change)

    def _update_example(self):
        prefix = self.folder_prefix.get().strip() or "_文件夹"
        try:
            num = int(self.start_number.get())
        except ValueError:
            num = 1
        self.example_text.set(f"示例：{prefix}{num}")

    def _validate_start_number(self, value):
        if value == "":
            return True
        return value.isdigit() and int(value) > 0

    def _get_start_number(self):
        try:
            return int(self.start_number.get())
        except ValueError:
            return 1

    def _log(self, msg):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _populate_tree(self, tasks):
        self._clear_tree()
        root = self.root_folder.get()
        for task in tasks:
            try:
                source_rel = str(task["source"].relative_to(root))
            except ValueError:
                source_rel = str(task["source"])
            try:
                target_rel = str(task["target"].relative_to(root))
            except ValueError:
                target_rel = str(task["target"])

            folder_index = str(task.get("folder_index", ""))
            folder_suffix = task.get("folder_suffix", "")

            self.tree.insert("", tk.END, values=(
                task["operation"],
                folder_index,
                folder_suffix,
                source_rel,
                target_rel,
            ))

    def _build_move_preview(self):
        root_dir = self.root_folder.get().strip()
        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showwarning("提示", "请先选择有效的总文件夹")
            return

        remove_text = self.remove_text.get().strip()
        folder_prefix = self.folder_prefix.get().strip() or "_文件夹"
        start_number = self._get_start_number()
        self._log("正在扫描子文件夹并生成移动预览...")

        try:
            tasks = build_move_preview(root_dir, remove_text, folder_prefix, start_number)
        except Exception as e:
            self._log(f"生成预览失败：{e}")
            return

        if not tasks:
            self._log("未找到任何视频文件。")
            messagebox.showinfo("提示", "未找到任何视频文件。")
            return

        self.preview_tasks = tasks
        self.current_mode = "move"
        self._populate_tree(tasks)

        folders = {}
        for t in tasks:
            fi = t.get("folder_index", 0)
            fs = t.get("folder_suffix", "")
            if fi not in folders:
                folders[fi] = (t["source_folder"], fs)
        self._log("子文件夹排序完成：")
        for fi in sorted(folders.keys()):
            sf_name, sf_suffix = folders[fi]
            self._log(f"第 {fi} 个：{sf_name}，文件夹标识：{sf_suffix}")

        for t in tasks:
            self._log(f"预览：{t['source'].name} -> {t['target'].name}")

        self._log(f"移动预览生成完成，共 {len(tasks)} 个视频。")

    def _build_rename_preview(self):
        root_dir = self.root_folder.get().strip()
        remove_text = self.remove_text.get().strip()

        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showwarning("提示", "请先选择有效的总文件夹")
            return
        if not remove_text:
            messagebox.showwarning("提示", "请先填写要删除的文件名内容")
            return

        self._log("正在扫描视频并生成仅重命名预览...")

        try:
            tasks = build_rename_only_preview(root_dir, remove_text)
        except Exception as e:
            self._log(f"生成预览失败：{e}")
            return

        if not tasks:
            self._log("没有找到需要重命名的视频文件。")
            messagebox.showinfo("提示", "没有找到需要重命名的视频文件。")
            return

        self.preview_tasks = tasks
        self.current_mode = "rename"
        self._populate_tree(tasks)

        for t in tasks:
            self._log(f"预览：{t['source'].name} -> {t['target'].name}")

        self._log(f"删除指定内容预览生成完成，共 {len(tasks)} 个视频。")

    def _confirm_execute(self):
        if not self.preview_tasks:
            messagebox.showinfo("提示", "请先生成预览。")
            return

        count = len(self.preview_tasks)

        if self.current_mode == "move":
            msg = (
                f"即将移动并重命名 {count} 个视频。\n\n"
                f"视频会从子文件夹移动到总文件夹。\n\n"
                f"是否确认执行？"
            )
        else:
            msg = (
                f"即将重命名 {count} 个视频。\n\n"
                f"此操作只会删除文件名中的指定内容，不会移动文件。\n\n"
                f"是否确认执行？"
            )

        if not messagebox.askyesno("确认执行", msg):
            self._log("用户取消执行。")
            return

        self._log("正在执行...")

        def run():
            try:
                result = execute_tasks(self.preview_tasks)
                for log_entry in result["logs"]:
                    if log_entry["success"]:
                        self.after(0, lambda m=log_entry["message"]: self._log(m))
                    else:
                        self.after(0, lambda m=log_entry["message"]: self._log(m))
                        self.after(0, lambda r=log_entry.get("reason", ""): self._log(f"原因：{r}"))
                summary = (
                    f"执行完成\n"
                    f"成功数量：{result['success_count']}\n"
                    f"失败数量：{result['fail_count']}\n"
                    f"总数：{result['total']}"
                )
                self.after(0, lambda: self._log(""))
                self.after(0, lambda s=summary: self._log(s))
                self.after(0, lambda: messagebox.showinfo(
                    "完成",
                    f"执行完成\n\n成功：{result['success_count']}\n失败：{result['fail_count']}"
                ))
                self.after(0, self._clear_preview)
            except Exception as e:
                self.after(0, lambda: self._log(f"执行异常：{e}"))

        threading.Thread(target=run, daemon=True).start()

    def _clear_preview(self):
        self.preview_tasks = []
        self.current_mode = None
        self._clear_tree()
        self._log("预览已清空。")
