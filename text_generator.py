import random
from pathlib import Path

from config import (
    MIN_LENGTH_VARIATION_RATE,
    MAX_LENGTH_VARIATION_RATE,
    RANDOM_ATTEMPTS,
)


def load_keywords(file_path):
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
        raise ValueError(f"无法识别关键词文件编码：{file_path}")

    lines = content.splitlines()
    keywords = []
    seen = set()
    for line in lines:
        kw = line.strip()
        if kw and kw not in seen:
            keywords.append(kw)
            seen.add(kw)
    return keywords


def load_lines(text):
    if not text or not text.strip():
        return []
    lines = text.splitlines()
    values = []
    seen = set()
    for line in lines:
        item = line.strip()
        if item and item not in seen:
            values.append(item)
            seen.add(item)
    return values


def load_first_words(text):
    return load_lines(text)


def load_required_keywords(text):
    return load_lines(text)


def generate_text(area_name, keywords, first_words, required_keywords, required_keyword_order, target_length):
    if not keywords and not required_keywords:
        return area_name

    variation = random.uniform(MIN_LENGTH_VARIATION_RATE, MAX_LENGTH_VARIATION_RATE)
    if random.random() < 0.5:
        variation = -variation
    max_length = int(target_length * (1 + variation))
    max_length = max(20, max_length)

    best_items = []
    best_length = 0

    for _ in range(RANDOM_ATTEMPTS):
        normal_keywords = list(keywords)
        random.shuffle(normal_keywords)

        if required_keywords:
            if required_keyword_order == "随机":
                ordered_required = list(required_keywords)
                random.shuffle(ordered_required)
            else:
                ordered_required = list(required_keywords)
        else:
            ordered_required = []

        items = []
        current_length = 0

        # 先加入必选关键词，必须保留
        for keyword in ordered_required:
            phrase = area_name + keyword
            next_length = len(phrase) if not items else current_length + 1 + len(phrase)
            items.append(phrase)
            current_length = next_length

        for keyword in normal_keywords:
            if first_words and random.random() < 0.5:
                fw = random.choice(first_words)
                phrase = area_name + fw
            else:
                phrase = area_name + keyword

            next_length = current_length + len(phrase)
            if items:
                next_length += 1

            if next_length <= max_length:
                items.append(phrase)
                current_length = next_length
            else:
                break

        if items:
            total = sum(len(item) for item in items) + len(items) - 1
            if abs(total - max_length) < abs(best_length - max_length) or not best_items:
                best_items = items
                best_length = total

    if not best_items and (keywords or required_keywords):
        # 最低兜底：必选关键词优先展示
        if required_keywords:
            phrase = area_name + required_keywords[0]
        else:
            phrase = area_name + (first_words[0] if first_words else keywords[0])
        best_items = [phrase]

    return "，".join(best_items)
