import time
import random
import shutil
from pathlib import Path

from config import OUTPUT_ENCODING, IMAGE_EXTS
from text_generator import generate_text


def scan_images(folder_path):
    """扫描文件夹中的所有图片文件"""
    folder = Path(folder_path)
    images = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
            images.append(f)
    images.sort(key=lambda x: x.name.lower())
    return images


def load_addresses(file_path):
    """读取地址文件，每行一个地址，去重去空"""
    path = Path(file_path)
    content = None
    for encoding in ["utf-8-sig", "utf-8", "gb18030", "gbk"]:
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if content is None:
        raise ValueError(f"无法识别地址文件编码：{file_path}")

    addresses = []
    seen = set()
    for line in content.splitlines():
        addr = line.strip()
        if addr and addr not in seen:
            addresses.append(addr)
            seen.add(addr)
    return addresses


def pick_images_sequential(images, count, pointer, used_first):
    """顺序选取图片，确保首图尽可能不与其他文件夹重复"""
    total = len(images)
    if total == 0:
        return [], 0
    selected = []

    # 首图：若当前指针对应的图片已当过首图，跳到下一个未使用的
    first_idx = pointer % total
    if images[first_idx] in used_first:
        for offset in range(total):
            candidate = images[(first_idx + offset) % total]
            if candidate not in used_first:
                first_idx = (first_idx + offset) % total
                break
        else:
            used_first.clear()
    used_first.add(images[first_idx])

    for i in range(count):
        idx = (first_idx + i) % total
        selected.append(images[idx])
    new_pointer = (first_idx + count) % total
    return selected, new_pointer


def pick_images_random(images, count, used_first):
    """随机选取图片，确保首图尽可能不与其他文件夹重复"""
    if len(images) == 0:
        return []
    if count == 0:
        return []

    # 首图优先从未当过首图的图片中选
    available = [img for img in images if img not in used_first]
    if not available:
        used_first.clear()
        available = list(images)
    first = random.choice(available)
    used_first.add(first)

    # 剩余图片从除首图外的池中随机选取
    remaining = [img for img in images if img != first]
    need = count - 1
    if need <= 0:
        return [first]
    if need >= len(remaining):
        rest = list(remaining)
        extra = need - len(rest)
        if extra > 0:
            rest.extend(random.choices(remaining, k=extra))
        random.shuffle(rest)
    else:
        rest = random.sample(remaining, need)
    return [first] + rest


def process_one_address(address, keywords, required_keywords, required_keyword_order,
                        first_words, separator, target_length, extractor, mode,
                        target_level, smart_mode, output_folder, images, images_per_folder,
                        selection_mode, image_pointer, img_counter_start, used_first):
    """处理单个地址：用地址原文创建文件夹 -> 从文件夹名提取地区 -> 生成TXT -> 复制图片"""
    actual_mode = "lowest" if smart_mode else mode

    # 用地址原文作为文件夹名（重名时加序号避免冲突）
    sub_folder = _unique_folder(Path(output_folder) / address)

    # 从文件夹名提取地区名，用于生成 TXT 文案
    folder_name = sub_folder.name
    region_result = extractor.extract(folder_name, actual_mode, target_level)
    area_name = region_result["name"]

    # 生成同名 TXT
    text = generate_text(
        area_name=area_name,
        keywords=keywords,
        first_words=first_words,
        required_keywords=required_keywords,
        required_keyword_order=required_keyword_order,
        separator=separator,
        target_length=target_length,
    )
    txt_path = sub_folder / f"{folder_name}.txt"
    txt_path.write_text(text, encoding=OUTPUT_ENCODING)

    # 选取图片（used_first 确保首图不重复）
    if selection_mode == "random":
        picked = pick_images_random(images, images_per_folder, used_first)
    else:
        picked, image_pointer = pick_images_sequential(images, images_per_folder, image_pointer, used_first)

    # 复制图片，全局序号命名
    copied_images = []
    counter = img_counter_start
    for img in picked:
        ext = img.suffix
        dest = sub_folder / f"{counter:04d}_{img.name}"
        shutil.copy2(img, dest)
        copied_images.append(dest.name)
        counter += 1

    return {
        "success": True,
        "area_name": area_name,
        "original_address": address,
        "sub_folder": str(sub_folder),
        "txt_file": str(txt_path),
        "text_length": len(text),
        "copied_images": copied_images,
        "region_result": region_result,
        "image_pointer": image_pointer,
        "img_counter": counter,
    }


def _unique_folder(base_path):
    """若文件夹已存在，加 _2, _3... 后缀避免冲突"""
    if not base_path.exists():
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path
    parent = base_path.parent
    stem = base_path.name
    for n in range(2, 1000):
        candidate = parent / f"{stem}_{n}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


def run_image_generation(image_folder, address_file, output_folder, keyword_file,
                         keywords_text, required_keyword_file, required_keywords_text,
                         required_keyword_order, first_words_text, separator,
                         target_length, mode, target_level, images_per_folder,
                         selection_mode, smart_mode, extractor, log_callback,
                         progress_callback):
    from text_generator import load_keywords, load_lines, load_first_words, load_required_keywords

    keywords = []
    if keyword_file and Path(keyword_file).is_file():
        keywords = load_keywords(keyword_file)
    if not keywords and keywords_text and keywords_text.strip():
        keywords = load_lines(keywords_text)
    if not keywords:
        return {"success": False, "error": "关键词为空"}

    required_keywords = []
    if required_keyword_file:
        if Path(required_keyword_file).is_file():
            try:
                required_keywords = load_keywords(required_keyword_file)
            except Exception as e:
                return {"success": False, "error": f"必选关键词文件读取失败：{e}"}
    required_keywords += [kw for kw in load_required_keywords(required_keywords_text)
                          if kw not in required_keywords]

    first_words = load_first_words(first_words_text)

    # 加载地址
    try:
        addresses = load_addresses(address_file)
    except Exception as e:
        return {"success": False, "error": f"地址文件读取失败：{e}"}
    if not addresses:
        return {"success": False, "error": "地址文件为空"}

    # 扫描图片
    images = scan_images(image_folder)
    if not images:
        return {"success": False, "error": "图片文件夹中没有支持的图片文件"}

    total = len(addresses)
    success_count = 0
    fail_count = 0
    start_time = time.perf_counter()

    image_pointer = 0
    img_counter = 1
    used_first = set()
    region_origin_map = {}

    counts_str = ",".join(str(c) for c in images_per_folder)
    log_callback(f"地址数量：{total}，图片数量：{len(images)}，每文件夹图片数：[{counts_str}]")
    log_callback(f"图片选取方式：{selection_mode}")

    for idx, address in enumerate(addresses):
        count = images_per_folder[idx % len(images_per_folder)]
        try:
            result = process_one_address(
                address=address,
                keywords=keywords,
                required_keywords=required_keywords,
                required_keyword_order=required_keyword_order,
                first_words=first_words,
                separator=separator,
                target_length=target_length,
                extractor=extractor,
                mode=mode,
                target_level=target_level,
                smart_mode=smart_mode,
                output_folder=output_folder,
                images=images,
                images_per_folder=count,
                selection_mode=selection_mode,
                image_pointer=image_pointer,
                img_counter_start=img_counter,
                used_first=used_first,
            )
            if selection_mode == "sequential":
                image_pointer = result["image_pointer"]
            img_counter = result["img_counter"]

            success_count += 1
            rr = result["region_result"]
            region_name = rr["name"]
            if region_name not in region_origin_map:
                region_origin_map[region_name] = []
            region_origin_map[region_name].append({
                "original": result["original_address"],
                "is_fallback": rr.get("is_fallback", False),
                "level_name": rr.get("level_name", ""),
            })

            progress_callback(idx + 1, total)
            log_callback(
                f"[成功] {result['area_name']} | "
                f"原地址：{result['original_address']} | "
                f"提取地区：{rr['name']} | "
                f"层级：{rr['level_name']} | "
                f"模式：{rr['mode']} | "
                f"字数：{result['text_length']} | "
                f"图片：{len(result['copied_images'])}张"
            )
        except Exception as e:
            fail_count += 1
            log_callback(f"[失败] {address} | 原因：{e}")
            progress_callback(idx + 1, total)

    elapsed = time.perf_counter() - start_time
    speed = total / elapsed if elapsed > 0 else 0

    summary = (
        f"处理完成\n"
        f"地址总数：{total}\n"
        f"成功数量：{success_count}\n"
        f"失败数量：{fail_count}\n"
        f"总耗时：{elapsed:.1f} 秒\n"
        f"平均速度：{speed:.1f} 个/秒\n"
        f"关键词数量：{len(keywords)}"
    )

    return {
        "success": True,
        "success_count": success_count,
        "fail_count": fail_count,
        "total": total,
        "elapsed": elapsed,
        "summary": summary,
        "region_origin_map": region_origin_map,
    }
