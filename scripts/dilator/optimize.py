"""NSGA-II(pymoo)による拡張ブリッジ型フレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/dilator/evaluation.py)をpymooの
Problemでラップし、FrameParamsの8設計変数を探索してパレートフロントを
求める。可視化・結果表示はcommons/report.py側の責務とし、このファイルは
実行(FrameProblemの定義とminimize()の呼び出し)だけを持つ
(earrings/spiral.optimize.pyと同じ構成)。

## 目的関数の符号

pymooは最小化のみを扱う。3目的(extension_force・plug_hold・
inconspicuousness)はいずれも最大化したいので、OBJ_SIGN([-1, -1, -1])で
すべて符号を反転する。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(いずれも正の値であること)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(GAを実際に動かしながら見直す前提の暫定値。
scripts/dilator/frame_model.pyのモジュールdocstring参照):

- natural_radius: 装着後の実際の曲率半径(bridge_curvature)に対し、
  curvature_margin(_MIN_CURVATURE_RATIO=1.2倍)を満たせる下限の
  すぐ内側を下限(6.0mm)にした(装着位置bridge_yによって装着後の曲率が
  変わるので、下限付近ではcurvature_marginが実際に効く)。上限100.0mmは、これ以上平らにしてもdeflection
  (1/actual_radius - 1/natural_radius)の増分が小さくなり
  (1/natural_radiusが0に近づくため)、実質的な効果が頭打ちになる水準の
  暫定値だった。その後、印刷する帯を「装着した形の曲がりをactual_radius/
  natural_radiusの割合に弱めた形」にした(frame_model._print_profile)ため、
  natural_radiusが大きいほど印刷した帯は平らになる。GAは拡張力のために
  上限へ寄せ、帯がほぼ平らな板になって「アーチ状が平べったすぎる。前と
  同じくらいのアーチ状がいい」(ユーザー指摘)となったので、14.0〜26.0mm
  (装着時の曲率半径は約9.5〜13mmなので、印刷した帯の曲がりは装着時の
  約4〜9割)にした
- bridge_width: 実際のブリーズライトの幅の水準に近づけた範囲(下限3.8mm、
  上限5.0mm)。下限は、連結部のクリップの突起と丸穴が帯の幅に収まる
  必要(cuff_fit_margin)と、両面テープの貼り代の面積(tape_area_margin、
  幅×貼り代長さ×2が_MIN_TAPE_AREA以上)から決まる。ユーザー指摘(「縦が長すぎる、鼻にフィットする感じに」)を
  受けて、以前の上限(7.0mm、鼻翼の隆起commons.nose_model._ALAE_BUMP_SPAN
  ≈7mmに合わせた値)から縮めた。なお、bridge_widthはextension_force
  (∝width)とpain(∝thickness^3/length^3、widthはforce/areaの計算で
  相殺されるため現れない)・inconspicuousness(thicknessのみに依存)の
  いずれにも本質的なトレードオフがなく、GAは常にこの上限へ寄せる
  (実際のパレートフロントでも全個体がbridge_width≈上限値だった)。
  この上限自体が実質的な既定の見た目を決める値になるため、値そのものを
  ユーザーの見た目の指摘に合わせて調整する方針にした
- bridge_thickness: 平らな板ばね(実際のブリーズライトのテープ厚)の
  水準。ユーザー要望「アーチをもう少し横に長く、かつ薄くしたい。厚さは
  1mmくらい。両端に医療用両面テープを貼ってブリーズライトのように使う」
  を受けて0.8〜1.4mmにした(印刷・嵌め込みに耐える厚みは、連結部だけ
  以前は連結部だけ局所的に厚くするパッドで確保していたが、連結部をクリップに
  したいまは帯は一枚板のまま
  するので、帯本体はテープが貼れる薄さにできる)。下限0.8mmはFDMの
  0.2mm積層で4層、上限1.4mmは「1mmくらい」の幅
- tab_side_ratio: 帯の端(円弧の端、=貼り代の位置)を、断面の側面の輪郭の
  どこに置くか(直線の辺の長さを1とした弧長。0=鼻の正面寄りの端、1=背面角
  の手前、1を超えると背面角の丸みに入る)。連結部のクリップは
  この端から少し内側に付く。以前は定数0.75だったが、ユーザー
  指摘「接続部分がもう少し外側にあってもいい。今は鼻の正面に沿っていて、
  メガネをしていると付けづらそう」を受けて変数にした。帯は鼻の前面と
  側面に沿い、1を超えるぶんは背面角の丸みに沿わせず直線の辺の向きの
  まままっすぐ伸ばす(frame_model._bridge_profile)。下限0.85は
  joint_access_margin(鼻の側面への寄り)が効き始める水準(これより
  正面寄りは、帯の高さによってはほぼ全滅する)。帯を一定の曲率の円弧に
  してからは、直線の辺の上(上限1.0)だけではアーチが短すぎた(ユーザー
  指摘「アーチを前みたいに長く」。GAの解はbridge_y≈20でx=±9mm、以前は
  鼻の側面を回り込んで±13mm)ため、背面角の丸みまで広げて1.10〜1.35にした
  (弧長27〜35mm)。帯を鼻に沿うアーチ+まっすぐな端に改めてからは
  1.2〜1.4(弧長27〜33mm)。帯は長いほど曲げ戻りの力が弱くなる(剛性が
  長さの3乗に反比例)ため、1.0から探索させるとGAは下限(弧長約24mm)に
  寄せ、アーチが短く戻ってしまった。1.4で端の浮きが1.5mm前後になり、
  それより先は貼り代が減っていく
- bridge_y: 帯を鼻のどの高さに貼るか(mm)。以前はframe_modelの定数
  (_BRIDGE_Y)で最適化の対象外だったが、装着位置は装着後の曲率半径と
  帯の経路長(=拡張力)・棒の長さ(=鼻栓の保持剛性と目立ち方)の
  すべてを左右するため探索変数にした。下限6.0mmは小鼻の隆起のあたり、
  上限22.0mmは鼻筋の半ば(鼻の長さ52.2mmの4割)。その後、アーチを長く
  保つため(tab_side_ratio参照。鼻筋側ほど断面が細く、アーチが短くなる)
  上限を18.0mmにし(帯を鼻に沿うアーチに戻してからは、GAが上限へ寄せて
  弧長が25mmまで縮んだので15.0mmにした。15mmで弧長27mm以上)、鼻栓を下げて(frame_model.DILATOR_PLUG)棒が3mm
  長くなったので下限を10.0mmに下げた。以前の下限13.0mmは、棒を
  平たいブレードにしてアーチの面からリングの面へねじる造形(frame_model.
  _blade_manifold)に必要な長さ(blade_twist_margin、31mm前後で3.0度/mmを
  切る)から決まる。以前は6.0mmだったが、そこでは棒が25mmしかなく
  「ねじれた板」に見えない。実測では
  extension_forceに+0.36、plug_holdに-0.78、inconspicuousnessに-0.67と、
  3目的すべてに効く唯一の変数になっている
- leg_thickness: 当初はearrings.optimize.pyのring_thicknessと同じ範囲
  (0.8〜2.5mm)にしていたが、実際に3Dプリントしたところ「サポートを
  つけても強度がなく崩れてしまう」という指摘を受け、下限を1.2mmへ
  引き上げ、その後さらに実際に印刷したユーザーの「棒をもう少し太く(印刷
  できない)」「まだ太くして欲しい」という指摘を受けて1.2→1.6→2.2mmへ
  上げた(上限も1.9→2.6→3.2mm)。いまは2.0〜4.0mmで、plug_hold(棒の
  曲げ剛性、実測相関+0.70)とinconspicuousness(-0.47)の主役。棒の
  太さ(鼻の側面に沿う区間の最大)・タブの首の幅に使われる。レンズ(筒)自体の壁の肉厚には使われない(以前はleg_thicknessを
  そのまま流用していたが、左右のレンズが重なってブーリアン結合が破綻する
  原因になったため、frame_model._COLLAR_WALL_THICKNESSという固定値に
  切り離した。同定数のコメント参照)。上限は1.9mmにとどめた:
  leg_clearance_margin(棒が鼻の側面に沿う区間の、線径に比例しためり込み
  許容量)が太い個体ほど厳しくなるため(この制約自体は鼻表面への不自然な
  沈み込みを防ぐためのもので、印刷強度の指摘とは無関係。緩めていない)。
  なお棒は、レンズへ溶け込む手前と、帯(ブリッジ)のタブへ入る手前では、
  レンズ・帯の厚みに収まる太さまでなめらかに細くなる(frame_model.
  _rod_radii参照)ため、この値は「棒の最も太いところ」の意味になる。
  最も細いところ(レンズへ溶け込む区間)はrod_thickness_marginが印刷可能な
  太さ(_MIN_ROD_DIAMETER=1.8mm)を下回らないか監視する。
  leg_thicknessも目的(extension_force・pain・inconspicuousness)の
  いずれにも現れないため、bridge_widthと同様、GAは制約が許す限りこの
  上限へ寄せる
- collar_length: レンズ(鼻栓を差し込む筒)の厚み。レンズは鼻栓の露出部分
  (鼻の外、commons.plug_model.plug_outer_endからcommons.nose_model.
  tip_cap_min_yまでの間、実測で約2.25mm)に収める設計のため、これを
  超えると鼻本体メッシュにめり込む(collar_clearance_margin、実測の
  違反率34%)。
  ユーザー指摘「まだ太くして欲しい」を受けてframe_model._COLLAR_PLUG_INSETを
  0.3→0.15mmに詰め、そのぶん上限を1.9→2.1mmへ伸ばした(実測で2.2mmから
  違反し始める)。下限1.95mmは、棒がレンズへ溶け込む区間の太さがこの厚みで
  決まる(_rod_radii。レンズの上下の面からはみ出さない=直径≦collar_length)
  ため、要求する太さ(rod_thickness_margin、直径1.8mm以上)をわずかな余裕を
  持って満たす水準から決めた。つまりこの変数は、レンズの厚みと棒の太さを
  同時に決める一番効くつまみになっている
- cuff_detent: 連結部(帯を抱くC)が、帯の端近くの浅い段を越えるときの
  締めしろ(mm、片側)。連結部をエッジクリップ→帯を抱くCに変えた(ユーザーが
  3案を見比べて選んだ)のに伴い、clip_detent(クリップの突起の高さ)から
  置き換えた。大きいほど外すのに力が要る(cuff_retention_margin、1.5〜10N)が、
  そのぶんCが大きく開いて折れやすい(cuff_strain_margin、ひずみ3%以下)。
  どちらもCの背の長さ(=帯の幅bridge_width)と、Cの長さ(=棒の幅
  leg_thickness)に依存するので、それらとの組み合わせで範囲が決まる。
  範囲0.03〜0.25mmは、下側・上側をそれぞれ2つの制約が実際に弾く幅
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
from dilator.frame_model import (  # noqa: E402
    DILATOR_PLUG,
    FrameParams,
    validate_collar_no_overlap,
    validate_target_reach,
)

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("natural_radius", 14.0, 26.0),
    ("tab_side_ratio", 1.2, 1.4),
    ("bridge_y", 10.0, 15.0),
    ("bridge_width", 3.8, 5.0),
    ("bridge_thickness", 0.8, 1.4),
    ("leg_thickness", 2.0, 4.0),
    ("collar_length", 1.9, 2.2),
    ("cuff_detent", 0.03, 0.25),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(extension_force, plug_hold, inconspicuousness)の符号。pymooは
# 最小化のみ扱うため、3つとも最大化したい今の構成では全て反転する
# (モジュールdocstring参照)
OBJ_SIGN = np.array([-1.0, -1.0, -1.0])

# 目的の表示名(グラフの軸ラベル)。extension_force, pain, inconspicuousness
# の順で固定(FrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = [
    "extension_force (帯の拡張力, 基準の帯の剛性=1, 最大化)",
    "plug_hold (鼻栓の保持剛性, 同じ正規化, 最大化)",
    "inconspicuousness (目立たなさ = -正面投影面積 mm^2, 最大化)",
]
# print_summaryの並べ替え指定: 目的の名前 → (列番号, 大きい順か)。
# OBJ_SIGN・_OBJ_LABELSと同じ順序・向き
_SORT_KEYS: SortKeys = {
    "extension_force": (0, True),
    "plug_hold": (1, True),
    "inconspicuousness": (2, True),
}
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [
    ("nat_r", 8),
    ("tab_pos", 8),
    ("bridge_y", 9),
    ("bridge_w", 9),
    ("bridge_t", 9),
    ("leg_t", 7),
    ("collar_l", 9),
    ("detent", 8),
]
_F_COLUMNS = [("force", 8), ("hold", 8), ("inconspic.", 11)]


class FrameProblem(Problem):
    """FrameParamsの8変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく(earrings/spiral.optimize.pyと同じ理由)
        validate_target_reach(plug, nose)
        validate_collar_no_overlap(plug, nose)

        super().__init__(n_var=8, n_obj=3, n_ieq_constr=16, xl=_XL, xu=_XU)
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
                score.plug_hold,
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

    problem = FrameProblem(DILATOR_PLUG, NoseParams())
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
