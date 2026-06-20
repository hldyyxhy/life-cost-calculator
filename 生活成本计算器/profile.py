# -*- coding: utf-8 -*-
"""
profile.py —— 用户个人档案数据模型

设计目的：
    把"我是谁、挣多少、怎么活、养谁、欠多少"这些个人情况集中成一份档案，
    供各计算模块（处境/对比/三座山）读取，避免每个页面重复填写。
    本轮先独立存在（可填、可保存、可加载），模块如何调用后续再接。

档案结构（6 组）：
    basic       本人基础（年龄、城市、健康）
    income      收入与社保（本人税前月薪、社保类型、是否有副业及其收入）
    living      居住与生活方式（住房、饮食、交通、给老家生活费）
    partner     伴侣（是否有、伴侣税前月薪、伴侣社保）—— 双收入视角
    family      家庭负担（子女数、子女年龄段、赡养老人、专项扣除）
    finance     负债与资产（房贷月供、车贷月供、现有存款、月人情娱乐）—— 抗风险用

序列化：to_dict() / from_dict() 全是基础类型，可直接 json.dump。
默认值：DEFAULT_PROFILE 提供一份空档案的合理默认。
"""

import json
import os
import sys

import cost_data as D

# 档案结构定义：键 -> (默认值, 中文标签, 控件类型, 说明/选项)
# 控件类型：spin(数字步进) / entry(文本数字) / combo(下拉) / check(勾选)
# combo 的 options 放在说明字段（list）
FIELD_DEFS = {
    "basic": [
        ("age", 30, "年龄", "spin", (16, 80)),
        ("city", "", "所在城市", "entry", "如：北京、成都、长沙…输入后自动匹配城市等级"),
        ("tier", "三线", "城市等级", "combo", ["一线", "新一线", "二线", "三线", "四线", "五线"]),
        ("health", "健康（无慢性病）", "健康状况", "combo",
         ["健康（无慢性病）", "有慢性病（需长期用药）", "需定期就医"]),
    ],
    "income": [
        ("wage", "", "本人税前月薪（元）", "entry", "留空则用本城市典型月薪"),
        ("insurance", "在职（单位缴）", "社保类型", "combo",
         ["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"]),
        ("has_side_income", False, "有副业/兼职收入", "check", None),
        ("side_income", "", "副业月收入（元）", "entry", "已扣除税费后的到手估算"),
    ],
    "living": [
        ("housing", "合租单间", "住房方式", "combo",
         ["合租单间", "一居室整租", "已购房（还月供）", "与父母同住（免租）"]),
        ("food", "普通", "饮食档次", "combo", ["节俭", "普通", "宽裕"]),
        ("has_car", False, "养车", "check", None),
        ("support_family", "", "给老家生活费（元/月）", "entry", "0 或留空表示不给"),
    ],
    "partner": [
        ("has_partner", False, "有伴侣/配偶", "check", None),
        ("partner_wage", "", "伴侣税前月薪（元）", "entry", "留空则用本城市典型月薪"),
        ("partner_insurance", "在职（单位缴）", "伴侣社保", "combo",
         ["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"]),
    ],
    "family": [
        ("num_children", 0, "子女数量", "spin", (0, 6)),
        ("child_baby", 0, "　3岁以下（婴幼儿）几人", "spin", (0, 6)),
        ("child_kg", 0, "　幼儿园（3-6岁）几人", "spin", (0, 6)),
        ("child_school", 0, "　中小学（6-18岁）几人", "spin", (0, 6)),
        ("child_uni", 0, "　大学在读（18岁+）几人", "spin", (0, 6)),
        ("support_elderly", False, "赡养老人（个税专项扣除）", "check", None),
        ("has_housing_deduction", False, "有住房租金/房贷利息扣除", "check", None),
        ("has_continuing_education", False, "本人继续教育（+400元/月）", "check", None),
    ],
    "finance": [
        ("mortgage_monthly", "", "房贷月供（元，另计/非默认）", "entry",
         "若上面选了'已购房'，这里可覆盖默认月供；留空用默认"),
        ("car_loan_monthly", "", "车贷月供（元）", "entry", "0 或留空"),
        ("savings", "", "现有存款/应急金（元）", "entry", "用于估算失业能撑多久"),
        ("social_expense", "", "人情/娱乐月支出（元）", "entry", "红白喜事、聚餐等，0 或留空"),
    ],
}

# 组标题（中文）
GROUP_TITLES = {
    "basic": "一、本人基础",
    "income": "二、收入与社保",
    "living": "三、居住与生活方式",
    "partner": "四、伴侣（双收入）",
    "family": "五、家庭负担",
    "finance": "六、负债与资产（抗风险）",
}


# 首次填写向导的步骤（字段 key 对齐 FIELD_DEFS；show_if 为 None 总显示，
# 否则按已答字典 a 决定该字段是否出现——实现"没伴侣就不问伴侣薪资"式的智能跳过）
WIZARD_STEPS = [
    {"title": "先认识一下", "fields": [
        {"key": "age"}, {"key": "city"},
    ]},
    {"title": "你的收入", "fields": [
        {"key": "wage"}, {"key": "insurance"}, {"key": "has_side_income"},
        {"key": "side_income", "show_if": lambda a: a.get("has_side_income")},
    ]},
    {"title": "住和吃、出行", "fields": [
        {"key": "housing"}, {"key": "food"}, {"key": "has_car"},
    ]},
    {"title": "成家了吗", "fields": [
        {"key": "has_partner"},
        {"key": "partner_wage",      "show_if": lambda a: a.get("has_partner")},
        {"key": "partner_insurance", "show_if": lambda a: a.get("has_partner")},
    ]},
    {"title": "孩子和老人", "fields": [
        {"key": "num_children"},
        {"key": "child_baby",   "show_if": lambda a: (a.get("num_children") or 0) > 0},
        {"key": "child_kg",     "show_if": lambda a: (a.get("num_children") or 0) > 0},
        {"key": "child_school", "show_if": lambda a: (a.get("num_children") or 0) > 0},
        {"key": "child_uni",    "show_if": lambda a: (a.get("num_children") or 0) > 0},
        {"key": "support_elderly"},
    ]},
    {"title": "负债和存款", "fields": [
        {"key": "mortgage_monthly"},
        {"key": "car_loan_monthly", "show_if": lambda a: a.get("has_car")},
        {"key": "savings"}, {"key": "social_expense"},
    ]},
    {"title": "其他（都可留空）", "fields": [
        {"key": "health"}, {"key": "support_family"},
        {"key": "has_housing_deduction"}, {"key": "has_continuing_education"},
    ]},
]


def default_profile():
    """生成一份默认（空）档案 dict。"""
    profile = {}
    for group, fields in FIELD_DEFS.items():
        for key, default, *_ in fields:
            profile[key] = default
    return profile


def auto_map_tier(profile):
    """
    根据 profile 中的 city 自动匹配城市等级并写入 tier 字段。
    若匹配不到则保留原 tier 不变。
    返回更新后的 profile。
    """
    city = profile.get("city", "").strip()
    if city:
        tier = D.city_to_tier(city)
        if tier:
            profile["tier"] = tier
    return profile


# 旧档案 child_age_group（单值字符串）→ 对应 child_* 段字段
_OLD_CHILD_SEG_TO_FIELD = {
    "3岁以下（婴幼儿）": "child_baby",
    "幼儿园（3-6岁）": "child_kg",
    "中小学（6-18岁）": "child_school",
    "大学在读（18岁+）": "child_uni",
}


def validate_profile(raw):
    """
    用 FIELD_DEFS 校验并补全一份档案：
    - 多出的键丢弃
    - 缺失的键用默认值补
    - 数字类（entry/spin）空字符串保留为空串（表示"未填"）
    - 旧版 child_age_group（单值）自动迁移为对应 child_* 段计数
    """
    raw = dict(raw or {})
    if "child_age_group" in raw:
        old_seg = raw.pop("child_age_group")
        n = raw.get("num_children", 0) or 0
        field = _OLD_CHILD_SEG_TO_FIELD.get(old_seg, "child_school")
        # 仅当还没填任何段计数时，才把旧段映射过去（避免覆盖已填的新数据）
        if not any(raw.get(f) for f in _OLD_CHILD_SEG_TO_FIELD.values()):
            raw[field] = n
    result = default_profile()
    all_keys = {k for fields in FIELD_DEFS.values() for (k, *_) in fields}
    for k in all_keys:
        if k in raw:
            result[k] = raw[k]
    return result


# ---------- 序列化 ----------

def to_json(profile, pretty=True):
    """档案 → JSON 字符串。"""
    indent = 2 if pretty else None
    ensure = False  # 中文不转义
    return json.dumps(profile, indent=indent, ensure_ascii=ensure)


def from_json(text):
    """JSON 字符串 → 档案（经 validate 校验补全）。"""
    data = json.loads(text)
    return validate_profile(data)


def save_to_file(profile, path):
    """保存档案到 JSON 文件。成功返回路径。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_json(profile, pretty=True))
    return path


def load_from_file(path):
    """从 JSON 文件读取档案。返回校验后的 dict。"""
    with open(path, "r", encoding="utf-8") as f:
        return from_json(f.read())


# ---------- 本地持久化（上次档案） ----------

def app_data_dir():
    """返回程序数据目录（程序同级 data/）。

    开发运行指向脚本所在目录；用 PyInstaller 打包成 exe 后指向 exe 同级目录
    （仍可写）。若该目录不可写（极端只读），退回用户家目录，避免崩溃。
    """
    if getattr(sys, "frozen", False):          # PyInstaller 打包后的 exe
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:                                       # 源码运行
        base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "data")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError:
        data_dir = os.path.join(os.path.expanduser("~"), ".生活成本计算器")
        os.makedirs(data_dir, exist_ok=True)
    return data_dir


def last_profile_path():
    """上次使用档案的固定路径（程序同级 data/last_profile.json）。"""
    return os.path.join(app_data_dir(), "last_profile.json")


def save_last_profile(profile):
    """把档案存为「上次档案」。失败静默，不阻塞用户。"""
    try:
        save_to_file(profile, last_profile_path())
    except OSError:
        pass


def load_last_profile():
    """读取「上次档案」。文件不存在或损坏返回 None（调用方走默认值）。"""
    path = last_profile_path()
    if not os.path.exists(path):
        return None
    try:
        return load_from_file(path)
    except (OSError, ValueError):
        return None


# ---------- 自检 ----------
if __name__ == "__main__":
    p = default_profile()
    print("默认档案字段数:", len(p))
    # 往返测试
    p["wage"] = 8000
    p["has_partner"] = True
    p["partner_wage"] = 7000
    js = to_json(p)
    p2 = from_json(js)
    assert p2["wage"] == 8000 and p2["has_partner"] is True
    # 缺字段补全
    p3 = from_json('{"age": 25}')
    assert p3["age"] == 25 and p3["tier"] == "三线"
    # 多余字段丢弃
    p4 = from_json('{"age": 25, "nonexistent": 999}')
    assert "nonexistent" not in p4
    print("往返/补全/丢弃 测试通过")
