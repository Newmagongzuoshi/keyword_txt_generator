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

    # 行政区划名称中可迭代剥离的后缀，按长度降序排列确保长匹配优先
    _ADMIN_SUFFIXES = sorted([
        # 行政功能词（多字）
        "自治县", "自治区", "自治州", "自治旗",
        "县级市", "地区", "特区", "林区", "矿区", "新区",
        "居委会", "村委会", "民族乡",
        "街道", "苏木",
        # 单字行政后缀
        "县", "区", "市", "镇", "乡", "村", "省", "州", "盟", "旗",
        # 常见民族名称+族（用于剥离"X族自治县"等组合）
        "壮族", "回族", "维吾尔族", "苗族", "彝族", "藏族", "蒙古族",
        "满族", "朝鲜族", "土家族", "布依族", "侗族", "瑶族", "白族",
        "土族", "哈尼族", "傣族", "黎族", "水族", "东乡族", "纳西族",
        "羌族", "仡佬族", "畲族", "拉祜族", "佤族", "傈僳族",
        "高山族", "布朗族", "撒拉族", "毛南族", "锡伯族",
        "仫佬族", "达斡尔族", "景颇族", "柯尔克孜族", "基诺族",
        "保安族", "裕固族", "京族", "塔塔尔族", "独龙族",
        "鄂伦春族", "赫哲族", "门巴族", "珞巴族", "怒族",
        "阿昌族", "普米族", "塔吉克族", "乌孜别克族", "俄罗斯族",
        "鄂温克族", "德昂族", "哈萨克族",
        # 民族名不带"族"（用于剥离"巴里坤哈萨克→巴里坤"等）
        "维吾尔", "哈萨克", "蒙古", "朝鲜", "土家", "布依", "东乡",
        "哈尼", "纳西", "仡佬", "拉祜", "傈僳", "高山", "布朗",
        "撒拉", "毛南", "锡伯", "仫佬", "达斡尔", "景颇",
        "柯尔克孜", "基诺", "保安", "裕固", "塔塔尔", "独龙",
        "鄂伦春", "赫哲", "门巴", "珞巴", "阿昌", "普米",
        "塔吉克", "乌孜别克", "俄罗斯", "鄂温克", "德昂",
        # 功能词
        "自治", "各族",
        # 单字"族"用于剥离"东乡族自治县→东乡族→东乡"
        "族",
    ], key=len, reverse=True)

    def _generate_abbreviations(self, name, short_name):
        """从地区全称和简称迭代剥离行政后缀，生成所有实用简称。

        例如 镇宁布依族苗族自治县 → 镇宁布依族苗族 → 镇宁布依族 → 镇宁
        单字后缀剥离后立即停止，避免误切核心地名（如"东乡"→"东"）。
        """
        results = set()
        for source in (name, short_name):
            current = source
            while True:
                stripped = None
                for suffix in self._ADMIN_SUFFIXES:
                    if current.endswith(suffix) and len(current) > len(suffix):
                        stripped = suffix
                        break
                if stripped is None:
                    break
                abbr = current[:-len(stripped)]
                if len(abbr) >= 2:
                    results.add(abbr)
                current = abbr
                # 剩余长度<=2时停止剥离，避免误切核心地名
                # 如"东乡"→"东"是不可接受的，但"X族乡"剥离"乡"后仍可继续剥离"族"
                if len(current) <= 2:
                    break
        return results

    def _build_trie(self):
        for region in self.region_db.regions:
            names = set()
            names.add(region["name"])
            names.add(region["short_name"])
            for alias in region.get("aliases", []):
                names.add(alias)
            # 对所有行政区划自动生成简称（迭代剥离行政后缀）
            generated = self._generate_abbreviations(region["name"], region["short_name"])
            for abbr in generated:
                if abbr not in names:
                    names.add(abbr)
            # 为长地名生成 核心简称 + 末端单字后缀 变体
            # 如"沿河土家族自治县"→"沿河县"，"六枝特区"→"六枝区"
            _SINGLE_ADMIN = ("县", "区", "市", "镇", "乡", "村", "州", "旗")
            for sfx in _SINGLE_ADMIN:
                if region["name"].endswith(sfx):
                    core = min(generated, key=len) if generated else region["short_name"]
                    variant = core + sfx
                    if variant != region["name"] and len(variant) < len(region["name"]):
                        names.add(variant)
                    break
            for name in names:
                name = name.strip()
                if name and len(name) >= 2:
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

    def _get_valid_start_positions(self, raw_matches, text_len):
        """计算文本中哪些位置是合法的匹配起始位置。

        位置 x 合法当且仅当：
        1. x == 0（文本开头），或
        2. 存在某个匹配在 x 处结束，或
        3. 没有任何匹配跨越 x（即不存在匹配 [a,b] 满足 a < x < b）

        规则 3 避免前置修饰词（如"旅游北京"）导致合法匹配被误杀。
        此方法用于在重叠裁决前过滤跨边界幻影匹配（如贵阳白云区→阳白）。
        """
        if not raw_matches:
            return set()

        valid = {0}
        match_ends = {m["end"] for m in raw_matches}
        spans = [(m["start"], m["end"]) for m in raw_matches]

        for x in range(1, text_len + 1):
            if x in match_ends:
                valid.add(x)
            else:
                spanned = any(a < x < b for (a, b) in spans)
                if not spanned:
                    valid.add(x)

        return valid

    def match_regions(self, text):
        raw_matches = self.trie.search_all_matches(text)
        if not raw_matches:
            return []

        # 预过滤：剔除起始位置不合法的跨边界幻影匹配
        valid_starts = self._get_valid_start_positions(raw_matches, len(text))
        raw_matches = [m for m in raw_matches if m["start"] in valid_starts]
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

            # 同一位置匹配到不同地区（如广州白云区/贵阳白云区），都保留
            if m_start == k_start and m_end == k_end:
                return "both"
            if m_start >= k_start and m_end <= k_end:
                return "k"  # m完全被k包含，保留k
            if k_start >= m_start and k_end <= m_end:
                return "m"  # k完全被m包含，保留m

            # 边界单字重叠（如"贵阳市"与"市西"共享"市"），不互斥
            overlap_start = max(m_start, k_start)
            overlap_end = min(m_end, k_end)
            if overlap_end - overlap_start <= 1:
                return "both"

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
                    if winner == "both":
                        continue  # 同名不同地区，都保留
                    elif winner == "m":
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

    def _count_ancestor_matches(self, candidate, all_candidates):
        """统计其他候选项中有多少个是 candidate 的后代（即 candidate 在其祖先链中）"""
        region = candidate.get("region")
        if not region:
            return 0
        rid = region["id"]
        count = 0
        for other in all_candidates:
            if other is candidate:
                continue
            other_region = other.get("region")
            if not other_region:
                continue
            for p in other_region.get("parent_chain", []):
                if p["id"] == rid:
                    count += 1
                    break
        return count

    def _build_parent_set(self, region):
        """返回 region 及其所有祖先的 id 集合"""
        ids = {region["id"]}
        for p in region.get("parent_chain", []):
            ids.add(p["id"])
        return ids

    def _check_consistency(self, candidate, all_candidates):
        """检查 candidate 与文本中其他非重叠候选者的父子关系是否一致。
        如果存在一个非重叠的更高层级候选者不在 candidate 的祖先链中，
        说明两者不匹配（如"汇川区中观镇"—中观镇不属于汇川区），返回 False。
        """
        region = candidate.get("region")
        if not region:
            return True
        parent_ids = self._build_parent_set(region)
        for other in all_candidates:
            if other is candidate:
                continue
            # 只检查位于 candidate 之前的候选者（地理前缀），允许1字边界重叠
            # candidate 之后的通常是关键词后缀（如"去北京旅游"中的"北京"），不参与校验
            if other["end"] <= candidate["start"] + 1:
                other_region = other.get("region")
                if not other_region:
                    continue
                # 如果其他候选者是我们的祖先 → 一致
                if other_region["id"] in parent_ids:
                    continue
                # 其他候选者层级更高（数字更小）且不在祖先链中 → 不一致
                if other_region["level"] < region["level"]:
                    return False
        return True

    def select_lowest(self, candidates, target_level=3):
        """智能匹配：每个文本位置选最优候选项（target 内优先），然后取全文本最具体的。
        同名多区自动选正确版本，越级隶属自动回退。
        """
        if not candidates:
            return None
        # 按位置分组
        by_pos = {}
        for c in candidates:
            pos = (c["start"], c["end"])
            if pos not in by_pos:
                by_pos[pos] = []
            by_pos[pos].append(c)
        # 每组选最优：target 内优先，祖先匹配数多优先，同条件层级更具体优先
        best_per_pos = []
        for pos, group in by_pos.items():
            in_t = [c for c in group if c["level"] <= target_level and self._check_consistency(c, candidates)]
            if in_t:
                # 优先选祖先链包含其他候选项多的（地理一致性更高）
                in_t.sort(key=lambda c: (-self._count_ancestor_matches(c, candidates), -c["level"]))
                best = in_t[0]
            else:
                consistent = [c for c in group if self._check_consistency(c, candidates)]
                if not consistent:
                    continue
                consistent.sort(key=lambda c: (-self._count_ancestor_matches(c, candidates), -c["level"]))
                best = consistent[0]
            best_per_pos.append(best)
        if not best_per_pos:
            best = min(candidates, key=lambda c: c["level"])
            best["is_fallback"] = True
            best["reason"] = f"无法确认归属关系，兜底为{best['level_name']}：{best['name']}"
            return best
        # 全文本取最具体位置
        best = max(best_per_pos, key=lambda c: c["level"])
        best["is_fallback"] = False
        best["reason"] = f"智能匹配成功提取{best['level_name']}：{best['name']}"
        return best

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
            if mode == "lowest":
                selected = self.select_lowest(candidates, target_level)
            elif mode == "priority":
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
                "region": selected.get("region"),
            }

            stem = Path(filename).stem
            region_obj = selected.get("region")
            if region_obj and result["name"] != region_obj["name"] and region_obj["name"] in stem:
                result["name"] = region_obj["name"]
                result["display_name"] = region_obj["name"]

        if ENABLE_EXTRACT_CACHE:
            self.extract_cache[cache_key] = result
        return result
