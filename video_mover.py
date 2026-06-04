import ctypes
import re
import random
import shutil
from datetime import datetime
from pathlib import Path

from config import VIDEO_EXTS


def is_video_file(file_path):
    return file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTS


def get_create_time(file_path):
    return file_path.stat().st_ctime


def clean_stem(stem, remove_text):
    if remove_text:
        stem = stem.replace(remove_text, "")
    stem = stem.strip()
    if not stem:
        stem = "未命名"
    return stem


def natural_sort_key(path):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", path.name)
    ]


def get_folder_suffix(folder_index, prefix="_文件夹"):
    return f"{prefix}{folder_index}"


def get_unique_path(target_path, used_paths, source_path=None):
    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix

    candidate = target_path
    index = 1

    while True:
        candidate_key = str(candidate).lower()

        if source_path is not None and candidate.resolve() == source_path.resolve():
            return candidate

        if not candidate.exists() and candidate_key not in used_paths:
            used_paths.add(candidate_key)
            return candidate

        candidate = parent / f"{stem}{index:02d}{suffix}"
        index += 1


def _resolve_name_conflicts(tasks, used_paths):
    base_name_groups = {}
    for task in tasks:
        target = task["target"]
        base_stem = target.stem
        while base_stem and (base_stem[-1].isdigit() or base_stem[-1] == "0"):
            if len(base_stem) >= 2 and base_stem[-2:].isdigit() and len(base_stem) >= 3:
                prev = base_stem[:-2]
                if prev and not prev[-1].isdigit():
                    break
            break
        else:
            base_key = base_stem + target.suffix.lower()
            if base_key not in base_name_groups:
                base_name_groups[base_key] = []
            base_name_groups[base_key].append(task)

    for base_key, group in base_name_groups.items():
        if len(group) > 1:
            continue
        task = group[0]
        target = task["target"]
        target_key = str(target).lower()
        if target_key in used_paths or (target.exists() and
           (task.get("source") is None or target.resolve() != task["source"].resolve())):
            parent = target.parent
            stem = target.stem
            suffix = target.suffix
            index = 1
            while True:
                candidate = parent / f"{stem}{index:02d}{suffix}"
                candidate_key = str(candidate).lower()
                if not candidate.exists() and candidate_key not in used_paths:
                    task["target"] = candidate
                    used_paths.add(candidate_key)
                    break
                index += 1

    return tasks


def _build_keyword_pool(keywords, total_needed):
    """用关键词构建随机池，至少覆盖所需数量"""
    if not keywords or total_needed == 0:
        return []
    pool = []
    while len(pool) < total_needed:
        batch = list(keywords)
        random.shuffle(batch)
        pool.extend(batch)
    return pool[:total_needed]


def build_move_preview(root_dir, remove_text, folder_prefix="_文件夹", start_number=1,
                       suffix_keywords=None):
    tasks = []
    used_paths = set()

    root_dir = Path(root_dir)
    subfolders = sorted(
        [p for p in root_dir.iterdir() if p.is_dir()],
        key=natural_sort_key,
    )

    # 预先统计视频总数（≥5取直接，<5优先"生成的视频"）
    total_videos = 0
    for subfolder in subfolders:
        direct_count = len([p for p in subfolder.iterdir() if is_video_file(p)])
        if direct_count >= 5:
            total_videos += direct_count
        else:
            generated_dir = subfolder / "生成的视频"
            generated_videos = [p for p in generated_dir.iterdir() if is_video_file(p)] if generated_dir.is_dir() else []
            total_videos += len(generated_videos) if generated_videos else direct_count
    kw_pool = _build_keyword_pool(suffix_keywords or [], total_videos)
    kw_index = 0
    used_combos = set()  # 用于关键词模式下主动避重

    for idx, subfolder in enumerate(subfolders):
        folder_index = start_number + idx
        folder_suffix = get_folder_suffix(folder_index, folder_prefix)

        # 子文件夹直接视频 ≥5 则用直接视频；否则检查"生成的视频"
        direct_videos = [p for p in subfolder.iterdir() if is_video_file(p)]
        if len(direct_videos) >= 5:
            videos = direct_videos
        else:
            generated_dir = subfolder / "生成的视频"
            generated_videos = [p for p in generated_dir.iterdir() if is_video_file(p)] if generated_dir.is_dir() else []
            videos = generated_videos if generated_videos else direct_videos
        videos.sort(key=lambda x: (get_create_time(x), x.name.lower()))

        for index, video_path in enumerate(videos, start=1):
            cleaned_stem = clean_stem(video_path.stem, remove_text)
            if kw_pool:
                # 主动避重：尝试关键词直到找到未用过的组合
                suffix = video_path.suffix
                kw = None
                for attempt in range(len(kw_pool)):
                    candidate_kw = kw_pool[(kw_index + attempt) % len(kw_pool)]
                    combo = f"{cleaned_stem}{candidate_kw}{suffix}".lower()
                    if combo not in used_combos:
                        kw = candidate_kw
                        kw_index = (kw_index + attempt + 1) % len(kw_pool)
                        break
                if kw is None:
                    kw = kw_pool[kw_index]
                    kw_index += 1
                target_stem = f"{cleaned_stem}{kw}"
                target_path = root_dir / f"{target_stem}{suffix}"
                # 直接注册路径，确保后续不重复；跳过 get_unique_path 的尾号逻辑
                used_paths.add(str(target_path).lower())
            else:
                target_stem = f"{index:04d}{cleaned_stem}{folder_suffix}"
                target_path = root_dir / f"{target_stem}{video_path.suffix}"
                target_path = get_unique_path(
                    target_path=target_path,
                    used_paths=used_paths,
                    source_path=video_path,
                )

            tasks.append({
                "mode": "move",
                "operation": "移动并重命名",
                "source": video_path,
                "target": target_path,
                "folder_index": folder_index,
                "folder_suffix": folder_suffix,
                "source_folder": subfolder.name,
            })


    # 关键词模式下已在分配阶段主动避重，无需冲突检测
    if not kw_pool:
        _resolve_name_conflicts(tasks, used_paths)
    return tasks


def build_rename_only_preview(root_dir, remove_text, suffix_keywords=None):
    if not remove_text or not remove_text.strip():
        return []

    tasks = []
    used_paths = set()
    root_dir = Path(root_dir)

    all_videos = [p for p in root_dir.iterdir() if is_video_file(p)]

    subfolders = sorted(
        [p for p in root_dir.iterdir() if p.is_dir()],
        key=natural_sort_key,
    )
    for subfolder in subfolders:
        all_videos.extend([p for p in subfolder.iterdir() if is_video_file(p)])

    kw_pool = _build_keyword_pool(suffix_keywords or [], len(all_videos))
    kw_index = 0
    used_combos = set()

    for video_path in all_videos:
        cleaned_stem = clean_stem(video_path.stem, remove_text)
        suffix = video_path.suffix
        if kw_pool:
            # 主动避重：尝试关键词直到找到未用过的组合
            kw = None
            for attempt in range(len(kw_pool)):
                candidate_kw = kw_pool[(kw_index + attempt) % len(kw_pool)]
                combo = f"{cleaned_stem}{candidate_kw}{suffix}".lower()
                if combo not in used_combos:
                    kw = candidate_kw
                    kw_index = (kw_index + attempt + 1) % len(kw_pool)
                    break
            if kw is None:
                kw = kw_pool[kw_index]
                kw_index += 1
            new_name = f"{cleaned_stem}{kw}{suffix}"
            target_path = video_path.parent / new_name
            used_combos.add(combo if kw else f"{cleaned_stem}{kw}{suffix}".lower())
            used_paths.add(str(target_path).lower())
            if target_path.resolve() == video_path.resolve():
                continue
        else:
            new_name = f"{cleaned_stem}{suffix}"
            target_path = video_path.parent / new_name
            if target_path.resolve() == video_path.resolve():
                continue
            target_path = get_unique_path(
                target_path=target_path,
                used_paths=used_paths,
                source_path=video_path,
            )

        tasks.append({
            "mode": "rename",
            "operation": "仅重命名",
            "source": video_path,
            "target": target_path,
            "folder_index": 0,
            "folder_suffix": "",
            "source_folder": video_path.parent.name,
        })

    return tasks


def execute_tasks(tasks, root_dir=None, progress_callback=None):
    success_count = 0
    fail_count = 0
    logs = []
    success_lines = []
    fail_lines = []
    total = len(tasks)

    for idx, task in enumerate(tasks):
        source = task["source"]
        target = task["target"]
        try:
            if task["mode"] == "move":
                shutil.move(str(source), str(target))
            elif task["mode"] == "rename_folder":
                source.rename(target)
            else:
                source.rename(target)
            success_count += 1
            success_lines.append((str(source), str(target)))
            logs.append({
                "success": True,
                "message": f"完成：{source.name} -> {target.name}",
            })
        except Exception as e:
            fail_count += 1
            fail_lines.append((str(source), str(target), str(e)))
            logs.append({
                "success": False,
                "message": f"失败：{source.name} -> {target.name}",
                "reason": str(e),
            })
        # 每 10 个或最后一个时回调进度
        if progress_callback and ((idx + 1) % 10 == 0 or idx + 1 == total):
            progress_callback(idx + 1, total)

    # 一次性写入 .log 隐藏文件
    log_path = None
    if root_dir:
        root = Path(root_dir)
        log_path = root / "移动日志.log"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"# 移动日志 - {now}"]
        for src, dst in success_lines:
            try:
                lines.append(f"{Path(src).relative_to(root)}\t->\t{Path(dst).relative_to(root)}")
            except ValueError:
                lines.append(f"{src}\t->\t{dst}")
        for src, dst, reason in fail_lines:
            try:
                lines.append(f"[失败] {Path(src).relative_to(root)}\t->\t{Path(dst).relative_to(root)}\t原因：{reason}")
            except ValueError:
                lines.append(f"[失败] {src}\t->\t{dst}\t原因：{reason}")
        log_path.write_text("\n".join(lines), encoding="utf-8")
        try:
            ctypes.windll.kernel32.SetFileAttributesW(str(log_path), 0x2)
        except Exception:
            pass

        # 用户可读 .txt
        if success_lines:
            tlines = [f"# 移动日志 - {now}"]
            for src, dst in success_lines:
                try:
                    tlines.append(f"{Path(src).relative_to(root)}\t->\t{Path(dst).relative_to(root)}")
                except ValueError:
                    tlines.append(f"{src}\t->\t{dst}")
            (root / "移动日志.txt").write_text("\n".join(tlines), encoding="utf-8")
        if fail_lines:
            flines = [f"# 移动失败日志 - {now}"]
            for src, dst, reason in fail_lines:
                try:
                    flines.append(f"{Path(src).relative_to(root)}\t->\t{Path(dst).relative_to(root)}\t原因：{reason}")
                except ValueError:
                    flines.append(f"{src}\t->\t{dst}\t原因：{reason}")
            (root / "移动失败日志.txt").write_text("\n".join(flines), encoding="utf-8")

    return {
        "success_count": success_count,
        "fail_count": fail_count,
        "total": len(tasks),
        "logs": logs,
        "log_path": str(log_path) if log_path else None,
    }


def restore_from_log(log_path, root_dir=None):
    """根据移动日志还原文件到原始位置。返回 (success, fail, logs, restore_log_path)"""
    path = Path(log_path)
    if not path.is_file():
        return 0, 0, [{"success": False, "message": f"日志文件不存在：{log_path}"}], None

    content = path.read_text(encoding="utf-8")
    records = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("[失败]"):
            continue
        parts = line.split("\t->\t")
        if len(parts) == 2:
            records.append((parts[0], parts[1]))

    if not records:
        return 0, 0, [{"success": False, "message": "日志中没有可还原的记录"}], None

    root = Path(root_dir) if root_dir else Path(log_path).parent
    success = 0
    fail = 0
    logs = []
    restore_records = []
    for src, dst in records:
        src_path = root / src if not Path(src).is_absolute() else Path(src)
        dst_path = root / dst if not Path(dst).is_absolute() else Path(dst)
        try:
            if dst_path.exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst_path), str(src_path))
                success += 1
                restore_records.append((str(dst_path), str(src_path)))
                logs.append({
                    "success": True,
                    "message": f"还原：{dst_path.name} -> {src_path.name}",
                })
            else:
                fail += 1
                logs.append({
                    "success": False,
                    "message": f"文件不存在，跳过：{dst_path.name}",
                    "reason": "目标文件已不存在",
                })
        except Exception as e:
            fail += 1
            logs.append({
                "success": False,
                "message": f"还原失败：{dst_path.name}",
                "reason": str(e),
            })

    # 删除旧 .log，一次性写入新 .log（反映还原后的状态）
    try:
        path.unlink()
    except Exception:
        pass

    new_log_path = None
    restore_txt_path = None
    if root_dir and restore_records:
        root = Path(root_dir)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # .log 隐藏文件
        new_log_path = root / "移动日志.log"
        log_lines = [f"# 移动日志 - {now}"]
        for dst, src in restore_records:
            try:
                log_lines.append(f"{Path(dst).relative_to(root)}\t->\t{Path(src).relative_to(root)}")
            except ValueError:
                log_lines.append(f"{dst}\t->\t{src}")
        new_log_path.write_text("\n".join(log_lines), encoding="utf-8")
        try:
            ctypes.windll.kernel32.SetFileAttributesW(str(new_log_path), 0x2)
        except Exception:
            pass

        # 用户可读 .txt
        restore_txt_path = root / "撤销移动日志.txt"
        txt_lines = [f"# 撤销移动日志 - {now}"]
        for dst, src in restore_records:
            try:
                txt_lines.append(f"{Path(dst).relative_to(root)}\t->\t{Path(src).relative_to(root)}")
            except ValueError:
                txt_lines.append(f"{dst}\t->\t{src}")
        restore_txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

    return success, fail, logs, str(restore_txt_path) if restore_txt_path else None
