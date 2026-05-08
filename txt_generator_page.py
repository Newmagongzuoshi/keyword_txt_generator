import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

from config import LEVEL_ORDER


class TxtGeneratorPage(ttk.Frame):
    def __init__(self, parent, extractor_ref):
        super().__init__(parent)
        self.extractor_ref = extractor_ref
        self.mp4_folder = tk.StringVar()
        self.keyword_file = tk.StringVar()
        self.required_keyword_file = tk.StringVar()
        self.required_keyword_order = tk.StringVar(value="随机")
        self.keywords_text = tk.StringVar()  # 新增关键词编辑框变量
        self.target_length = tk.StringVar(value="500")
        self.extract_mode = tk.StringVar(value="优先提取")
        self.target_level = tk.StringVar(value="区县级")
        self.smart_mode = tk.BooleanVar(value=True)  # 智能模式默认启用
        self._building = False
        self._setup_ui()
        # 初始化智能模式状态
        self._on_smart_mode_toggle()

    def _setup_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main, text="关键词同名 TXT 生成工具",
                          font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=(0, 10))

        row1 = ttk.Frame(main)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text="MP4 文件夹：", width=14).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.mp4_folder).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row1, text="选择文件夹", command=self._select_mp4_folder).pack(side=tk.LEFT)

        row2 = ttk.Frame(main)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text="关键词 TXT：", width=14).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.keyword_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row2, text="选择 TXT", command=self._select_keyword_file).pack(side=tk.LEFT)

        row_req_file = ttk.Frame(main)
        row_req_file.pack(fill=tk.X, pady=3)
        ttk.Label(row_req_file, text="必选关键词 TXT：", width=14).pack(side=tk.LEFT)
        ttk.Entry(row_req_file, textvariable=self.required_keyword_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row_req_file, text="选择 TXT", command=self._select_required_keyword_file).pack(side=tk.LEFT)

        row_req_order = ttk.Frame(main)
        row_req_order.pack(fill=tk.X, pady=3)
        ttk.Label(row_req_order, text="必选关键词顺序：", width=14).pack(side=tk.LEFT)
        ttk.Combobox(row_req_order, textvariable=self.required_keyword_order,
                     values=["随机", "顺序"], state="readonly", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(row_req_order, text="写入必选关键词时的顺序", foreground="gray").pack(side=tk.LEFT)

        row3 = ttk.Frame(main)
        row3.pack(fill=tk.X, pady=3)
        ttk.Label(row3, text="目标文本长度：", width=14).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.target_length, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row3, text="每条文案会在目标长度基础上随机浮动 2%~15%",
                  foreground="gray").pack(side=tk.LEFT)

        row4 = ttk.Frame(main)
        row4.pack(fill=tk.X, pady=3)
        ttk.Label(row4, text="提取模式：", width=14).pack(side=tk.LEFT)
        cb_mode = ttk.Combobox(row4, textvariable=self.extract_mode,
                               values=["优先提取", "强制提取"], state="readonly", width=12)
        cb_mode.pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(row4, text="智能模式", variable=self.smart_mode,
                        command=self._on_smart_mode_toggle).pack(side=tk.LEFT, padx=(20, 5))
        ttk.Label(row4, text="目标层级：").pack(side=tk.LEFT, padx=(10, 5))
        self.cb_level = ttk.Combobox(row4, textvariable=self.target_level,
                                     values=LEVEL_ORDER, state="readonly", width=12)
        self.cb_level.pack(side=tk.LEFT)

        # 关键词编辑框 - 蓝色边框
        row_keywords = ttk.Frame(main)
        row_keywords.pack(fill=tk.X, pady=3)
        ttk.Label(row_keywords, text="关键词\n（每行一个）：", width=14).pack(side=tk.LEFT, anchor=tk.N)
        self.keywords_text = scrolledtext.ScrolledText(row_keywords, height=4, width=40,
                                                       highlightbackground="#4A90E2", highlightcolor="#4A90E2",
                                                       highlightthickness=2)
        self.keywords_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(row_keywords, text="可不填，可从TXT导入或在此编辑",
                  foreground="gray").pack(side=tk.LEFT)

        # 必选关键词编辑框 - 红色边框
        row5 = ttk.Frame(main)
        row5.pack(fill=tk.X, pady=3)
        ttk.Label(row5, text="必选关键词\n（每行一个）：", width=14).pack(side=tk.LEFT, anchor=tk.N)
        self.required_keywords_text = scrolledtext.ScrolledText(row5, height=4, width=40,
                                                                highlightbackground="#E74C3C", highlightcolor="#E74C3C",
                                                                highlightthickness=2)
        self.required_keywords_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(row5, text="可不填，可从TXT导入或在此编辑",
                  foreground="gray").pack(side=tk.LEFT)

        # 首词编辑框 - 绿色边框
        row6 = ttk.Frame(main)
        row6.pack(fill=tk.X, pady=3)
        ttk.Label(row6, text="首词\n（每行一个）：", width=14).pack(side=tk.LEFT, anchor=tk.N)
        self.first_words_text = scrolledtext.ScrolledText(row6, height=4, width=40,
                                                          highlightbackground="#27AE60", highlightcolor="#27AE60",
                                                          highlightthickness=2)
        self.first_words_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(row6, text="可不填，一行一个首词，\n程序会随机选择一个放在最前面",
                  foreground="gray").pack(side=tk.LEFT)

        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=10)
        self.start_btn = ttk.Button(btn_row, text="开始生成", command=self._start_generation)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_row, text="停止", command=self._stop_generation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(5, 0))
        self.progress_label = ttk.Label(main, text="")
        self.progress_label.pack()

        self.log_area = scrolledtext.ScrolledText(main, height=14, width=80, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)

    def _select_mp4_folder(self):
        folder = filedialog.askdirectory(title="选择 MP4 文件夹")
        if folder:
            self.mp4_folder.set(folder)
            if self.smart_mode.get():
                self._analyze_mp4_files(folder)

    def _on_smart_mode_toggle(self):
        """智能模式切换处理"""
        if self.smart_mode.get():
            # 启用智能模式：禁用手动选择，自动分析
            self.cb_level.config(state="disabled")
            if self.mp4_folder.get():
                self._analyze_mp4_files(self.mp4_folder.get())
        else:
            # 关闭智能模式：启用手动选择
            self.cb_level.config(state="readonly")

    def _analyze_mp4_files(self, folder):
        """智能分析文件夹中的MP4文件，找到每个文件的最低层级地区，设置默认目标层级"""
        import os
        from pathlib import Path
        from collections import Counter

        extractor = self.extractor_ref.get("extractor")
        if not extractor:
            return

        # 扫描MP4文件
        mp4_files = []
        for f in os.listdir(folder):
            if f.lower().endswith('.mp4'):
                mp4_files.append(f)

        if not mp4_files:
            return

        # 统计每个文件的最低层级
        lowest_levels = Counter()
        sample_size = min(50, len(mp4_files))  # 最多分析50个文件作为样本

        for filename in mp4_files[:sample_size]:
            # 获取文件中的所有匹配候选者，找到最低层级
            try:
                candidates = extractor.get_all_candidates(filename)
                if candidates:
                    # 找到所有候选者中的最低层级（数字最大的层级）
                    lowest_level = max(c["level"] for c in candidates)
                    lowest_levels[lowest_level] += 1
            except Exception as e:
                # 如果分析失败，跳过这个文件
                continue

        if not lowest_levels:
            return

        # 找到最常见的最低层级
        most_common_lowest_level = lowest_levels.most_common(1)[0][0]
        level_name_map = {1: "省级", 2: "市级", 3: "区县级", 4: "乡镇街道级", 5: "村社区级"}
        default_level_name = level_name_map.get(most_common_lowest_level, "区县级")

        # 设置默认值
        self.target_level.set(default_level_name)

        # 显示统计信息（如果日志区域已初始化）
        total_analyzed = sum(lowest_levels.values())
        if total_analyzed > 0:
            level_distribution = ", ".join([
                f"{level_name_map[l]}: {count}"
                for l, count in sorted(lowest_levels.items())
            ])
            try:
                self._log(f"智能分析完成：共 {len(mp4_files)} 个MP4文件，"
                         f"分析了 {sample_size} 个样本，"
                         f"各文件最低层级分布：{level_distribution}，"
                         f"智能选择：{default_level_name}")
            except:
                # 如果日志区域还没准备好，静默跳过
                pass


    def _select_keyword_file(self):
        file = filedialog.askopenfilename(
            title="选择关键词 TXT",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if file:
            self.keyword_file.set(file)

    def _select_required_keyword_file(self):
        file = filedialog.askopenfilename(
            title="选择必选关键词 TXT",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if file:
            self.required_keyword_file.set(file)

    def _log(self, msg):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _update_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.progress_label.configure(text=f"{current}/{total}")

    def _start_generation(self):
        mp4_folder = self.mp4_folder.get().strip()
        keyword_file = self.keyword_file.get().strip()

        if not mp4_folder or not os.path.isdir(mp4_folder):
            messagebox.showwarning("提示", "请先选择有效的 MP4 文件夹")
            return
        if not keyword_file or not os.path.isfile(keyword_file):
            messagebox.showwarning("提示", "请先选择有效的关键词 TXT 文件")
            return

        try:
            target_length = int(self.target_length.get().strip())
            if target_length < 10:
                messagebox.showwarning("提示", "目标文本长度至少为 10")
                return
        except ValueError:
            messagebox.showwarning("提示", "目标文本长度必须为整数")
            return

        mode = "priority" if self.extract_mode.get() == "优先提取" else "force"
        level_map = {"省级": 1, "市级": 2, "区县级": 3, "乡镇街道级": 4, "村社区级": 5}
        target_level = level_map.get(self.target_level.get(), 3)

        first_words_text = self.first_words_text.get("1.0", tk.END)

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress["value"] = 0
        self.progress_label.configure(text="")
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state=tk.DISABLED)

        self._log("正在启动处理...")

        def _log_safe(msg):
            self.after(0, lambda: self._log(msg))

        def _progress_safe(current, total):
            self.after(0, lambda: self._update_progress(current, total))

        self._cancelled = False

        def run():
            try:
                from worker import run_generation
                extractor = self.extractor_ref.get("extractor")
                if extractor is None:
                    _log_safe("错误：地区提取器未初始化")
                    return

                required_keyword_file = self.required_keyword_file.get().strip()
                required_keywords_text = self.required_keywords_text.get("1.0", tk.END)
                required_keyword_order = self.required_keyword_order.get()

                result = run_generation(
                    mp4_folder=mp4_folder,
                    keyword_file=keyword_file,
                    required_keyword_file=required_keyword_file,
                    required_keywords_text=required_keywords_text,
                    required_keyword_order=required_keyword_order,
                    first_words_text=first_words_text,
                    target_length=target_length,
                    mode=mode,
                    target_level=target_level,
                    extractor=extractor,
                    log_callback=_log_safe,
                    progress_callback=_progress_safe,
                )
                _log_safe("")
                if result.get("success"):
                    _log_safe(result["summary"])
                else:
                    _log_safe(f"错误：{result.get('error', '未知错误')}")
            except Exception as e:
                _log_safe(f"发生异常：{e}")
            finally:
                self.after(0, self._on_done)

        threading.Thread(target=run, daemon=True).start()

    def _stop_generation(self):
        self._cancelled = True
        self._log("用户取消了操作（正在处理的任务会继续完成）")

    def _on_done(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
