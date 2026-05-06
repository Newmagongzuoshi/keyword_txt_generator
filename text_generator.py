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


def load_first_words(text):
    if not text or not text.strip():
        return []
    lines = text.splitlines()
    words = []
    seen = set()
    for line in lines:
        w = line.strip()
        if w and w not in seen:
            words.append(w)
            seen.add(w)
    return words


def generate_text(area_name, keywords, first_words, target_length):
    if not keywords:
        return area_name

    variation = random.uniform(MIN_LENGTH_VARIATION_RATE, MAX_LENGTH_VARIATION_RATE)
    if random.random() < 0.5:
        variation = -variation
    max_length = int(target_length * (1 + variation))
    max_length = max(20, max_length)

    best_items = []
    best_length = 0

    for _ in range(RANDOM_ATTEMPTS):
        shuffled = list(keywords)
        random.shuffle(shuffled)

        items = []
        current_length = 0

        for keyword in shuffled:
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

    if not best_items and keywords:
        fw = first_words[0] if first_words else keywords[0]
        best_items = [area_name + fw]
        best_length = len(best_items[0])

    return "，".join(best_items)
