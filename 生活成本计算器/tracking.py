# -*- coding: utf-8 -*-
"""tracking.py —— 长期跟踪档案数据层（纯函数，无 tkinter）。

关闭程序时可在弹窗里把"本次情况"存为一份带时间的快照；同名档案跨日期累积，
供「长期跟踪」页画变化趋势。同时生成 json（软件读）+ txt（人读）两份。

档案目录：data/tracking/<姓名>.json + <姓名>.txt
结构：{"name": ..., "snapshots": [{"time", "metrics": {5项}, "profile": {...完整档案}}]}
"""
import os
import re
import json
from datetime import datetime

import profile as P

# 文件名非法字符（Windows）：\ / : * ? " < > |
_SAFE_RE = re.compile(r'[\/\\:*?"<>|]')


def tracking_dir():
    """跟踪档案目录：data/tracking/（不存在则建）。"""
    d = os.path.join(P.app_data_dir(), "tracking")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def _safe_name(name):
    """姓名 → 安全文件名片段（去非法字符）；空则用默认。"""
    s = _SAFE_RE.sub("", (name or "").strip())
    return s if s else "我的档案"


def _path(name, ext):
    return os.path.join(tracking_dir(), _safe_name(name) + ext)


def _to_num(v, default=0):
    """entry 空串/None/异常 → default。"""
    try:
        if v in ("", None):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def metrics_from(profile, last_result=None):
    """从档案 + 处境页结果提取 5 项跟踪指标。
    last_result 优先（含处境页 override 的真实情况）；无则用档案默认参数现算。
    返回 {surplus, savings, cost_total, debt_monthly, surplus_rate}。
    """
    p = profile or {}
    if last_result and isinstance(last_result, dict) and "surplus" in last_result:
        surplus = last_result.get("surplus", 0)
        cost_total = last_result.get("cost_total", 0)
        surplus_rate = last_result.get("surplus_rate", 0)
    else:
        try:
            import calc_engine as E
            r = E.compute_current_situation(
                age=p.get("age", 30),
                wage_pretax=_to_num(p.get("wage"), 8000),
                tier=p.get("tier", "三线"),
                housing=p.get("housing", "合租单间"),
                food_level=p.get("food", "普通"),
                has_car=p.get("has_car", False),
                insurance_mode=p.get("insurance", "在职（单位缴）"),
                num_children=p.get("num_children", 0),
                support_elderly=p.get("support_elderly", False),
                support_family_monthly=_to_num(p.get("support_family")),
            )
            surplus = r.get("surplus", 0)
            cost_total = r.get("cost_total", 0)
            surplus_rate = r.get("surplus_rate", 0)
        except Exception:
            surplus = cost_total = surplus_rate = 0
    savings = _to_num(p.get("savings"))
    debt_monthly = _to_num(p.get("mortgage_monthly")) + _to_num(p.get("car_loan_monthly"))
    return {
        "surplus": round(surplus),
        "savings": round(savings),
        "cost_total": round(cost_total),
        "debt_monthly": round(debt_monthly),
        "surplus_rate": round(surplus_rate, 1),
    }


def load_track(name):
    """读取某档案 {"name", "snapshots"}；不存在或损坏返回空。"""
    path = _path(name, ".json")
    if not os.path.exists(path):
        return {"name": name, "snapshots": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"name": name, "snapshots": []}


def list_tracks():
    """列出所有档案名（按文件名，去 .json），按名排序。"""
    d = tracking_dir()
    try:
        return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))
    except OSError:
        return []


def render_txt(name, snapshots):
    """生成人读文本档案（标题 + 逐条 5 项数值）。"""
    lines = [f"长期跟踪档案 · {name}", "=" * 40]
    if not snapshots:
        lines.append("（暂无记录）")
    for s in snapshots:
        m = s.get("metrics", {})
        sp = m.get("surplus", 0)
        sp_s = f"{sp:+,.0f}" if sp else "0"
        lines += [
            "",
            s.get("time", ""),
            f"  月结余: {sp_s} 元    存款: {m.get('savings', 0):,.0f} 元"
            f"    月度成本: {m.get('cost_total', 0):,.0f} 元",
            f"  月负债: {m.get('debt_monthly', 0):,.0f} 元    结余率: {m.get('surplus_rate', 0):.0f}%",
        ]
    lines += ["", "=" * 40, f"共 {len(snapshots)} 次记录"]
    return "\n".join(lines)


def _write_txt(name, snapshots):
    try:
        with open(_path(name, ".txt"), "w", encoding="utf-8") as f:
            f.write(render_txt(name, snapshots))
    except OSError:
        pass


def save_snapshot(name, profile, metrics, when=None):
    """追加一条快照到 <name>.json（同名累积），并整份重写 <name>.txt。失败静默。

    when: 可选 datetime（测试用，默认当前时间）。
    """
    data = load_track(name)
    data["name"] = name
    data.setdefault("snapshots", []).append({
        "time": (when or datetime.now()).strftime("%Y-%m-%d %H:%M"),
        "metrics": metrics,
        "profile": profile,
    })
    try:
        with open(_path(name, ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        return
    _write_txt(name, data["snapshots"])


def delete_track(name):
    """删除某档案的 json + txt。"""
    for ext in (".json", ".txt"):
        try:
            os.remove(_path(name, ext))
        except OSError:
            pass
