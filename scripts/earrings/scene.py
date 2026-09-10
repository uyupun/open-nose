"""鼻ピアス型(「b」字)設計: 鼻本体・鼻栓・フレームを組み合わせ、1つのSceneにまとめる。"""

import trimesh

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams, build_plug_pair
from earrings.frame_model import FrameParams, build_frame_pair


def build_full_scene(frame: FrameParams | None = None) -> trimesh.Scene:
    """鼻本体・鼻栓・フレームを組み合わせたSceneを返す。

    frameを省略するとFrameParamsの既定値を使う。NSGA-IIが見つけた候補
    (earrings/optimize.pyの出力する設計変数の組)を実際の形状として見たい
    場合は、呼び出し側(view_nose.py等)から具体的なFrameParamsを渡す。
    """
    params = NoseParams()
    body = build_nose_body(params)

    plug = PlugParams()
    plug_left, plug_right = build_plug_pair(
        plug, gap=params.nostril_gap, depth_front=params.tip_depth_front
    )

    frame = frame or FrameParams()
    frame_left, frame_right = build_frame_pair(frame, plug, params)

    # 登録順は「内側の部品→外側の部品」(フレーム→鼻栓→鼻本体。commons.
    # viewer.DRAW_ORDER_PREFIXESと同じ順)。理由はDRAW_ORDER_PREFIXESの
    # コメント参照。glTF出力の内容(形状・色)には影響しない
    return trimesh.Scene(
        {
            "frame_left": frame_left,
            "frame_right": frame_right,
            "plug_left": plug_left,
            "plug_right": plug_right,
            "body": body,
        }
    )
