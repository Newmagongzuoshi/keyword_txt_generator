"""贵州地区提取单元测试"""
import sys
from pathlib import Path
from region_db import RegionDatabase
from region_extractor import RegionExtractor

TEST_ENTRIES = [
    # (输入文本, 期望提取)
    ("贵州高价回收废品", "贵州"),
    ("贵阳高价回收废品", "贵阳"),
    ("贵阳南明区高价回收废品", "南明区"),
    ("贵阳云岩区高价回收废品", "云岩区"),
    ("贵阳花溪区高价回收废品", "花溪区"),
    ("贵阳乌当区高价回收废品", "乌当区"),
    ("贵阳白云区高价回收废品", "白云区"),
    ("贵阳观山湖高价回收废品", "观山湖"),
    ("贵阳开阳县高价回收废品", "开阳县"),
    ("贵阳息烽县高价回收废品", "息烽县"),
    ("贵阳修文县高价回收废品", "修文县"),
    ("清镇高价回收废品", "清镇"),
    ("六盘水高价回收废品", "六盘水"),
    ("六盘水钟山区高价回收废品", "钟山区"),
    ("六盘水六枝高价回收废品", "六枝"),
    ("六盘水水城区高价回收废品", "水城区"),
    ("六盘水盘州市高价回收废品", "盘州市"),
    ("遵义高价回收废品", "遵义"),
    ("遵义红花岗高价回收废品", "红花岗"),
    ("遵义汇川区高价回收废品", "汇川区"),
    ("遵义播州区高价回收废品", "播州区"),
    ("遵义桐梓县高价回收废品", "桐梓县"),
    ("遵义绥阳县高价回收废品", "绥阳县"),
    ("遵义正安县高价回收废品", "正安县"),
    ("遵义道真县高价回收废品", "道真县"),
    ("遵义务川县高价回收废品", "务川县"),
    ("遵义凤冈县高价回收废品", "凤冈县"),
    ("遵义湄潭县高价回收废品", "湄潭县"),
    ("遵义余庆县高价回收废品", "余庆县"),
    ("遵义习水县高价回收废品", "习水县"),
    ("遵义赤水市高价回收废品", "赤水市"),
    ("遵义仁怀市高价回收废品", "仁怀市"),
    ("安顺高价回收废品", "安顺"),
    ("安顺西秀区高价回收废品", "西秀区"),
    ("安顺平坝区高价回收废品", "平坝区"),
    ("安顺普定县高价回收废品", "普定县"),
    ("安顺镇宁县高价回收废品", "镇宁县"),
    ("安顺关岭县高价回收废品", "关岭县"),
    ("安顺紫云县高价回收废品", "紫云县"),
    ("毕节高价回收废品", "毕节"),
    ("毕节七星关高价回收废品", "七星关"),
    ("毕节大方县高价回收废品", "大方县"),
    ("毕节金沙县高价回收废品", "金沙县"),
    ("毕节织金县高价回收废品", "织金县"),
    ("毕节纳雍县高价回收废品", "纳雍县"),
    ("毕节威宁县高价回收废品", "威宁县"),
    ("毕节赫章县高价回收废品", "赫章县"),
    ("毕节黔西市高价回收废品", "黔西市"),
    ("铜仁高价回收废品", "铜仁"),
    ("铜仁碧江区高价回收废品", "碧江区"),
    ("铜仁万山区高价回收废品", "万山区"),
    ("铜仁江口县高价回收废品", "江口县"),
    ("铜仁玉屏县高价回收废品", "玉屏县"),
    ("铜仁石阡县高价回收废品", "石阡县"),
    ("铜仁思南县高价回收废品", "思南县"),
    ("铜仁印江县高价回收废品", "印江县"),
    ("铜仁德江县高价回收废品", "德江县"),
    ("铜仁沿河县高价回收废品", "沿河县"),
    ("铜仁松桃县高价回收废品", "松桃县"),
    ("兴义市高价回收废品", "兴义市"),
    ("兴仁市高价回收废品", "兴仁市"),
    ("普安县高价回收废品", "普安县"),
    ("晴隆县高价回收废品", "晴隆县"),
    ("贞丰县高价回收废品", "贞丰县"),
    ("望谟县高价回收废品", "望谟县"),
    ("册亨县高价回收废品", "册亨县"),
    ("安龙县高价回收废品", "安龙县"),
    ("凯里市高价回收废品", "凯里市"),
    ("黄平县高价回收废品", "黄平县"),
    ("施秉县高价回收废品", "施秉县"),
    ("三穗县高价回收废品", "三穗县"),
    ("镇远县高价回收废品", "镇远县"),
    ("岑巩县高价回收废品", "岑巩县"),
    ("天柱县高价回收废品", "天柱县"),
    ("锦屏县高价回收废品", "锦屏县"),
    ("剑河县高价回收废品", "剑河县"),
    ("台江县高价回收废品", "台江县"),
    ("黎平县高价回收废品", "黎平县"),
    ("榕江县高价回收废品", "榕江县"),
    ("从江县高价回收废品", "从江县"),
    ("雷山县高价回收废品", "雷山县"),
    ("麻江县高价回收废品", "麻江县"),
    ("丹寨县高价回收废品", "丹寨县"),
    ("都匀市高价回收废品", "都匀市"),
    ("福泉市高价回收废品", "福泉市"),
    ("荔波县高价回收废品", "荔波县"),
    ("贵定县高价回收废品", "贵定县"),
    ("瓮安县高价回收废品", "瓮安县"),
    ("独山县高价回收废品", "独山县"),
    ("平塘县高价回收废品", "平塘县"),
    ("罗甸县高价回收废品", "罗甸县"),
    ("长顺县高价回收废品", "长顺县"),
    ("龙里县高价回收废品", "龙里县"),
    ("惠水县高价回收废品", "惠水县"),
    ("三都县高价回收废品", "三都县"),
]


def load_extractor():
    db_path = Path(__file__).parent / "region_db.json"
    db = RegionDatabase.load(db_path)
    return RegionExtractor.load(db)


def build_full_path(result):
    region = result.get("region")
    if not region:
        return result["name"]
    chain = region.get("parent_chain", [])
    parts = []
    for p in chain:
        pname = p.get("name", p.get("short_name", ""))
        if pname and pname not in parts:
            parts.append(pname)
    cur_name = region.get("name", result["name"])
    if cur_name and cur_name not in parts:
        parts.append(cur_name)
    return "".join(parts)


def main():
    extractor = load_extractor()
    total = 0
    passed = 0
    failed = 0
    failures = []

    for text, expected in TEST_ENTRIES:
        total += 1
        filename = f"{text}.mp4"
        result = extractor.extract(filename, "lowest", 3)
        extracted = result["name"]
        full_path = build_full_path(result)
        fallback = result.get("is_fallback", False)

        ok = extracted == expected
        if ok:
            passed += 1
            status = "OK"
        else:
            failed += 1
            status = "FAIL"
            failures.append({
                "text": text,
                "expected": expected,
                "extracted": extracted,
                "full_path": full_path,
                "fallback": fallback,
            })

        flag = " [兜底]" if fallback else ""
        print(f"  {status}  {text}  →  {extracted}  ({full_path}){flag}")

    print()
    print(f"{'='*60}")
    print(f"总计: {total}  通过: {passed}  失败: {failed}  通过率: {passed/total*100:.1f}%")

    if failures:
        print()
        print(f"{'='*60}")
        print("失败详情:")
        for f in failures:
            fb = " [兜底]" if f["fallback"] else ""
            print(f"  输入: {f['text']}")
            print(f"  期望: {f['expected']}  实际: {f['extracted']}{fb}")
            print(f"  完整路径: {f['full_path']}")
            print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
