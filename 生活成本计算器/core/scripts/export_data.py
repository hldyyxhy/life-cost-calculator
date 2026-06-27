# -*- coding: utf-8 -*-
"""
export_data.py —— 把 Python 数据模块的常量导出为 JSON（阶段0 数据导出）

输出到 core/src/data/*.json，供 TS 核心读取。机械导出，零逻辑翻译。

转换约定（Python json.dumps 默认即满足，这里显式说明）：
    tuple           → JSON array
    int dict key    → 字符串键（如 AGE_STAGE 的 0/3/... → "0"/"3"）
    None            → null
    float('inf')    → Infinity（非标准 JSON，但 TS/JS 的 JSON.parse 原生支持）
    衍生常量(CITY_TO_TIER/HOUSE_PURCHASE/CITY_NAMES) → 直接导 import 后的运行时值，TS 不重算

用法：
    cd core && python scripts/export_data.py
"""
import sys
import json
import hashlib
import datetime
import math
import types
from pathlib import Path

# 定位路径：本文件在 core/scripts/export_data.py
CORE_ROOT = Path(__file__).resolve().parents[1]          # core/
PROJECT_ROOT = Path(__file__).resolve().parents[2]        # 生活成本计算器/
sys.path.insert(0, str(PROJECT_ROOT))

import cost_data
import rights_data
import medical_data
import relief_data

DATA_DIR = CORE_ROOT / "src" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 各模块要导出的常量：取所有「全大写、非下划线开头」的顶层变量（数据常量），
# 自动覆盖派生常量（CITY_TO_TIER / HOUSE_PURCHASE / CITY_NAMES 等运行时已构建好）。
# 小写的函数（city_factor 等）天然被排除，留待 TS 端翻译成函数。
MODULES = [
    ("cost", cost_data),
    ("rights", rights_data),
    ("medical", medical_data),
    ("relief", relief_data),
]

# 显式排除个别不适合直接导出的全大写符号（目前无）
EXCLUDE = set()


def pick_constants(mod):
    """取模块里所有全大写、非下划线开头、非模块对象的顶层常量。"""
    out = {}
    for key, val in vars(mod).items():
        if key.startswith("_"):
            continue
        if key in EXCLUDE:
            continue
        if not key.isupper():          # 排除小写函数、混合大小写
            continue
        if callable(val):              # 排除类/函数对象（保险）
            continue
        if isinstance(val, types.ModuleType):  # 排除 import 别名（如 medical_data 里的 D/R）
            continue
        out[key] = val
    return out


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize(obj):
    """递归把 float('inf')/-inf/nan 转为 None（JSON null）。
    tsc 的 resolveJsonModule 不支持 Infinity 字面量，故 dump 成 null，
    TS 端用 `?? Infinity` 还原（见 data/cost.ts 的 TAX_BRACKETS）。
    顺带统一 tuple→list、数字键→字符串键。"""
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {(str(k) if isinstance(k, (int, float)) else k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(x) for x in obj]
    return obj


def write_json(name, obj):
    path = DATA_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        # allow_nan=False：sanitize 已把 inf→None，若仍有残留会报错（暴露问题）
        json.dump(sanitize(obj), f, ensure_ascii=False, indent=2, allow_nan=False)
    return path


def main():
    source_md5 = {}
    counts = {}
    for name, mod in MODULES:
        consts = pick_constants(mod)
        write_json(name, consts)
        counts[name] = len(consts)
        # 源文件 md5（用于 _meta 追溯）
        src = PROJECT_ROOT / f"{mod.__name__}.py"
        if src.exists():
            source_md5[mod.__name__] = md5_of(src)

    # _meta.json：生成时间 / Python 版本 / 源文件 md5
    meta = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version.split()[0],
        "conventions": {
            "tuple_to_array": True,
            "int_key_to_string": True,
            "none_to_null": True,
            "inf_to_infinity": "float('inf') 写为 Infinity（非标准 JSON，TS JSON.parse 支持）",
            "derived_constants": "CITY_TO_TIER/HOUSE_PURCHASE/CITY_NAMES 等导运行时值",
        },
        "source_md5": source_md5,
        "constant_counts": counts,
    }
    write_json("_meta", meta)

    # 打印核对信息
    print(f"数据导出完成 → {DATA_DIR}")
    for name, mod in MODULES:
        consts = pick_constants(mod)
        print(f"  {name}.json: {len(consts)} 个常量")
        # 抽样：打印 3 个标量/小常量便于人工核对
        sample = []
        for k, v in list(consts.items())[:3]:
            vs = json.dumps(v, ensure_ascii=False, default=str)
            if len(vs) > 60:
                vs = vs[:57] + "..."
            sample.append(f"{k}={vs}")
        print(f"    抽样: {'; '.join(sample)}")
    print(f"  _meta.json: 生成时间 {meta['generated_at']}")

    # 重点核对：situation 链路依赖的几个常量
    print("\n=== situation 链路关键常量核对 ===")
    cd = pick_constants(cost_data)
    print(f"  COST_FACTOR = {cd['COST_FACTOR']}")
    print(f"  TAX_THRESHOLD = {cd['TAX_THRESHOLD']}")
    print(f"  TAX_BRACKETS 末档 = {cd['TAX_BRACKETS'][-1]}  (upper=Infinity?)")
    print(f"  HOUSE_PURCHASE['三线'] = {cd['HOUSE_PURCHASE']['三线']}")
    print(f"  CITY_TO_TIER 城市数 = {len(cd['CITY_TO_TIER'])}  (台州={cd['CITY_TO_TIER'].get('台州')})")


if __name__ == "__main__":
    main()
