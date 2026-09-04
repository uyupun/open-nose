"""フレームの評価関数(v2: 機能性・快適さ・意匠性の3目的+到達性の制約)。
PROJECT.md の「評価関数」に対応。

frame_model.build_frame_pair が作る円柱メッシュを経由せず、経路の点列
(build_side_paths)と鼻本体メッシュだけを使って評価する。円柱メッシュの
生成コストを払わずに済むため、遺伝的アルゴリズムが個体ごとに繰り返し
呼び出す用途でも軽量に計算できる。

- **機能性(function、最大化)**: retention(保持力)。grip_depthが深いほど
  鼻中隔を強く挟み込み、arm_thicknessが太いほどその挟み込みを維持する
  剛性が高い、という代理指標。ただしarm_thicknessの寄与は鼻栓自体の
  直径(plug.diameter)で頭打ちにする(下記の注意点参照)。clip_angleは
  含めない(下記参照)。到達性(鼻栓の露出端に保持部が届いているか)は
  reach_gapで別途扱う(0であるべき制約。目的関数を増やしすぎないよう、
  目的ではなく実行不可能個体を弾く制約として使う想定)
- **快適さ(comfort、最小化)**: pain(痛み)。retentionと同じgrip_depthの
  裏返し(圧迫が度を越していないか)
- **意匠性(style、最小化)**: fit_gap(視覚的一体感)・smoothness(経路の
  滑らかさ)・proportion_penalty(太さ・長さのプロポーション破綻)の複合。
  各サブ項目をどう重み付けて1つのスカラーに合成するかはNSGA-II導入時の
  未決定事項(PROJECT.md参照)のため、ここでは合成せず個別の値を返す

## retentionにclip_angleを含めない理由

サブエージェントによるレビューでは「clip_angleも保持力に寄与するはず」と
指摘されたが、実際のジオメトリ(frame_model.arm_points)を確認すると、
左右のアームは起点(x=0、clip_angleに依らず常に同じ点)から生えており、
clip_angleは起点から離れた後の開き方(左右への広がり方)にしか影響しない。
実物のバネ式クリップのように、起点そのものの角度が挟み込む力を生む
構造にはなっていないため、retentionの代理指標には含めなかった。

## retentionのarm_thicknessをplug.diameterで頭打ちにする理由

別セッションのサブエージェントによるレビューで、retention(grip_depth×
arm_thickness)とproportion_penalty(太さ/長さ比の上限のみ)の組み合わせに
抜け穴が見つかった。当初proportion_penaltyの上限を緩く設定していたため、
grip_depthをほぼ0(=painもほぼ0)にしたままarm_thicknessだけ非現実的に
太くすると、意匠性側のコストをほぼ払わずにretentionだけ稼げてしまう
(v1で発覚した「体積を0に近づけて最適化目的と矛盾する」問題が、対象を
arm_thicknessに変えて再発した形)。

これに対し、retention自体にarm_thicknessの寄与の頭打ちを設け、
proportion_penaltyの上限も長さとの自己参照的な比率ではなく、シーン内に
実在する物理的な基準(鼻栓の直径)との比較に置き換えた。アームが鼻栓
本体よりも太くなる理由はなく、それを超えて太くしても保持力の向上には
寄与しない(=挟んでいる相手より太いクリップは、太さの分だけ無駄という
考え方)とみなす。
"""

from dataclasses import dataclass

import numpy as np
import trimesh

from models.frame_model import (
    FrameParams,
    SidePaths,
    build_side_paths,
    surface_following_points,
    validate_anchor_height,
    validate_arm_clearance,
    validate_grip_depth,
    validate_grip_ring,
    validate_target_reach,
)
from models.nose_model import NoseParams, build_nose_body
from models.plug_model import PlugParams, plug_outer_end

# プロポーション評価(下限)で許容する、太さ(arm_thickness)/全長 比の下限。
# 固定の「理想比率」を目標にすると設計者個人の美意識を客観指標と偽装する
# ことになるため、範囲内は罰則0とし、下回った分だけを罰則にする
# (毛髪のように細く見える、という明らかに破綻したケースだけを弾く緩い値。
# 現行のデフォルト値(比率約0.078)は範囲内に収まることを確認済み)
_MIN_THICKNESS_RATIO = 0.03
# retention・プロポーション評価(上限)で、arm_thicknessの寄与を頭打ちに
# する基準。plug.diameterに対する倍率(理由は上のモジュールdocstring参照)
_MAX_THICKNESS_TO_PLUG_DIAMETER = 1.0


def _retention(frame: FrameParams, plug: PlugParams) -> float:
    """保持力(機能性、最大化)。grip_depth(めり込み量)×arm_thickness(剛性)。
    arm_thicknessの寄与はplug.diameterで頭打ちにする(理由はモジュール
    docstring参照)。clip_angleを含めない理由も同docstring参照。
    """
    effective_thickness = min(
        frame.arm_thickness, plug.diameter * _MAX_THICKNESS_TO_PLUG_DIAMETER
    )
    return frame.grip_depth * effective_thickness


def _pain(frame: FrameParams) -> float:
    """痛み(快適さ、最小化)。retentionと表裏一体のgrip_depthそのもの。"""
    return frame.grip_depth


def _reach_gap(sides: list[SidePaths], targets: list[np.ndarray]) -> float:
    """到達性の制約チェック用の値(0であるべき)。

    connector_pointsの最終点がtarget(鼻栓の露出端)に届いていない距離
    (holder_offsetがdive_distにクランプされた場合の未到達量)。左右のうち
    より届いていない側(最大値)を返す。
    """
    return max(
        float(np.linalg.norm(target - path[-1]))
        for (_, path), target in zip(sides, targets)
    )


def _fit_gap(
    sides: list[SidePaths], body: trimesh.Trimesh, arm_thickness: float
) -> tuple[float, float]:
    """視覚的一体感(意匠性の一部)。表面沿い区間の"円柱表面"から鼻本体表面
    までの距離の(平均, 最悪点)を返す。値が小さいほど顔に馴染んで見える。

    表面沿い区間の点列(surface_points)はメッシュの中心線であり、実際に
    見える/触れるのは半径arm_thickness/2だけ太い円柱の表面。中心線からの
    距離をそのまま使うと、太いアームほど実際の見た目の隙間より過大な
    値になってしまう(frame_model.arm_points/connector_pointsが中心線を
    arm_thickness/2の分だけ余分に浮かせているのと対になる補正)。
    curvature等により半径分を引いた値がわずかに負になりうるため0で
    クランプする。
    """
    means, maxes = [], []
    for points, path in sides:
        surface_points = surface_following_points(points, path)
        _, distance, _ = trimesh.proximity.closest_point_naive(body, surface_points)
        tube_distance = np.maximum(distance - arm_thickness / 2, 0.0)
        means.append(float(np.mean(tube_distance)))
        maxes.append(float(np.max(tube_distance)))
    return max(means), max(maxes)


def _smoothness(sides: list[SidePaths]) -> float:
    """経路の滑らかさ(意匠性の一部、最小化)。表面沿い区間からダイブ区間への
    遷移角度(度)。0に近いほど、鼻栓へ向けて滑らかに連続する経路になる。

    折れ線全体の角度をまとめて評価すると、最適解が単純な直線(無機質な
    針金)に収束してしまう、あるいはサンプリング分割数の副作用を測るだけに
    なりやすいため、設計意図(表面沿いの経路→鼻栓へのダイブ)を反映する
    この1箇所の遷移角だけに絞る。

    holder_offset=0(バリデーション上は有効)の場合、connector_pointsの
    最終区間(approach→path[-1])の長さが0になり、diveベクトルがゼロに
    なる。同様にincomingベクトル(path[-2]とpath[-3]、連続する2つの
    表面沿いサンプル点の差)も、_CONNECTOR_SAMPLESの分割の仕方や
    arm_end/targetのyがたまたま一致する等の縮退したジオメトリでは
    ゼロになりうる。どちらの場合も「その区間が実質存在しない」とみなし、
    追加の折れがないという意味で角度0を返す(0除算でNaNになることを避ける)。
    """
    angles = []
    for _, path in sides:
        incoming = path[-2] - path[-3]
        dive = path[-1] - path[-2]
        incoming_norm = np.linalg.norm(incoming)
        dive_norm = np.linalg.norm(dive)
        if incoming_norm < 1e-9 or dive_norm < 1e-9:
            angles.append(0.0)
            continue
        cos_angle = np.dot(incoming, dive) / (incoming_norm * dive_norm)
        angles.append(float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))))
    return max(angles)


def _proportion_penalty(
    sides: list[SidePaths], arm_thickness: float, max_thickness: float
) -> float:
    """プロポーションの破綻(意匠性の一部、最小化)。下限は太さ/全長比が
    _MIN_THICKNESS_RATIOを下回った分(細すぎ)、上限はarm_thicknessが
    max_thickness(plug.diameter基準の頭打ち値)を超えた分(太すぎ)を
    罰則にする(範囲内は0)。上限をplug.diameter基準にする理由はモジュール
    docstring参照(retentionの頭打ちと同じ基準で、太さだけを稼ぐ抜け道を
    塞ぐ)。
    """
    penalties = []
    for points, path in sides:
        full_path = points + path[1:]
        length = sum(
            float(np.linalg.norm(full_path[i + 1] - full_path[i]))
            for i in range(len(full_path) - 1)
        )
        ratio = arm_thickness / length
        too_thin = max(0.0, _MIN_THICKNESS_RATIO - ratio)
        too_thick = max(0.0, arm_thickness - max_thickness)
        penalties.append(too_thin + too_thick)
    return max(penalties)


@dataclass(frozen=True)
class FrameScore:
    """フレームの評価値。

    retention(機能性)は最大化、他は最小化。reach_gapは目的ではなく制約
    (0であるべき)として別枠で保持する。styleのサブ項目は重み付け方法が
    未定(PROJECT.md参照)のため、合成せず個別の値のまま返す。
    """

    retention: float  # 機能性(最大化)
    reach_gap: float  # 制約(0であるべき)
    pain: float  # 快適さ(最小化)
    fit_gap_mean: float  # 意匠性: 視覚的一体感・平均(最小化)
    fit_gap_max: float  # 意匠性: 視覚的一体感・最悪点(最小化)
    smoothness: float  # 意匠性: 経路の滑らかさ(最小化)
    proportion_penalty: float  # 意匠性: プロポーション破綻(最小化)


def evaluate_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FrameScore:
    """FrameParams から機能性・快適さ・意匠性の評価値を計算する。"""
    validate_target_reach(plug, params)
    validate_grip_depth(frame, params)
    validate_anchor_height(params)
    body = build_nose_body(params)
    sides: list[SidePaths] = [
        build_side_paths(frame, plug, params, side) for side in (-1, 1)
    ]
    validate_arm_clearance(sides, body, frame.arm_thickness)
    validate_grip_ring(frame, params, body)

    targets = [
        plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)
        for side in (-1, 1)
    ]
    max_thickness = plug.diameter * _MAX_THICKNESS_TO_PLUG_DIAMETER
    fit_gap_mean, fit_gap_max = _fit_gap(sides, body, frame.arm_thickness)

    return FrameScore(
        retention=_retention(frame, plug),
        reach_gap=_reach_gap(sides, targets),
        pain=_pain(frame),
        fit_gap_mean=fit_gap_mean,
        fit_gap_max=fit_gap_max,
        smoothness=_smoothness(sides),
        proportion_penalty=_proportion_penalty(sides, frame.arm_thickness, max_thickness),
    )
