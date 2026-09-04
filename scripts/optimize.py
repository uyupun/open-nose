"""NSGA-II(pymoo)によるフレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/evaluation.py)をpymooのProblemで
ラップし、FrameParamsの5設計変数を探索してパレートフロントを求める。
可視化・結果表示はoptimize_report.py側の責務とし、このファイルは実行
(FrameProblemの定義とminimize()の呼び出し)だけを持つ。個体数・世代数は
未決定事項のため、CLI引数で調整できるようにしている(PROJECT.md「NSGA-IIの
パラメータ設定」参照)。

## 目的関数の符号

pymooは最小化のみを扱う。retentionは最大化したい目的なので、OBJ_SIGN
([-1, 1, 1])をFrameProblem._evaluateで使い、retentionの符号だけ反転する。
optimize_report.py側で表示用に符号を戻す際もこの定数を使う(値の変換に
使う符号の定義を1箇所に集約するため)。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(arm_length>=1.0、clip_angle>0等)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(fit_gap_max/smoothnessの閾値と同様、GAを実際に動かし
ながら見直す前提の暫定値):

- clip_angle: 下限は0を避けるため1.0(浮動小数点境界)。上限は
  _MAX_CLIP_ANGLE(60.0)をそのまま使う
- arm_length: 下限は_MIN_ARM_LENGTH(1.0)。上限は明確な基準がないため、
  _ARM_ANCHOR_Y(6.0)や鼻先までの距離感を踏まえた15.0mmとした。retentionが
  arm_lengthに比例するようになった(evaluation.pyのモジュールdocstring
  「retentionにarm_lengthを掛ける理由」参照)ため、下限に張り付く傾向は
  解消された。実際に既定設定(pop_size=50, n_gen=60)で動かすと、上限
  (15.0mm)まで達する前に約6〜8.7mm付近で釣り合う結果になった。smoothness
  制約をアーム→コネクタの継ぎ目まで含む経路全体に一般化した後(issue #2)は、
  grip_ring_marginに加えてsmoothnessもこの範囲でほぼ同時に頭打ちになる
  (アームが長いほどコネクタとの継ぎ目の折れが急になりやすいため)
- arm_thickness: 下限0.5mm(針のように細すぎない程度)。上限8.0mmは
  retention/proportion_penaltyが頭打ちにする値より余裕を持って大きくし、
  制約の境界が探索範囲の内側に来るようにした(境界ちょうどが上限だと、
  GAがその外側を探れず境界形状を見誤る)。境界はplug.diameter(6.0mm)。
  以前はholder_size_penalty(保持部の球の直径がplug.diameterを超えた分を
  罰則にする制約)がarm_thickness換算で約2.14mmとより厳しい境界を作って
  いたが、保持部の球自体を廃止した(evaluation.pyのモジュールdocstring
  「holder_size_penaltyを廃止した理由」参照)ため、この境界は消滅した
- holder_offset: 下限0(dataclass上の下限)。上限12.0mmは、デフォルト設定
  での実際の到達距離(dive_dist、約8mm)より少し余裕を持たせた値
  (PROJECT.mdの既知の限界の通り、dive_distを超えると評価に無反応になる
  平坦領域に入るため、それ以上大きくしても意味はない)
- grip_depth: 下限0(dataclass上の下限)。上限8.0mmは、デフォルト設定での
  アーム起点における鼻の局所的な厚み(実測: 約11.1mm、front_surface_z_at_
  center - back_surface_z_at_centerで計算)を踏まえ、arm_thicknessが薄い
  個体では実行可能、太い個体では制約(grip_depth_margin)違反になる
  ちょうど境界付近を探索範囲に収める値とした
"""

import argparse
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

from evaluation import constraint_values, evaluate_frame
from models.frame_model import FrameParams, validate_anchor_height, validate_target_reach
from models.nose_model import NoseParams
from models.plug_model import PlugParams
from optimize_report import plot_evolution, print_summary

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("clip_angle", 1.0, 60.0),
    ("arm_length", 1.0, 15.0),
    ("arm_thickness", 0.5, 8.0),
    ("holder_offset", 0.0, 12.0),
    ("grip_depth", 0.0, 8.0),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(retention, pain, fit_gap)の符号。pymooは最小化のみ扱うため、
# 最大化したいretentionだけ反転する(モジュールdocstring参照)。
# optimize_report.pyが表示用に符号を戻す際にも使うため、モジュール外に
# 公開する(先頭にアンダースコアを付けない)
OBJ_SIGN = np.array([-1.0, 1.0, 1.0])


class FrameProblem(Problem):
    """FrameParamsの5変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく。ここで弾かれず個体評価のたびに呼んでも
        # 結果は変わらないが(evaluate_frame参照)、不正な設定なら数千回の
        # 評価を待たずに即座に気付きたい
        validate_target_reach(plug, nose)
        validate_anchor_height(nose)

        super().__init__(n_var=5, n_obj=3, n_ieq_constr=7, xl=_XL, xu=_XU)
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
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
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

    # optimize_report.py側はpymooのResult/Problemに依存させず、表示用に
    # 変換済みのプレーンなnumpy配列だけを渡す(可視化・表示ロジックをGAの
    # 実行から完全に切り離すため)
    generations = [OBJ_SIGN * h.pop.get("F") for h in res.history]
    pareto_f = OBJ_SIGN * res.F
    n_feasible = int(res.algorithm.pop.get("feasible").sum())
    n_total = len(res.algorithm.pop)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    evolution_path = args.output_dir / "evolution.png"
    plot_evolution(generations, evolution_path)
    print_summary(res.X, pareto_f, n_feasible, n_total)
    print(f"\n画像を出力: {evolution_path}")


if __name__ == "__main__":
    main()
