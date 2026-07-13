import os
import random
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext


class TopicGeneratorPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.source_folder = tk.StringVar()
        self.topic_count = tk.StringVar(value="5")
        self.required_position = tk.StringVar(value="后面")
        self.append_button = None
        self._setup_ui()
        self.source_folder.trace_add("write", self._on_source_folder_change)

    def _setup_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main, text="话题生成", font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=(0, 10))

        row_folder = ttk.Frame(main)
        row_folder.pack(fill=tk.X, pady=3)
        ttk.Label(row_folder, text="选择文件夹：", width=18).pack(side=tk.LEFT)
        ttk.Entry(row_folder, textvariable=self.source_folder).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row_folder, text="选择文件夹", command=self._select_folder).pack(side=tk.LEFT)

        row_count = ttk.Frame(main)
        row_count.pack(fill=tk.X, pady=3)
        ttk.Label(row_count, text="话题总数量：", width=18).pack(side=tk.LEFT)
        ttk.Combobox(row_count, textvariable=self.topic_count,
                     values=[str(i) for i in range(1, 6)], state="readonly", width=6).pack(side=tk.LEFT)
        ttk.Label(row_count, text="最多 5 个，默认 5 个", foreground="gray").pack(side=tk.LEFT, padx=10)

        row_position = ttk.Frame(main)
        row_position.pack(fill=tk.X, pady=3)
        ttk.Label(row_position, text="必选话题位置：", width=18).pack(side=tk.LEFT)
        ttk.Combobox(row_position, textvariable=self.required_position,
                     values=["前面", "中间", "后面", "随机"], state="readonly", width=10).pack(side=tk.LEFT)
        ttk.Label(row_position, text="必选话题在最终文本中的位置", foreground="gray").pack(side=tk.LEFT, padx=10)

        row_topics = ttk.Frame(main)
        row_topics.pack(fill=tk.X, pady=3)
        ttk.Label(row_topics, text="话题列表\n（每行一个）：", width=18).pack(side=tk.LEFT, anchor=tk.N)
        self.topics_text = scrolledtext.ScrolledText(row_topics, height=6, width=40,
                                                    highlightbackground="#4A90E2",
                                                    highlightcolor="#4A90E2",
                                                    highlightthickness=2)
        self.topics_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(row_topics, text="每行填写一个话题，用于随机选择。", foreground="gray").pack(side=tk.LEFT)

        row_required = ttk.Frame(main)
        row_required.pack(fill=tk.X, pady=3)
        ttk.Label(row_required, text="必选话题\n（每行一个）：", width=18).pack(side=tk.LEFT, anchor=tk.N)
        self.required_topics_text = scrolledtext.ScrolledText(row_required, height=6, width=40,
                                                              highlightbackground="#E74C3C",
                                                              highlightcolor="#E74C3C",
                                                              highlightthickness=2)
        self.required_topics_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(row_required, text="默认追加在最后面，可设置位置。", foreground="gray").pack(side=tk.LEFT)

        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=10)
        self.append_button = ttk.Button(btn_row, text="开始追加话题", command=self._execute_append)
        self.append_button.pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="撤回上次追加", command=self._undo_last_append).pack(side=tk.LEFT, padx=3)

        log_frame = ttk.LabelFrame(main, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=12, width=80, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _select_folder(self):
        folder = filedialog.askdirectory(title="选择包含 TXT 的文件夹")
        if folder:
            self.source_folder.set(folder)

    def _on_source_folder_change(self, *args):
        self._update_append_button_state()

    def _update_append_button_state(self):
        if self.append_button is None:
            return
        folder = self.source_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            self.append_button.config(state=tk.DISABLED)
            return
        history_path = Path(folder) / ".topic_append_history.json"
        if history_path.exists():
            self.append_button.config(state=tk.DISABLED)
        else:
            self.append_button.config(state=tk.NORMAL)

    def _log(self, msg):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _get_topic_count(self):
        try:
            count = int(self.topic_count.get())
        except ValueError:
            count = 5
        return max(1, min(5, count))

    def _load_lines(self, widget):
        return [line.strip() for line in widget.get("1.0", tk.END).splitlines() if line.strip()]

    def _format_topic(self, topic):
        return f"#{topic}"

    def _detect_encoding(self, path):
        for encoding in ["utf-8-sig", "utf-8", "gb18030", "gbk"]:
            try:
                with open(path, "r", encoding=encoding) as f:
                    f.read()
                return encoding
            except Exception:
                continue
        return "utf-8"

    def _append_line_to_file(self, path, line):
        encoding = self._detect_encoding(path)
        with open(path, "a", encoding=encoding, errors="ignore") as f:
            f.write(line)

    def _ends_with_newline(self, path, encoding):
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                if f.tell() == 0:
                    return True
                f.seek(-1, os.SEEK_END)
                return f.read(1) == b"\n"
        except Exception:
            pass
        return True

    def _collect_txt_files(self, folder):
        return [p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() == ".txt"]

    def _write_undo_log(self, folder, append_text, files):
        import json
        history_path = Path(folder) / ".topic_append_history.json"
        entry = {
            "append": append_text,
            "files": [str(p.name) for p in files],
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        try:
            history = []
            if history_path.exists():
                try:
                    with open(history_path, "r", encoding="utf-8") as hf:
                        history = json.load(hf) or []
                except Exception:
                    history = []

            history.append(entry)
            with open(history_path, "w", encoding="utf-8") as lf:
                json.dump(history, lf, ensure_ascii=False, indent=2)
            # try to hide on Windows
            if os.name == "nt":
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(str(history_path), FILE_ATTRIBUTE_HIDDEN)
                except Exception:
                    pass
        except Exception:
            pass

    def _undo_last_append(self):
        import json
        folder = self.source_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("提示", "请先选择包含 TXT 的有效文件夹。")
            return
        history_path = Path(folder) / ".topic_append_history.json"
        if not history_path.exists():
            messagebox.showinfo("提示", "未找到可撤回的追加记录。")
            return
        try:
            with open(history_path, "r", encoding="utf-8") as lf:
                history = json.load(lf) or []
        except Exception as e:
            messagebox.showwarning("提示", f"读取撤回日志失败：{e}")
            return

        if not history:
            messagebox.showinfo("提示", "撤回日志为空。")
            try:
                history_path.unlink()
            except Exception:
                pass
            return

        # pop last entry (most recent)
        entry = history.pop()
        append_text = entry.get("append", "")
        files = entry.get("files", [])
        success = 0
        for fname in files:
            p = Path(folder) / fname
            if not p.exists():
                self._log(f"撤回失败（文件不存在）：{fname}")
                continue
            try:
                enc = self._detect_encoding(p)
                with open(p, "r", encoding=enc, errors="ignore") as f:
                    content = f.read()
                if content.endswith(append_text):
                    new_content = content[: -len(append_text)]
                    with open(p, "w", encoding=enc, errors="ignore") as f:
                        f.write(new_content)
                    self._log(f"已撤回：{fname}")
                    success += 1
                else:
                    self._log(f"未撤回（末尾不匹配）：{fname}")
            except Exception as e:
                self._log(f"撤回失败：{fname}，原因：{e}")

        # write back remaining history or delete file
        try:
            if history:
                with open(history_path, "w", encoding="utf-8") as lf:
                    json.dump(history, lf, ensure_ascii=False, indent=2)
            else:
                history_path.unlink()
        except Exception:
            pass

        self._update_append_button_state()
        messagebox.showinfo("撤回完成", f"已撤回 {success}/{len(files)} 个文件。")

    def _prepare_topic_list(self, topics, required, count):
        if len(required) > count:
            raise ValueError("必选话题数量不能超过总话题数量。")

        normal_needed = count - len(required)
        selected_normal = []
        if normal_needed > 0:
            if len(topics) < normal_needed:
                raise ValueError(f"普通话题数量不足，至少需要 {normal_needed} 个。")
            selected_normal = random.sample(topics, normal_needed)

        if self.required_position.get() == "前面":
            final = required + selected_normal
        elif self.required_position.get() == "中间":
            mid = len(selected_normal) // 2
            final = selected_normal[:mid] + required + selected_normal[mid:]
        elif self.required_position.get() == "随机":
            final = selected_normal[:]
            for topic in required:
                insert_at = random.randint(0, len(final))
                final.insert(insert_at, topic)
        else:
            final = selected_normal + required

        return [self._format_topic(t) for t in final]

    def _execute_append(self):
        folder = self.source_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("提示", "请先选择包含 TXT 的有效文件夹。")
            return

        topics = self._load_lines(self.topics_text)
        required_topics = self._load_lines(self.required_topics_text)
        count = self._get_topic_count()

        if not topics and not required_topics:
            messagebox.showwarning("提示", "请先填写话题或必选话题。")
            return

        try:
            formatted_topics = self._prepare_topic_list(topics, required_topics, count)
        except ValueError as e:
            messagebox.showwarning("提示", str(e))
            return

        txt_files = self._collect_txt_files(folder)
        if not txt_files:
            messagebox.showwarning("提示", "文件夹中未找到任何 TXT 文件。")
            return

        # build single-line append text: leading space before first topic, ensure single spaces between topics and trailing space
        append_line = " " + " ".join(formatted_topics) + " "
        if not append_line.strip():
            messagebox.showwarning("提示", "生成的追加内容为空。")
            return

        self._log(f"开始追加话题到 {len(txt_files)} 个 TXT 文件，数量：{count}。")
        success_count = 0
        success_files = []
        for file_path in txt_files:
            try:
                self._append_line_to_file(file_path, append_line)
                self._log(f"已追加：{file_path.name}")
                success_count += 1
                success_files.append(file_path)
            except Exception as exc:
                self._log(f"追加失败：{file_path.name}，原因：{exc}")

        self._log(f"完成：{success_count}/{len(txt_files)} 个文件已追加话题。")
        # write undo log only for successfully modified files
        if success_files:
            try:
                self._write_undo_log(folder, append_line, success_files)
                self._log("已在目标文件夹中写入隐藏撤回日志。")
            except Exception:
                self._log("写入撤回日志失败。")

        self._update_append_button_state()
        messagebox.showinfo("完成", f"已向 {success_count} 个 TXT 文件追加话题。")
