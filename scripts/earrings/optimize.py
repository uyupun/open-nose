"""NSGA-II(pymoo)によるフレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/earrings/evaluation.py)をpymooのProblemで
ラップし、FrameParamsの6設計変数を探索してパレートフロントを求める。
可視化・結果表示はcommons/report.py側の責務とし、このファイルは実行
(FrameProblemの定義とminimize()の呼び出し)だけを持つ。個体数・世代数は
未決定事項のため、CLI引数で調整できるようにしている。

## 目的関数の符号

pymooは最小化のみを扱う。retentionは最大化したい目的なので、OBJ_SIGN
([-1, 1, 1])をFrameProblem._evaluateで使い、retentionの符号だけ反転する。
commons/report.py側で表示用に符号を戻す際もこの定数を使う(値の変換に
使う符号の定義を1箇所に集約するため)。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(いずれも正の値であること等)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(GAを実際に動かしながら見直す前提の暫定値):

- ring_radius: リングの終端(鼻翼の皮膚に掛かる接触点)は固定で、半径と
  隙間の角度から中心と内側の接点(=ステムの位置)が決まる(models.
  frame_modelのモジュールdocstring「幾何」参照)ため、ステムが鼻栓の
  円柱内に収まる(stem_plug_margin)半径の範囲は隙間の角度に依存する
  (既定の隙間90度では約2〜5mm)。下限1.5mm・上限6.0mmは、その境界の
  少し外側まで探索して境界形状を見誤らないようにした値
- ring_gap_deg: 隙間は内側上方(鼻翼の壁が上へつながる場所)に開く。
  終端の方向は180度-ring_gap_deg(90度で真上)。下限60度は、これより
  狭いと終端が内側上方へ回り込みすぎて円弧が鼻翼の壁に突っ込む
  (ring_clearance_margin違反)境界の少し外側。上限180度は、終端が
  横端になり円弧が下半分だけの「J」字になる境界
- ring_thickness: 下限0.8mm。上限2.5mmは、実際の鼻ピアスの線材の細さに
  近づけるため、旧上限(5.0mm)から引き下げた。ring_radiusの上限(4.5mm)に
  対してチューブの半径(ring_thickness/2)が太くなりすぎない範囲でもある
- ring_depth: 下限0.1mm(クリップとして機能する最小限の押し込み)。上限
  1.5mmは、リングが鼻翼の肉に深く埋没しすぎない範囲にした
- stem_length: ステムはリングの内側の端(鼻孔の縁の少し上)から鼻栓の
  軸方向へ伸びる。下限2.0mmは鼻栓に最低限刺さる長さ、上限10.0mmは
  鼻栓の奥の端(plug.length=12.0mmの90%)を突き抜ける(plug_overshoot_
  margin違反)境界の少し外側
- stem_thickness: 下限0.5mm(針のように細すぎない程度)。上限2.0mmは、
  ring_thicknessの上限引き下げ(2.5mm)に合わせて調整した値で、
  thickness_order_margin(ring_thickness>stem_thickness)と矛盾しない
  (ring_thicknessの下限0.8mmとの間に探索の余地を残している)

「b」字型はリング(丸い部分)+ステム(まっすぐな部分)というシンプルな
構成のため、旧設計(コネクタの4区間の曲げ)にあった曲げの自由度は持たない
(earrings.frame_modelのモジュールdocstring参照)。探索変数の総数は11から
6に減った。
"""

import argparse
import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/earrings/xxx.py`で
# 実行するとsys.path[0]はscripts/earrings/になり、commons/earringsパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: E402
from pymoo.core.problem import Problem  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402

from commons.nose_model import NoseParams, build_nose_body  # noqa: E402
from commons.plug_model import PlugParams  # noqa: E402
from commons.report import SORT_KEYS, plot_evolution, print_summary  # noqa: E402
from earrings.evaluation import constraint_values, evaluate_frame  # noqa: E402
from earrings.export_model import OUTPUT_DIR  # noqa: E402
from earrings.frame_model import (  # noqa: E402
    FrameParams,
    validate_ring_height,
    validate_target_reach,
)

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("ring_radius", 1.5, 6.0),
    ("ring_gap_deg", 60.0, 180.0),
    ("ring_thickness", 0.8, 2.5),
    ("ring_depth", 0.1, 1.5),
    ("stem_length", 2.0, 10.0),
    ("stem_thickness", 0.5, 2.0),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(retention, pain, fit_gap)の符号。pymooは最小化のみ扱うため、
# 最大化したいretentionだけ反転する(モジュールdocstring参照)。
# commons/report.pyが表示用に符号を戻す際にも使うため、モジュール外に
# 公開する(先頭にアンダースコアを付けない)
OBJ_SIGN = np.array([-1.0, 1.0, 1.0])

# 目的の表示名(グラフの軸ラベル)。retention, pain, fit_gapの順で固定
# (FrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = [
    "retention (挟み力, 既定=1, 最大化)",
    "pain (圧力 = 挟み力/接触面積, 最小化)",
    "fit_gap (mm, 最小化)",
]
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [
    ("ring_r", 7),
    ("ring_gap", 9),
    ("ring_t", 7),
    ("ring_d", 7),
    ("stem_len", 9),
    ("stem_t", 7),
]
_F_COLUMNS = [("retention", 11), ("pain", 8), ("fit_gap", 9)]


class FrameProblem(Problem):
    """FrameParamsの6変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく。ここで弾かれず個体評価のたびに呼んでも
        # 結果は変わらないが(evaluate_frame参照)、不正な設定なら数千回の
        # 評価を待たずに即座に気付きたい
        validate_target_reach(plug, nose)
        validate_ring_height(nose, build_nose_body(nose))

        super().__init__(n_var=6, n_obj=3, n_ieq_constr=9, xl=_XL, xu=_XU)
        self.plug = plug
        self.nose = nose

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        objectives = np.empty((len(x), self.n_obj))
        constraints = np.empty((len(x), self.n_ieq_constr))
        for i, row in enumerate(x):
            frame = FrameParams(**dict(zip(_VAR_NAMES, row)))
            score = evaluate_frame(frame, self.plug, self.nose)
            objectives[i] = OBJ_SIGN * [score.retention, score.pain, score.fit_gap]
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
        choices=sorted(SORT_KEYS),
        default="retention",
        help="パレートフロントの表をどの目的が良い順に並べるか(既定: retention)",
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

    # commons/report.py側はpymooのResult/Problemに依存させず、表示用に
    # 変換済みのプレーンなnumpy配列だけを渡す(可視化・表示ロジックをGAの
    # 実行から完全に切り離すため)
    generations = [OBJ_SIGN * h.pop.get("F") for h in res.history]
    pareto_f = OBJ_SIGN * res.F
    n_feasible = int(res.algorithm.pop.get("feasible").sum())
    n_total = len(res.algorithm.pop)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    evolution_path = args.output_dir / "evolution.png"
    plot_evolution(generations, evolution_path, _OBJ_LABELS)
    print_summary(
        res.X, pareto_f, n_feasible, n_total, _X_COLUMNS, _F_COLUMNS, sort_by=args.sort_by
    )
    print(f"\n画像を出力: {evolution_path}")


if __name__ == "__main__":
    main()
