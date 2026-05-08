import re
import shutil
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


def get_folder_suffix(folder_index):
    return f"_文件夹{folder_index}"


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


def build_move_preview(root_dir, remove_text):
    tasks = []
    used_paths = set()

    root_dir = Path(root_dir)
    subfolders = sorted(
        [p for p in root_dir.iterdir() if p.is_dir()],
        key=natural_sort_key,
    )

    for folder_index, subfolder in enumerate(subfolders, start=1):
        folder_suffix = get_folder_suffix(folder_index)

        videos = [p for p in subfolder.iterdir() if is_video_file(p)]
        videos.sort(key=lambda x: (get_create_time(x), x.name.lower()))

        for index, video_path in enumerate(videos, start=1):
            cleaned_stem = clean_stem(video_path.stem, remove_text)
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

        if videos:
            new_folder_name = f"{subfolder.name}{folder_suffix}"
            folder_target = root_dir / new_folder_name
            if folder_target.resolve() != subfolder.resolve():
                folder_target = get_unique_path(
                    target_path=folder_target,
                    used_paths=used_paths,
                    source_path=subfolder,
                )
                tasks.append({
                    "mode": "rename_folder",
                    "operation": "重命名文件夹",
                    "source": subfolder,
                    "target": folder_target,
                    "folder_index": folder_index,
                    "folder_suffix": folder_suffix,
                    "source_folder": subfolder.name,
                })

    _resolve_name_conflicts(tasks, used_paths)
    return tasks


def build_rename_only_preview(root_dir, remove_text):
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

    for video_path in all_videos:
        cleaned_stem = clean_stem(video_path.stem, remove_text)
        new_name = f"{cleaned_stem}{video_path.suffix}"
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


def execute_tasks(tasks):
    success_count = 0
    fail_count = 0
    logs = []

    for task in tasks:
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
            logs.append({
                "success": True,
                "message": f"完成：{source.name} -> {target.name}",
            })
        except Exception as e:
            fail_count += 1
            logs.append({
                "success": False,
                "message": f"失败：{source.name} -> {target.name}",
                "reason": str(e),
            })

    return {
        "success_count": success_count,
        "fail_count": fail_count,
        "total": len(tasks),
        "logs": logs,
    }
