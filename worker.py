import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import MAX_WORKERS, OUTPUT_ENCODING
from text_generator import generate_text


def process_one_mp4(mp4_file, keywords, required_keywords, required_keyword_order, first_words, separator, target_length, extractor, mode, target_level, smart_mode=False):
    actual_mode = "lowest" if smart_mode else mode
    region_result = extractor.extract(str(mp4_file), actual_mode, target_level)
    area_name = region_result["name"]

    text = generate_text(
        area_name=area_name,
        keywords=keywords,
        first_words=first_words,
        required_keywords=required_keywords,
        required_keyword_order=required_keyword_order,
        separator=separator,
        target_length=target_length,
    )

    output_txt = mp4_file.with_suffix(".txt")
    output_txt.write_text(text, encoding=OUTPUT_ENCODING)

    return {
        "success": True,
        "message": region_result["reason"],
        "output_file": str(output_txt),
        "original_name": mp4_file.stem,
        "region_result": region_result,
        "text_length": len(text),
    }


def scan_mp4_files(folder_path):
    folder = Path(folder_path)
    mp4_files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".mp4":
            mp4_files.append(f)
    mp4_files.sort(key=lambda x: x.name.lower())
    return mp4_files


def run_generation(mp4_folder, keyword_file, keywords_text, required_keyword_file, required_keywords_text,
                   required_keyword_order, first_words_text, separator, target_length,
                   mode, target_level, extractor, log_callback, progress_callback, smart_mode=False):
    keywords = []
    required_keywords = []
    first_words = []
    errors = []

    from text_generator import load_keywords, load_lines, load_first_words, load_required_keywords

    if keyword_file and Path(keyword_file).is_file():
        keywords = load_keywords(keyword_file)
    if not keywords and keywords_text and keywords_text.strip():
        keywords = load_lines(keywords_text)
    if not keywords:
        return {"success": False, "error": "关键词为空"}

    if required_keyword_file:
        if Path(required_keyword_file).is_file():
            try:
                required_keywords = load_keywords(required_keyword_file)
            except Exception as e:
                return {"success": False, "error": f"必选关键词文件读取失败：{e}"}

    required_keywords += [kw for kw in load_required_keywords(required_keywords_text) if kw not in required_keywords]
    first_words = load_first_words(first_words_text)

    mp4_files = scan_mp4_files(mp4_folder)
    if not mp4_files:
        return {"success": False, "error": "文件夹中没有 MP4 文件"}

    total = len(mp4_files)
    success_count = 0
    fail_count = 0
    start_time = time.perf_counter()

    workers = MAX_WORKERS

    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for mp4 in mp4_files:
            future = executor.submit(
                process_one_mp4,
                mp4, keywords, required_keywords, required_keyword_order,
                first_words, separator, target_length,
                extractor, mode, target_level, smart_mode,
            )
            futures[future] = mp4

        for future in as_completed(futures):
            mp4 = futures[future]
            completed += 1
            try:
                result = future.result()
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
                results.append(result)

                if completed % 20 == 0 or completed == total:
                    progress_callback(completed, total)
                    if result["success"]:
                        log_callback(
                            f"[成功] {Path(result['output_file']).name} | "
                            f"原名：{result['original_name']} | "
                            f"提取地区：{result['region_result']['name']} | "
                            f"模式：{result['region_result']['mode']} | "
                            f"目标层级：{result['region_result']['target_level_name']} | "
                            f"实际字数：{result['text_length']}"
                        )
            except Exception as e:
                fail_count += 1
                log_callback(f"[失败] {mp4.name} | 原因：{e}")

            progress_callback(completed, total)

    elapsed = time.perf_counter() - start_time
    speed = total / elapsed if elapsed > 0 else 0

    summary = (
        f"处理完成\n"
        f"文件总数：{total}\n"
        f"成功数量：{success_count}\n"
        f"失败数量：{fail_count}\n"
        f"总耗时：{elapsed:.1f} 秒\n"
        f"平均速度：{speed:.1f} 个/秒\n"
        f"线程数量：{workers}\n"
        f"地区库数量：{len(extractor.region_db.regions)}\n"
        f"关键词数量：{len(keywords)}"
    )

    return {
        "success": True,
        "success_count": success_count,
        "fail_count": fail_count,
        "total": total,
        "elapsed": elapsed,
        "speed": speed,
        "summary": summary,
    }
