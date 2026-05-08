import pickle
import re
from pathlib import Path

from config import (
    DIGIT_TRANSLATION,
    INVALID_PREFIXES,
    INVALID_TAIL_WORDS,
    ENABLE_EXTRACT_CACHE,
)


class TrieNode:
    __slots__ = ("children", "regions")

    def __init__(self):
        self.children = {}
        self.regions = []


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word, region):
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.regions.append(region)

    def search_all_matches(self, text):
        matches = []
        n = len(text)
        for i in range(n):
            node = self.root
            for j in range(i, n):
                ch = text[j]
                if ch not in node.children:
                    break
                node = node.children[ch]
                for region in node.regions:
                    matches.append({
                        "region": region,
                        "matched_text": text[i:j + 1],
                        "start": i,
                        "end": j + 1,
                    })
        return matches


class RegionExtractor:
    def __init__(self, region_db):
        self.region_db = region_db
        self.trie = Trie()
        self.normalize_cache = {}
        self.extract_cache = {}
        self._build_trie()

    @classmethod
    def load(cls, region_db, cache_path=None, force_rebuild=False):
        if cache_path is None:
            cache_path = Path(__file__).parent / "region_extractor.pkl"
        else:
            cache_path = Path(cache_path)

        if not force_rebuild and cache_path.exists():
            source_path = getattr(region_db, "source_path", None)
            if source_path is None or cache_path.stat().st_mtime >= source_path.stat().st_mtime:
                try:
                    with open(cache_path, "rb") as f:
                        extractor = pickle.load(f)
                    extractor.region_db = region_db
                    # 重新初始化缓存，避免pickle序列化问题
                    extractor.normalize_cache = {}
                    extractor.extract_cache = {}
                    return extractor
                except Exception:
                    pass

        extractor = cls(region_db)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(extractor, f, pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass
        return extractor

    def _build_trie(self):
        for region in self.region_db.regions:
            names = set()
            names.add(region["name"])
            names.add(region["short_name"])
            for alias in region.get("aliases", []):
                names.add(alias)
            for name in names:
                name = name.strip()
                if name:
                    self.trie.insert(name, region)

    def normalize_filename_cached(self, filename):
        """带缓存的文件名规范化"""
        if filename in self.normalize_cache:
            return self.normalize_cache[filename]
        result = self.normalize_filename(filename)
        self.normalize_cache[filename] = result
        return result

    def normalize_filename(self, filename):
        stem = Path(filename).stem
        # 去除 _文件夹N / -文件夹N / _文件夹 等后缀（支持中文数字）
        stem = re.sub(r"[_\-－—–]\s*文件夹\s*[一二三四五六七八九十\d]*$", "", stem)
        text = stem.translate(DIGIT_TRANSLATION)
        text = re.sub(r"\d+", "", text)
        # 将地区间常见分隔符替换为空格，避免粘连
        text = re.sub(r"[_\-－—–·、，,。/\\~→\s]+", " ", text)
        chinese_parts = re.findall(r"[一-鿿]+", text)
        text = "".join(chinese_parts)

        changed = True
        while changed:
            changed = False
            for prefix in INVALID_PREFIXES:
                if text.startswith(prefix) and len(text) > len(prefix):
                    text = text[len(prefix):]
                    changed = True
                    break

        changed = True
        while changed:
            changed = False
            for tail in INVALID_TAIL_WORDS:
                if text.endswith(tail) and len(text) > len(tail):
                    text = text[:-len(tail)]
                    changed = True
                    break

        return text.strip()

    def get_all_candidates(self, filename):
        """获取文件名中的所有地区候选者，用于智能模式分析"""
        clean_text = self.normalize_filename_cached(filename)
        candidates = self.match_regions(clean_text)
        candidates = self.filter_invalid_candidates(candidates)
        return candidates

    def _is_direct_name(self, match):
        r = match["region"]
        t = match["matched_text"]
        return t == r["name"] or t == r["short_name"]

    def match_regions(self, text):
        raw_matches = self.trie.search_all_matches(text)
        if not raw_matches:
            return []

        raw_matches.sort(key=lambda m: (m["start"], m["region"]["level"]))

        def _resolve_overlap(m, k):
            """Determine which of two overlapping matches to keep. Returns 'm', 'k', or None (skip both)."""
            m_start, m_end = m["start"], m["end"]
            k_start, k_end = k["start"], k["end"]
            m_level = m["region"]["level"]
            k_level = k["region"]["level"]
            m_len = m_end - m_start
            k_len = k_end - k_start
            m_direct = self._is_direct_name(m)
            k_direct = self._is_direct_name(k)

            if m_start >= k_start and m_end <= k_end:
                return "k"  # m完全被k包含，保留k
            if k_start >= m_start and k_end <= m_end:
                return "m"  # k完全被m包含，保留m

            # 部分重叠：优先直接名称匹配，然后长度
            if m_direct and not k_direct:
                return "m"
            if k_direct and not m_direct:
                return "k"

            if m_len >= k_len * 2:
                return "m"  # m明显更长，更可信
            if k_len >= m_len * 2:
                return "k"  # k明显更长，更可信

            if m_level > k_level:
                return "m"
            if k_level > m_level:
                return "k"

            if m_len > k_len:
                return "m"
            return "k"

        kept = []
        for m in raw_matches:
            should_keep = True
            for i, k in enumerate(kept):
                if not (m["end"] <= k["start"] or m["start"] >= k["end"]):
                    winner = _resolve_overlap(m, k)
                    if winner == "m":
                        kept[i] = m
                        should_keep = False
                        break
                    else:
                        should_keep = False
                        break
            if should_keep:
                kept.append(m)

        candidates = []
        for m in kept:
            r = m["region"]
            candidates.append({
                "region": r,
                "name": m["matched_text"],
                "display_name": m["matched_text"],
                "matched_text": m["matched_text"],
                "start": m["start"],
                "end": m["end"],
                "level": r["level"],
                "level_name": r["level_name"],
                "region_id": r["id"],
                "parent_chain": r.get("parent_chain", []),
            })
        return candidates

    def filter_invalid_candidates(self, candidates):
        return [
            c for c in candidates
            if c["name"] not in INVALID_TAIL_WORDS
            and c["matched_text"] not in INVALID_TAIL_WORDS
        ]

    def get_all_candidates(self, filename):
        """获取文件名中的所有地区候选者，用于分析最低层级"""
        clean_text = self.normalize_filename_cached(filename)
        raw_candidates = self.match_regions(clean_text)
        return self.filter_invalid_candidates(raw_candidates)
        exact = [c for c in candidates if c["level"] == target_level]
        if exact:
            return self._choose_best(exact, target_level)

        upper = [c for c in candidates if c["level"] < target_level]
        if upper:
            upper.sort(key=lambda c: c["level"], reverse=True)
            best = upper[0]
            best["is_fallback"] = True
            best["reason"] = (
                f"未找到{best.get('target_level_name', '')}级地区，"
                f"降级为{best['level_name']}：{best['name']}"
            )
            return best

        if candidates:
            best = self._choose_most_specific(candidates)
            best["is_fallback"] = True
            best["reason"] = f"未找到目标层级，使用最佳匹配：{best['name']}"
            return best

        return None

    def select_by_force(self, candidates, target_level):
        source = self._choose_most_specific(candidates)
        if source is None:
            return None

        if source["level"] == target_level:
            source["reason"] = f"成功提取{source['level_name']}地区：{source['name']}"
            return source

        if source["level"] > target_level:
            target_region = self.region_db.resolve_parent_at_level(
                source["region"], target_level
            )
            if target_region:
                result = {
                    "region": target_region,
                    "name": target_region["name"],
                    "display_name": target_region["name"],
                    "matched_text": source["matched_text"],
                    "start": source["start"],
                    "end": source["end"],
                    "level": target_region["level"],
                    "level_name": target_region["level_name"],
                    "region_id": target_region["id"],
                    "parent_chain": target_region.get("parent_chain", []),
                    "source_region": source["name"],
                    "is_fallback": False,
                    "reason": (
                        f"强制提取{target_region['level_name']}，"
                        f"根据{source['name']}上级关系返回{target_region['name']}"
                    ),
                }
                return result

        source["is_fallback"] = True
        source["reason"] = (
            f"强制提取失败，无法从{source['level_name']}向下推断具体区县，"
            f"保留{source['name']}"
        )
        return source

    def _choose_best(self, candidates, target_level):
        candidates.sort(key=lambda c: (c["level"] != target_level, c["start"]))
        best = candidates[0]
        best["reason"] = f"成功提取{best['level_name']}地区：{best['name']}"
        return best

    def select_by_priority(self, candidates, target_level):
        level_name_map = {
            1: "省级", 2: "市级", 3: "区县级", 4: "乡镇街道级", 5: "村社区级"
        }
        target_level_name = level_name_map.get(target_level, "目标级别")

        exact = [c for c in candidates if c["level"] == target_level]
        if exact:
            return self._choose_best(exact, target_level)

        upper = [c for c in candidates if c["level"] < target_level]
        if upper:
            best = max(upper, key=lambda c: c["level"])
            best["is_fallback"] = True
            best["reason"] = (
                f"未找到{target_level_name}级地区，降级为{best['level_name']}：{best['name']}"
            )
            return best

        lower = [c for c in candidates if c["level"] > target_level]
        if lower:
            best = self._choose_most_specific(lower)
            best["is_fallback"] = True
            best["reason"] = (
                f"未找到{target_level_name}级地区，已使用更具体匹配：{best['name']}"
            )
            return best

        best = self._choose_most_specific(candidates)
        if best is not None:
            best["is_fallback"] = True
            best["reason"] = f"未找到目标层级，使用最佳匹配：{best['name']}"
        return best

    def _choose_most_specific(self, candidates):
        if not candidates:
            return None
        candidates.sort(key=lambda c: (c["level"], c["start"]), reverse=False)
        best = max(candidates, key=lambda c: c["level"])
        return best

    def extract(self, filename, mode, target_level):
        cache_key = (filename, mode, target_level)
        if ENABLE_EXTRACT_CACHE and cache_key in self.extract_cache:
            return self.extract_cache[cache_key]

        clean_text = self.normalize_filename_cached(filename)
        raw_candidates = self.match_regions(clean_text)
        candidates = self.filter_invalid_candidates(raw_candidates)

        level_name_map = {
            1: "省级", 2: "市级", 3: "区县级", 4: "乡镇街道级", 5: "村社区级"
        }

        if not candidates:
            result = {
                "success": True,
                "name": clean_text if clean_text else Path(filename).stem,
                "display_name": clean_text if clean_text else Path(filename).stem,
                "matched_text": "",
                "level": 0,
                "level_name": "未知",
                "target_level": target_level,
                "target_level_name": level_name_map.get(target_level, ""),
                "mode": mode,
                "source_region": "",
                "is_fallback": True,
                "reason": f"地区无法识别，已使用清洗后的文件名兜底：{clean_text}",
            }
        else:
            target_level_name = level_name_map.get(target_level, "")
            if mode == "priority":
                selected = self.select_by_priority(candidates, target_level)
            else:
                selected = self.select_by_force(candidates, target_level)

            result = {
                "success": True,
                "name": selected["name"],
                "display_name": selected.get("display_name", selected["name"]),
                "matched_text": selected.get("matched_text", ""),
                "level": selected["level"],
                "level_name": selected.get("level_name", ""),
                "target_level": target_level,
                "target_level_name": target_level_name,
                "mode": mode,
                "source_region": selected.get("source_region", ""),
                "is_fallback": selected.get("is_fallback", False),
                "reason": selected.get("reason", ""),
            }

            stem = Path(filename).stem
            region_obj = selected.get("region")
            if region_obj and result["name"] != region_obj["name"] and region_obj["name"] in stem:
                result["name"] = region_obj["name"]
                result["display_name"] = region_obj["name"]

        if ENABLE_EXTRACT_CACHE:
            self.extract_cache[cache_key] = result
        return result
