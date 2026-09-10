"""NSGA-II(pymoo)によるフレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/evaluation.py)をpymooのProblemで
ラップし、FrameParamsの11設計変数を探索してパレートフロントを求める。
可視化・結果表示はoptimize_report.py側の責務とし、このファイルは実行
(FrameProblemの定義とminimize()の呼び出し)だけを持つ。個体数・世代数は
未決定事項のため、CLI引数で調整できるようにしている。

## 目的関数の符号

pymooは最小化のみを扱う。retentionは最大化したい目的なので、OBJ_SIGN
([-1, 1, 1])をFrameProblem._evaluateで使い、retentionの符号だけ反転する。
optimize_report.py側で表示用に符号を戻す際もこの定数を使う(値の変換に
使う符号の定義を1箇所に集約するため)。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(connector_length_1..4>=0等)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(fit_gap_max/smoothnessの閾値と同様、GAを実際に動かし
ながら見直す前提の暫定値):

- connector_heading・connector_turn_2..4: アーム下端からの方向、および
  直前の区間からの曲げ角(度)。frame_model.connector_pointsがsin/cosベース
  の計算のため数値的な特異点がなく、-180〜180度のフル可動域を探索範囲に
  している
- connector_length_1..4: 下限0(dataclass上の下限。0にするとその区間の
  移動量は無視されるが、対応する曲げ角は次の区間に引き継がれる。
  FrameParamsのdocstring参照)。上限12.0mmは、コネクタがアーム下端
  (y≈6付近)から鼻栓の露出端(y≈-4.6付近)まで約11mm以上、曲がりながら
  到達する必要があることを踏まえ、arm_length系(旧設計、上限8.0mm)より
  やや広めにした
- arm_thickness: 下限0.5mm(針のように細すぎない程度)。上限8.0mmは
  retention/proportion_penaltyが頭打ちにする境界(plug.diameter=6.0mm)より
  余裕を持って大きくし、制約の境界が探索範囲の内側に来るようにした
  (境界ちょうどが上限だと、GAがその外側を探れず境界形状を見誤る)
- holder_offset: 下限0(dataclass上の下限)。上限12.0mmは、デフォルト設定
  での実際の到達距離(dive_dist、約8mm)より少し余裕を持たせた値
  (connector_points参照。dive_distを超えると評価に無反応になる平坦領域に
  入るため、それ以上大きくしても意味はない)
- grip_depth: 下限0(dataclass上の下限)。上限8.0mmは、デフォルト設定での
  アーム起点における鼻の局所的な厚み(実測: 約11.1mm、front_surface_z_at_
  center - back_surface_z_at_centerで計算)を踏まえ、arm_thicknessが薄い
  個体では実行可能、太い個体では制約(grip_depth_margin)違反になる
  ちょうど境界付近を探索範囲に収める値とした

曲げの自由度は以前アーム側にあった(issue #3)が、(1) retentionには
経路長さえあればよく曲げる意味がない、(2) 実際に形状を左右するのは
コネクタの向きだった、(3) アーム側の平坦近似ベースの検証が大きく曲がる
経路で実際の埋没を見逃す安全性バグがあった、という3点が判明し、コネクタ
側へ委譲した(models.frame_modelのモジュールdocstring参照)。アーム側の
起点(anchor_y)が固定定数に戻り、コネクタ側には起点に相当する変数が
不要なため、探索変数の総数は12から11に減った。
"""

import argparse
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

from evaluation import constraint_values, evaluate_frame
from models.frame_model import FrameParams, validate_anchor_height, validate_target_reach
from commons.nose_model import NoseParams
from commons.plug_model import PlugParams
from optimize_report import plot_evolution, print_summary

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("connector_heading", -180.0, 180.0),
    ("connector_length_1", 0.0, 12.0),
    ("connector_turn_2", -180.0, 180.0),
    ("connector_length_2", 0.0, 12.0),
    ("connector_turn_3", -180.0, 180.0),
    ("connector_length_3", 0.0, 12.0),
    ("connector_turn_4", -180.0, 180.0),
    ("connector_length_4", 0.0, 12.0),
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
    """FrameParamsの11変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく。ここで弾かれず個体評価のたびに呼んでも
        # 結果は変わらないが(evaluate_frame参照)、不正な設定なら数千回の
        # 評価を待たずに即座に気付きたい
        validate_target_reach(plug, nose)
        validate_anchor_height(nose)

        super().__init__(n_var=11, n_obj=3, n_ieq_constr=7, xl=_XL, xu=_XU)
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
