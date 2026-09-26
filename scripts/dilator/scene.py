"""拡張ブリッジ型設計: 鼻本体・鼻栓・フレームを組み合わせ、1つのSceneにまとめる。"""

import trimesh

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import build_plug_pair
from dilator.frame_model import DILATOR_PLUG, FrameParams, build_bridge_piece, build_leg_piece


def build_full_scene(frame: FrameParams | None = None) -> trimesh.Scene:
    """鼻本体・鼻栓・フレームを組み合わせたSceneを返す。

    frameを省略するとFrameParamsの既定値を使う。フレームは、印刷しやすい
    ように分解して一つずつ装着できるようにしてほしいというユーザー要望を
    受けて、ブリッジ(鼻頭のアーチ状)・左の脚(棒とレンズ)・右の脚(棒と
    レンズ)の3つの別々の部品(dilator.frame_model.build_bridge_piece/
    build_leg_piece)で構成する。ブーリアン結合はせず、組み立てた状態の
    位置にそれぞれ配置するだけ(タブとスロットは嵌め合う形状だが、実際に
    固定するブーリアン結合は行わない。3Dプリント後にタブをスロットへ
    押し込んで組み立てる想定のため)。Sceneには"frame_bridge"・
    "frame_leg_left"・"frame_leg_right"の3キーを登録する
    (commons.viewer.DRAW_ORDER_PREFIXESの"frame"プレフィックスにすべて
    一致する)。
    """
    params = NoseParams()
    body = build_nose_body(params)

    plug = DILATOR_PLUG
    plug_left, plug_right = build_plug_pair(
        plug, gap=params.nostril_gap, depth_front=params.tip_depth_front
    )

    frame = frame or FrameParams()
    bridge_mesh = build_bridge_piece(frame, params)
    leg_left_mesh = build_leg_piece(frame, plug, params, side=-1)
    leg_right_mesh = build_leg_piece(frame, plug, params, side=1)

    return trimesh.Scene(
        {
            "frame_bridge": bridge_mesh,
            "frame_leg_left": leg_left_mesh,
            "frame_leg_right": leg_right_mesh,
            "plug_left": plug_left,
            "plug_right": plug_right,
            "body": body,
        }
    )
