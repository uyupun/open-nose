"""NSGA-II(pymoo)によるゼンマイ型フレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/spiral/evaluation.py)をpymooの
Problemでラップし、FrameParamsの5設計変数を探索してパレートフロントを
求める。可視化・結果表示はcommons/report.py側の責務とし、このファイルは
実行(FrameProblemの定義とminimize()の呼び出し)だけを持つ
(earrings/optimize.pyと同じ構成)。

## 目的関数の符号

pymooは最小化のみを扱う。visibility・turnsは最大化したい目的なので、
OBJ_SIGN([-1, 1, -1])を使い、weight以外の符号を反転する。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(いずれも正の値であること)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(GAを実際に動かしながら見直す前提の暫定値。
scripts/spiral/frame_model.pyのモジュールdocstring「幾何」参照):

- turns: 下限1.0(1周未満では「渦巻き」に見えない)。上限3.5は、
  turns・start_radius・wire_thicknessが大きいほど経路長(=weight)が
  増えるため、あまり大きくすると重さが支配的になり実用に耐えない
  という考え方の暫定値
- start_radius: 下限3.0mm(渦の外径が小さすぎると見た目の主張が弱い)。
  上限8.0mmは、earrings.optimize.pyのring_radius上限と同じ理由
  (実物の鼻ピアスに近いサイズ感)
- end_radius: 下限0.5mm(渦の中心が尖りすぎない最小限)。上限3.0mmは
  start_radius(上限8.0)に対してradius_order_margin
  (_MIN_RADIUS_DROP=1.0mm差)を満たす余地を残すための暫定値
- wire_thickness: 下限0.5mm(針のように細すぎない程度)。上限2.0mmは
  earrings.optimize.pyのstem_thicknessの上限と同じ考え方
- stem_length: earrings.optimize.pyのstem_lengthと同じ根拠(下限6.0mmは
  鼻栓の下部から刺さる分の余裕を見た最低限の長さ、上限16.0mmは鼻栓の
  奥の端を突き抜ける境界の少し外側)
"""

import argparse
import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/spiral/xxx.py`で
# 実行するとsys.path[0]はscripts/spiral/になり、commons/spiralパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: E402
from pymoo.core.problem import Problem  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402

from commons.nose_model import NoseParams, build_nose_body  # noqa: E402
from commons.plug_model import PlugParams  # noqa: E402
from commons.report import SortKeys, plot_evolution, print_summary  # noqa: E402
from spiral.evaluation import constraint_values, evaluate_frame  # noqa: E402
from spiral.export_model import OUTPUT_DIR  # noqa: E402
from spiral.frame_model import (  # noqa: E402
    FrameParams,
    validate_anchor_height,
    validate_target_reach,
)

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("turns", 1.0, 3.5),
    ("start_radius", 3.0, 8.0),
    ("end_radius", 0.5, 3.0),
    ("wire_thickness", 0.5, 2.0),
    ("stem_length", 6.0, 16.0),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(visibility, weight, turns)の符号。pymooは最小化のみ扱うため、
# 最大化したいvisibility・turnsだけ反転する(モジュールdocstring参照)
OBJ_SIGN = np.array([-1.0, 1.0, -1.0])

# 目的の表示名(グラフの軸ラベル)。visibility, weight, turnsの順で固定
# (FrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = [
    "visibility (コイルの突き出し mm, 最大化)",
    "weight (コイル+ステムの体積 mm^3, 最小化)",
    "turns (渦の巻き数, 最大化)",
]
# print_summaryの並べ替え指定: 目的の名前 → (列番号, 大きい順か)。
# OBJ_SIGN・_OBJ_LABELSと同じ順序・向き
_SORT_KEYS: SortKeys = {
    "visibility": (0, True),
    "weight": (1, False),
    "turns": (2, True),
}
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [
    ("turns", 7),
    ("start_r", 8),
    ("end_r", 7),
    ("wire_t", 7),
    ("stem_len", 9),
]
_F_COLUMNS = [("visibility", 11), ("weight", 9), ("turns", 7)]


class FrameProblem(Problem):
    """FrameParamsの5変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく(earrings/optimize.pyと同じ理由)
        validate_target_reach(plug, nose)
        validate_anchor_height(nose, build_nose_body(nose))

        super().__init__(n_var=5, n_obj=3, n_ieq_constr=5, xl=_XL, xu=_XU)
        self.plug = plug
        self.nose = nose

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        objectives = np.empty((len(x), self.n_obj))
        constraints = np.empty((len(x), self.n_ieq_constr))
        for i, row in enumerate(x):
            frame = FrameParams(**dict(zip(_VAR_NAMES, row)))
            score = evaluate_frame(frame, self.plug, self.nose)
            objectives[i] = OBJ_SIGN * [score.visibility, score.weight, score.turns]
            constraints[i] = constraint_values(score)
        out["F"] = objectives
        out["G"] = constraints


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pop-size", type=int, default=50)
    parser.add_argument("--n-gen", type=int, default=60)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--sort-by",
        choices=sorted(_SORT_KEYS),
        default="visibility",
        help="パレートフロントの表をどの目的が良い順に並べるか(既定: visibility)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    problem = FrameProblem(PlugParams(), NoseParams())
    algorithm = NSGA2(pop_size=args.pop_size)
    res = minimize(
        problem,
        algorithm,
        ("n_gen", args.n_gen),
        seed=args.seed,
        save_history=True,
        verbose=True,
    )

    generations = [OBJ_SIGN * h.pop.get("F") for h in res.history]
    pareto_f = OBJ_SIGN * res.F
    n_feasible = int(res.algorithm.pop.get("feasible").sum())
    n_total = len(res.algorithm.pop)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    evolution_path = args.output_dir / "evolution.png"
    plot_evolution(generations, evolution_path, _OBJ_LABELS)
    print_summary(
        res.X, pareto_f, n_feasible, n_total, _X_COLUMNS, _F_COLUMNS, _SORT_KEYS, args.sort_by
    )
    print(f"\n画像を出力: {evolution_path}")


if __name__ == "__main__":
    main()
