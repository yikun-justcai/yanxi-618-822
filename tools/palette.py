"""配色重映射：把页面色值按 HSL 归到五个色族，换色相与饱和上限。

用法：
    python tools/palette.py                 # 应用默认「暖纸琥珀」
    python tools/palette.py --file x.html --ink-h 158 --accent-h 152 --accent-s 30 ...
    python tools/palette.py --preview       # 只看映射，不改文件

规则幂等：饱和用 min 截断，重复跑不会继续漂移。
"""

import argparse
import colorsys
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def to_hex(r, g, b):
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(PROJECT / "index.html"))
    ap.add_argument("--neutral-h", type=int, default=38)
    ap.add_argument("--ink-h", type=int, default=30)
    ap.add_argument("--ink-s", type=float, default=0.18)
    ap.add_argument("--accent-h", type=int, default=36)
    ap.add_argument("--accent-s", type=float, default=0.62)
    ap.add_argument("--sage-h", type=int, default=108)
    ap.add_argument("--sage-s", type=float, default=0.24)
    ap.add_argument("--brick-h", type=int, default=14)
    ap.add_argument("--brick-s", type=float, default=0.58)
    ap.add_argument("--slate-h", type=int, default=205)
    ap.add_argument("--slate-s", type=float, default=0.22)
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    def remap(hex_color):
        raw = hex_color.lstrip("#")
        alpha = ""
        if len(raw) == 8:
            raw, alpha = raw[:6], raw[6:]
        if len(raw) == 3:
            raw = "".join(c * 2 for c in raw)
        r, g, b = (int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        deg = h * 360

        if l <= 0.26:
            nh, ns, nl = a.ink_h, a.ink_s, min(max(l, 0.08), 0.26)
        elif l >= 0.88:
            if s <= 0.18:
                if l >= 0.99:
                    nh, ns, nl = a.neutral_h, 0.16, 0.985
                elif l >= 0.93:
                    nh, ns, nl = a.neutral_h, 0.38, 0.945
                else:
                    nh, ns, nl = a.neutral_h, 0.30, l
            else:
                if 40 <= deg < 95:
                    nh, ns = a.accent_h, a.accent_s
                elif 95 <= deg < 165:
                    nh, ns = a.sage_h, a.sage_s
                elif 165 <= deg < 235:
                    nh, ns = a.slate_h, a.slate_s
                else:
                    nh, ns = a.brick_h, a.brick_s
                ns, nl = min(s, ns), l
        elif s <= 0.12:
            nh, ns, nl = a.neutral_h, 0.10, l
        else:
            if 40 <= deg < 95:
                nh, ns = a.accent_h, a.accent_s
            elif 95 <= deg < 165:
                nh, ns = a.sage_h, a.sage_s
            elif 165 <= deg < 235:
                nh, ns = a.slate_h, a.slate_s
            elif deg < 40 or deg >= 320:
                nh, ns = a.brick_h, a.brick_s
            else:
                nh, ns = a.accent_h, a.accent_s
            ns, nl = min(s, ns), l
        nr, ng, nb = colorsys.hls_to_rgb(nh / 360, nl, ns)
        return to_hex(nr, ng, nb) + alpha

    path = Path(a.file)
    s = path.read_text(encoding="utf-8")
    hexes = sorted({m.group(0).lower() for m in re.finditer(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\b", s)}
                   | {m.group(0).lower() for m in re.finditer(r"#[0-9a-fA-F]{3}\b", s)})
    mapping = {h: remap(h) for h in hexes}
    if a.preview:
        for k, v in mapping.items():
            print(f"{k} -> {v}")
        return
    for old, new in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        s = re.sub(re.escape(old) + r"(?![0-9a-fA-F])", new, s, flags=re.I)
    path.write_text(s, encoding="utf-8")
    (path.parent / (path.stem + ".palette.json")).write_text(
        json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name}: mapped {len(mapping)} colors")


if __name__ == "__main__":
    main()
