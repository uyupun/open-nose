"""NSGA-II(pymoo)による拡張ブリッジ型フレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/dilator/evaluation.py)をpymooの
Problemでラップし、FrameParamsの4設計変数を探索してパレートフロントを
求める。可視化・結果表示はcommons/report.py側の責務とし、このファイルは
実行(FrameProblemの定義とminimize()の呼び出し)だけを持つ
(earrings/spiral.optimize.pyと同じ構成)。

## 目的関数の符号

pymooは最小化のみを扱う。extension_force・inconspicuousnessは最大化
したい目的なので、OBJ_SIGN([-1, 1, -1])を使い、pain以外の符号を反転する。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(いずれも正の値であること)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(GAを実際に動かしながら見直す前提の暫定値。
scripts/dilator/frame_model.pyのモジュールdocstring参照):

- natural_radius: 既定のNoseParamsでの装着後の実際の曲率半径
  (bridge_curvature、実測約10.5mm)に対し、curvature_margin
  (_MIN_CURVATURE_RATIO=1.2倍)を満たす下限(約12.6mm)の少し外側を
  下限(15.0mm)にした。上限100.0mmは、これ以上平らにしても
  deflection(1/actual_radius - 1/natural_radius)の増分が小さくなり
  (1/natural_radiusが0に近づくため)、実質的な効果が頭打ちになる
  水準の暫定値
- bridge_thickness: earrings.optimize.pyのring_thicknessと同じ範囲
  (下限0.8mm、上限2.5mm、実際の鼻ピアスの線材の太さに近づけるため)
- stem_thickness: earrings/spiral.optimize.pyのstem_thicknessと同じ
  根拠・同じ範囲(下限0.5mm、上限2.0mm)
- stem_length: earrings/spiral.optimize.pyのstem_lengthと同じ根拠
  (下限6.0mmは鼻栓の下部から刺さる分の余裕を見た最低限の長さ、上限
  16.0mmは鼻栓の奥の端を突き抜ける境界の少し外側)
"""

import argparse
import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/dilator/xxx.py`で
# 実行するとsys.path[0]はscripts/dilator/になり、commons/dilatorパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: E402
from pymoo.core.problem import Problem  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402

from commons.nose_model import NoseParams  # noqa: E402
from commons.plug_model import PlugParams  # noqa: E402
from commons.report import SortKeys, plot_evolution, print_summary  # noqa: E402
from dilator.evaluation import constraint_values, evaluate_frame  # noqa: E402
from dilator.export_model import OUTPUT_DIR  # noqa: E402
from dilator.frame_model import FrameParams, validate_target_reach  # noqa: E402

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("natural_radius", 15.0, 100.0),
    ("bridge_thickness", 0.8, 2.5),
    ("stem_thickness", 0.5, 2.0),
    ("stem_length", 6.0, 16.0),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(extension_force, pain, inconspicuousness)の符号。pymooは最小化のみ
# 扱うため、最大化したいextension_force・inconspicuousnessだけ反転する
# (モジュールdocstring参照)
OBJ_SIGN = np.array([-1.0, 1.0, -1.0])

# 目的の表示名(グラフの軸ラベル)。extension_force, pain, inconspicuousness
# の順で固定(FrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = [
    "extension_force (拡張力, 既定=1, 最大化)",
    "pain (圧力 = 拡張力/接触面積, 最小化)",
    "inconspicuousness (目立たなさ = -突き出し量 mm, 最大化)",
]
# print_summaryの並べ替え指定: 目的の名前 → (列番号, 大きい順か)。
# OBJ_SIGN・_OBJ_LABELSと同じ順序・向き
_SORT_KEYS: SortKeys = {
    "extension_force": (0, True),
    "pain": (1, False),
    "inconspicuousness": (2, True),
}
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [
    ("nat_r", 8),
    ("bridge_t", 9),
    ("stem_t", 7),
    ("stem_len", 9),
]
_F_COLUMNS = [("force", 8), ("pain", 8), ("inconspic.", 11)]


class FrameProblem(Problem):
    """FrameParamsの4変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく(earrings/spiral.optimize.pyと同じ理由)
        validate_target_reach(plug, nose)

        super().__init__(n_var=4, n_obj=3, n_ieq_constr=6, xl=_XL, xu=_XU)
        self.plug = plug
        self.nose = nose

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        objectives = np.empty((len(x), self.n_obj))
        constraints = np.empty((len(x), self.n_ieq_constr))
        for i, row in enumerate(x):
            frame = FrameParams(**dict(zip(_VAR_NAMES, row)))
            score = evaluate_frame(frame, self.plug, self.nose)
            objectives[i] = OBJ_SIGN * [
                score.extension_force,
                score.pain,
                score.inconspicuousness,
            ]
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
        default="extension_force",
        help="パレートフロントの表をどの目的が良い順に並べるか(既定: extension_force)",
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
