"""NSGA-II(pymoo)による水引型の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/mizuhiki/evaluation.py)をpymooの
Problemでラップし、MizuhikiParamsのうち結びの位置(高さ・小鼻の上の位置)と
紐の太さの3つを探索してパレートフロントを求める。結びの大きさは探索せず、
--knot-scaleで与える(既定は_KNOT_SCALE。後述)。出力は次の5つ(output/mizuhiki/)。

- evolution.png: 世代ごとの集団の分布推移(目的空間)
- pareto.csv: パレートフロントの全個体の設計変数・目的・制約
- candidate_presence.glb: 横顔での存在感が最も大きい候補
- candidate_frontal.glb: 正面で最も読みやすい候補
- candidate_balanced.glb: 3つの目的の釣り合いが最も良い候補(パレート
  フロントの中で、各目的を0〜1に正規化した理想点(1, 1, 1)に最も近い個体)

## 目的の符号

pymooは最小化のみを扱う。3目的(profile_presence・frontal_legibility・
tissue_grip)はいずれも最大化したいので、OBJ_SIGN([-1, -1, -1])ですべて
符号を反転する。

## 探索範囲(_SEARCH_SPACEの根拠)

結びの大きさを1.74に固定して、探索範囲からランダムに400件を評価したときの
実行可能は3%(11件)で、違反率はfront_open_margin 71%・knot_open_margin 67%・
ala_top_margin 52%・tail_low_margin 34%・inner_edge_margin 28%・
knot_on_skin_margin 24%・knot_hug_margin 22%。正面から三つ輪の穴が開くには
knot_f≧約1.0(鼻の側面の面の上)が要り、赤線(鼻の穴の中心の線)を越えない
にはknot_f≦約1.4に収める必要があるので、成り立つ範囲は狭い。刷れるかの
制約(neck・cord・bed_area)と、頬・左右の当たり(cheek・pair_gap)は、この
範囲では違反しない安全網。

- knot_y: 1.0〜4.5。小鼻の膨らみ(鼻先の底面から約7mm)の中。これより高いと
  結びの上端が小鼻の上端を越える(ala_top_margin)
- knot_f: 0.9〜1.5。1を超えると、正面を斜めに向いた鼻の側面の面の上。
  前寄りほど正面から読みやすく(frontal_legibilityとの相関+0.69)、横顔での
  存在感は減る(profile_presenceと-0.43)。ただし鼻の側面の面は平らなので、
  正面での読みやすさはknot_f≈1.3でほぼ頭打ちになり、それより内側へ寄せても
  結びの向きは変わらない。この範囲の外は、正面から三つ輪が開かない(<0.9)
  か、赤線を越える(>1.5)ものしかない
- cord_radius: 0.40〜0.55。下限は紐の直径がFDMの線2本分(0.8mm)になる値。
  上限は、帯が紐3本に見える細さ(0.55で帯の幅が約3mm)。太いほど輪がよく
  つかむが、三つ輪の穴が狭くなる

knot_scale(結びの大きさ)は探索しない。3つの目的はどれも「見えるほど良い」
ので、大きすぎることを止める力が評価関数の中になく、1.65〜1.85で探索させると
GAは上限(1.84)に張り付いた(dilatorのbridge_widthと同じ状況)。大きさは
評価関数では決められない塩梅の判断なので、ユーザー指定「(試作で刷った
候補の)1.1倍程度大きくしたい」に合わせて、刷った候補(1.585)の1.1倍(1.74)
に固定する。10%増は面積で約2割増しで、以前の「結びが主張しすぎる」という
指摘からも、これ以上は大きくしない。大きくすると三つ輪の穴が広がって
正面からも横顔からも読みやすくなるが、刷った位置のままでは頬や小鼻の外に
はみ出すので、結びを前へ出す(knot_f)こととセットで成り立つ。

tail_length(結びの端の長さ)は、どの目的ともほぼ相関がない(±0.07)ため、
探索させるとGAの中で漂うだけなので、既定値に固定している。
"""

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

# scripts/ をimportパスに加える(export_model.pyと同じ理由)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.nose_model import NoseParams, build_nose_body  # noqa: E402
from commons.report import SortKeys, plot_evolution, print_summary  # noqa: E402
from mizuhiki.evaluation import (  # noqa: E402
    CONSTRAINT_NAMES,
    OBJECTIVE_LABELS,
    constraint_values,
    evaluate_frame,
    format_score,
)
from mizuhiki.export_frame import export_candidate  # noqa: E402
from mizuhiki.export_model import OUTPUT_DIR  # noqa: E402
from mizuhiki.frame_model import MizuhikiParams  # noqa: E402

# 探索変数(名前, 下限, 上限)。根拠はモジュールdocstring参照
# 結びの大きさ(探索しない。モジュールdocstring参照)
_KNOT_SCALE = 1.74
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("knot_y", 1.0, 4.5),
    ("knot_f", 0.9, 1.5),
    ("cord_radius", 0.40, 0.55),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的の並び(OBJ_SIGN・グラフ・表で共通)。3つとも最大化なので全て反転する
_OBJECTIVES = ["profile_presence", "frontal_legibility", "tissue_grip"]
OBJ_SIGN = np.array([-1.0, -1.0, -1.0])
_SORT_KEYS: SortKeys = {name: (k, True) for k, name in enumerate(_OBJECTIVES)}
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [("knot_y", 8), ("knot_f", 8), ("cord_r", 8)]
_F_COLUMNS = [("presence", 10), ("frontal", 9), ("grip", 8)]


def _frame(row: np.ndarray, knot_scale: float) -> MizuhikiParams:
    return MizuhikiParams(knot_scale=knot_scale, **dict(zip(_VAR_NAMES, (float(v) for v in row))))


class MizuhikiProblem(Problem):
    """MizuhikiParamsの3変数を探索するpymoo Problem。鼻と結びの大きさは固定。"""

    def __init__(self, nose: NoseParams, knot_scale: float):
        super().__init__(n_var=len(_SEARCH_SPACE), n_obj=3, n_ieq_constr=len(CONSTRAINT_NAMES), xl=_XL, xu=_XU)
        self.nose = nose
        self.knot_scale = knot_scale
        self.body = build_nose_body(nose)

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        objectives = np.empty((len(x), self.n_obj))
        constraints = np.empty((len(x), self.n_ieq_constr))
        for i, row in enumerate(x):
            score = evaluate_frame(_frame(row, self.knot_scale), self.nose, self.body)
            objectives[i] = OBJ_SIGN * [getattr(score, name) for name in _OBJECTIVES]
            constraints[i] = constraint_values(score)
        out["F"] = objectives
        out["G"] = constraints


def _balanced(f: np.ndarray) -> int:
    """各目的をパレートフロントの中で0(最悪)〜1(最良)に正規化し、理想点
    (1, 1, 1)に最も近い個体の番号。"""
    low, high = f.min(axis=0), f.max(axis=0)
    normalized = (f - low) / np.where(high > low, high - low, 1.0)
    return int(np.argmin(np.linalg.norm(1.0 - normalized, axis=1)))


def _write_pareto(path: Path, x: np.ndarray, f: np.ndarray, nose: NoseParams, knot_scale: float) -> None:
    body = build_nose_body(nose)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["knot_scale", *_VAR_NAMES, *_OBJECTIVES, *CONSTRAINT_NAMES])
        for row, objectives in zip(x, f):
            score = asdict(evaluate_frame(_frame(row, knot_scale), nose, body))
            writer.writerow(
                [f"{knot_scale:.4f}"]
                + [f"{v:.4f}" for v in row]
                + [f"{v:.3f}" for v in objectives]
                + [f"{score[name]:.4f}" for name in CONSTRAINT_NAMES]
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pop-size", type=int, default=40)
    parser.add_argument("--n-gen", type=int, default=40)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--knot-scale",
        type=float,
        default=_KNOT_SCALE,
        help=f"結びの大きさ(探索しない。既定: {_KNOT_SCALE}。刷った候補1.585の1.1倍)",
    )
    parser.add_argument(
        "--sort-by",
        choices=sorted(_SORT_KEYS),
        default="profile_presence",
        help="パレートフロントの表をどの目的が良い順に並べるか(既定: profile_presence)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    nose = NoseParams()
    res = minimize(
        MizuhikiProblem(nose, args.knot_scale),
        NSGA2(pop_size=args.pop_size),
        ("n_gen", args.n_gen),
        seed=args.seed,
        save_history=True,
        verbose=True,
    )
    if res.X is None:
        raise RuntimeError("実行可能な個体が見つからなかった(探索範囲か制約の閾値を見直す)")
    x = np.atleast_2d(res.X)
    pareto_f = OBJ_SIGN * np.atleast_2d(res.F)
    generations = [OBJ_SIGN * h.pop.get("F") for h in res.history]
    n_feasible = int(res.algorithm.pop.get("feasible").sum())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_evolution(generations, OUTPUT_DIR / "evolution.png", [OBJECTIVE_LABELS[name] for name in _OBJECTIVES])
    _write_pareto(OUTPUT_DIR / "pareto.csv", x, pareto_f, nose, args.knot_scale)
    print_summary(x, pareto_f, n_feasible, len(res.algorithm.pop), _X_COLUMNS, _F_COLUMNS, _SORT_KEYS, args.sort_by)

    picks = {
        "candidate_presence": int(np.argmax(pareto_f[:, 0])),
        "candidate_frontal": int(np.argmax(pareto_f[:, 1])),
        "candidate_balanced": _balanced(pareto_f),
    }
    for name, index in picks.items():
        frame = _frame(x[index], args.knot_scale)
        print(f"\n== {name} ==")
        export_candidate(frame, name)
        print(frame)
        print(format_score(evaluate_frame(frame, nose)))
    print(f"\n画像を出力: {OUTPUT_DIR / 'evolution.png'}")
    print(f"表を出力: {OUTPUT_DIR / 'pareto.csv'}")


if __name__ == "__main__":
    main()
