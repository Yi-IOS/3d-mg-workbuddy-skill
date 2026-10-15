# -*- coding: utf-8 -*-
"""把 3D-MG ASCII 流程图集渲染为 300dpi PNG。

为什么需要这个：ASCII 制表图放进 Word/PPT 会被折行错位（w:br 丢失导致整块被
压成一个段落）。渲染成图片后框线不错位、中文对齐。

原理：SimSun（simsun.ttc）中全角字宽 = 2 × ASCII 半角。
      以 ASC=9px 为半角单位宽度逐字符落笔，即可精确复现制表对齐。

用法：
    python gen_flowchart.py                      # 渲染全部 20 张到 ./figs_out/
    python gen_flowchart.py --index 10           # 只渲染第 10 张
    python gen_flowchart.py --index 10 --scale 2  # 放大 2 倍（插入PPT 时用）
    python gen_flowchart.py --list# 列出所有图
"""
import os
import re
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "references", "models_flowchart.txt")
OUT = os.path.join(HERE, "figs_out")

# 字体候选：Windows优先 simsun.ttc（注意是 .ttc 不是 .ttf）
# 字体候选：按平台给多套路径，找不到就报清晰错误。
# 为什么必须是"全角 = 2 x 半角"的字体：ASCII 制表图靠这个比例才能逐字符对齐。
# 宋体 / 思源宋 / 文泉驿正字 都满足；等宽字体不满足（全角宽度不等于 2 倍半角）。
FONT_CANDIDATES = [
    # Windows
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simsun.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    # macOS
    "/System/Library/Fonts/Songti.ttc",
    "/System/Library/Fonts/STSong.ttc",
    "/Library/Fonts/Songti.ttc",
    # Linux（文泉驿 / Noto CJK / 思源宋）
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/sourcehanseranscn/SourceHanSansCN-Regular.otf",
]
# 容器里字体路径不固定时，可用环境变量指定首选字体
_env_font = os.environ.get("DMG_FLOWCHART_FONT")
if _env_font:
    FONT_CANDIDATES.insert(0, _env_font)

FS = 17# 字号
ASC = 9# 半角宽 px
LH = 24       # 行高
PAD = 18      # 内边距
MAXW = 1500# 单图最大宽（超出整体缩放）
DPI = 300

# 配色（浅色系，适配打印与浅色主题）
C_BOX = (95, 105, 120)      # 制表线 蓝灰
C_TEXT = (32, 38, 48)       # 正文
C_ACCENT = (176, 58, 46)    # 强调框╔═╗ 砖红
C_STAR = (150, 40, 30)      # ★ 标记
BG = (255, 255, 255)

BOX = "┌─┐└┘│├┤▼▲╔╗╚╝═║╠╣┬┴┼"


def is_wide(ch):
    return ord(ch) > 0x2E80


def dw(s):
    """显示宽度：全角计 2"""
    return sum(2 if is_wide(c) else 1 for c in s)


def load_font(size):
    from PIL import ImageFont
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=0)
            except Exception:
                pass
    raise RuntimeError(
        "找不到可用中文字体。候选：\n  " + "\n  ".join(FONT_CANDIDATES)
    )


def parse_figs(path):
    """解析图集文件，返回 [(name, lines)]"""
    text = open(path, encoding="utf-8").read()
    figs = []
    cur_name, cur_lines = None, []
    for line in text.split("\n"):
        m = re.match(r"^#\s*图\d+：(.+)$", line.strip())
        if m:
            if cur_name is not None:
                figs.append((cur_name, cur_lines))
            cur_name, cur_lines = m.group(1).strip(), []
            continue
        if cur_name is None:
            continue
        if re.match(r"^={20,}$", line.strip()):
            continue
        cur_lines.append(line.rstrip("\n"))
    if cur_name is not None:
        figs.append((cur_name, cur_lines))
    # 去掉尾部空行
    out = []
    for n, ls in figs:
        while ls and not ls[-1].strip():
            ls.pop()
        out.append((n, ls))
    return out


def render(name, lines, outdir, scale=1.0):
    from PIL import Image, ImageDraw
    if not lines:
        return None
    os.makedirs(outdir, exist_ok=True)
    nw = max(dw(l) for l in lines)
    W = nw * ASC + PAD * 2
    H = len(lines) * LH + PAD * 2
    auto = 1.0
    if W > MAXW:
        auto = MAXW / W
    s = auto * scale
    img = Image.new("RGB", (max(1, int(W * s)), max(1, int(H * s))), BG)
    d = ImageDraw.Draw(img)
    fnt = load_font(FS)
    for ri, line in enumerate(lines):
        y = (PAD + ri * LH) * s
        cx = PAD * s
        for ch in line:
            cw = (2 if is_wide(ch) else 1) * ASC
            if ch in "╔╗╚╝═║":
                col = C_ACCENT
            elif ch in BOX:
                col = C_BOX
            elif ch in "★☆":
                col = C_STAR
            else:
                col = C_TEXT
            if ch.strip():
                d.text((cx, y), ch, font=fnt, fill=col)
            cx += cw * s
    safe = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", name)[:40]
    path = os.path.join(outdir, "fig%02d_%s.png" % (len(os.listdir(outdir)) + 1, safe))
    img.save(path, dpi=(DPI, DPI))
    return path


def main():
    ap = argparse.ArgumentParser(description="3D-MG ASCII 流程图 → PNG")
    ap.add_argument("--index", type=int, help="只渲染指定序号（1 起）")
    ap.add_argument("--scale", type=float, default=1.0, help="放大倍数，默认 1.0")
    ap.add_argument("--out", default=OUT, help="输出目录")
    ap.add_argument("--list", action="store_true", help="列出所有图后退出")
    args = ap.parse_args()

    if not os.path.exists(SRC):
        print("找不到图集文件：%s" % SRC)
        sys.exit(1)
    figs = parse_figs(SRC)
    if args.list:
        for i, (n, ls) in enumerate(figs, 1):
            print("图%-3d %s  （%d 行）" % (i, n, len(ls)))
        return
    if args.index:
        if args.index < 1 or args.index > len(figs):
            print("序号超出范围（1—%d）" % len(figs))
            sys.exit(1)
        figs = [figs[args.index - 1]]
    for i, (n, ls) in enumerate(figs, 1):
        p = render(n, ls, args.out, args.scale)
        if p:
            print("图%-3d %-44s → %s" % (i, n[:44], os.path.basename(p)))
    print("\n共 %d 张，输出目录：%s" % (len(figs), os.path.abspath(args.out)))


if __name__ == "__main__":
    main()
