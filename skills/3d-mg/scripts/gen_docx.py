# -*- coding: utf-8 -*-
"""从 Markdown 源稿生成 3D-MG 排版规范的 Word 文档。

与 editor_sdk 路线的取舍：
  · editor_sdk（tencent-local-office-edit）：适合快速插入长文，但表格列宽/图形位置
    控制较粗，且两处对齐要靠返回值续接（易出错）
  · 本脚本：直接从 Markdown 构造 XML，表格列宽按内容平方根加权、全单元格左对齐、
    图形居中插入、**不依赖 Word 编号**（自渲染悬挂缩进）
  → 需要精确排版时用本脚本；只是插一插文字时用 editor_sdk 更快

用法：
    python gen_docx.py 源稿.md 输出.docx                    # 单文件
    python gen_docx.py a.md b.md c.md 输出.docx              # 多章合并（按顺序）
    python gen_docx.py --brief 源稿.md 简版.docx# 管理层简版（大字号大行距）

Markdown 支持：标题 / 段落 / 有序无序列表 / 表格 / 代码块（渲染为图片）/ 引用 /
             **粗体** / `等宽` / 水平分隔线（跳过）

【排版要点】
  · 表格列宽= TBL_W × (content_len^0.62) / Σ，避免长文本列吃掉整行
  · 全部单元格 jc=left（用户明确要求），表头底色 + tblHeader 跨页重复
  · 图形段落居中 + keepNext（仅图高 ≤11000 twips 时，防止图与标题分离）
  · 不用 Word 的 numPr 自动编号：多组列表会串号（1.→8.→9.），改为自渲染前缀
"""
import os
import re
import sys
import io
import json
import zipfile
import argparse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- 命名空间 ----------
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W, "r": RNS,
      "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture"}
for p, u in NS.items():
    ET.register_namespace(p, u)
NSDECL = " ".join('xmlns:%s="%s"' % (p, u) for p, u in NS.items())
Wq = "{%s}" % W

# ---------- 版面参数 ----------
PAGE_W, MAR_T, MAR_B, MAR_L, MAR_R = 11906, 1418, 1418, 1418, 1418
USABLE = PAGE_W - MAR_L - MAR_R
TBL_W = USABLE
MIN_COL = 760
EMU_PER_TWIP = 635
BOX = "┌─┐└┘│├┤▼▲╔╗╚╝═║╠╣┬┴┼"

# 正文版
NORMAL = dict(body=24, tbl=18, h1=36, h2=30, h3=26, line=360,
              accent="1F3864", accent2="2F5496", head_fill="E8EDF4",
              border="8FA0B8", before_h1=300)
# 管理层简版（大字号大行距，适合高层扫读）
BRIEF = dict(body=23, tbl=19, h1=40, h2=30, h3=25, line=350,
             accent="1F3864", accent2="2F5496", head_fill="DEE7F2",
             border="9AAFC8", before_h1=360)


def dw(s):
    """显示宽度：全角计 2"""
    return sum(2 if ord(c) > 0x2E80 else 1 for c in s)


def runs(text, sz, color=None, af="SimSun", ef="SimSun", bold_all=False):
    """解析 **粗体** 与 `等宽`，返回 run XML。★避免 ASCII 直引号，此处不处理。"""
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        b, mono = False, False
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            part = part[2:-2]; b = True
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            part = part[1:-1]; mono = True
        part = (part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        fn = "Consolas" if mono else af
        rpr = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>' % (fn, fn, ef)
        if b or bold_all:
            rpr += "<w:b/><w:bCs/>"
        if color:
            rpr += '<w:color w:val="%s"/>' % color
        rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz)
        out.append('<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>'
                   % (rpr, part))
    return "".join(out)


def parse_blocks(md):
    """把 Markdown 拆成块列表"""
    lines = md.split("\n")
    blocks, i, n = [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1; continue
        if re.match(r"^[-*_]{3,}$", s):          # 水平分隔线：跳过
            i += 1; continue
        if s.startswith("```"):                  # 代码块 → 图或等宽文本
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            txt = "\n".join(buf)
            blocks.append(("fig", txt) if sum(txt.count(c) for c in BOX) >= 3
                          else ("code", txt))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            blocks.append(("h", len(m.group(1)), m.group(2).strip())); i += 1; continue
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s\-:|]+\|$", lines[i+1].strip()):
            hdr = [c.strip() for c in s.strip("|").split("|")]
            rows = [hdr]; i += 2
            while i < n and lines[i].strip().startswith("|"):
                c = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if len(c) < len(hdr):
                    c += [""] * (len(hdr) - len(c))
                rows.append(c[:len(hdr)]); i += 1
            blocks.append(("tbl", rows)); continue
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip()); i += 1
            blocks.append(("quote", " ".join(x for x in buf if x))); continue
        if re.match(r"^[-*]\s+", s):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            blocks.append(("ul", items)); continue
        if re.match(r"^\d+[.、]\s+", s):
            items = []
            while i < n and re.match(r"^\s*\d+[.、]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.、]\s+", "", lines[i])); i += 1
            blocks.append(("ol", items)); continue
        buf = [s]; i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|\||```|>|[-*]\s|\d+[.、]\s)", lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        blocks.append(("p", " ".join(buf)))
    return blocks


def build_table(rows, P):
    """列宽平方根加权 + 全左对齐 + 表头跨页重复"""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    colmax = []
    for c in range(ncol):
        wm = 0
        for r in rows:
            txt = re.sub(r"\*\*|`", "", r[c])
            wm = max(wm, min(dw(txt), 56))
        colmax.append(max(wm, 3))
    wgt = [max(1.0, c ** 0.62) for c in colmax]
    tot = sum(wgt)
    raw = [max(MIN_COL, int(TBL_W * c / tot)) for c in wgt]
    raw[raw.index(max(raw))] += TBL_W - sum(raw)
    bd = "".join('<w:%s w:val="single" w:sz="4" w:space="0" w:color="%s"/>' % (s, P["border"])
                 for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    xml = ['<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/>'
           '<w:tblBorders>%s</w:tblBorders>'
           '<w:tblCellMar><w:top w:w="34" w:type="dxa"/><w:left w:w="76" w:type="dxa"/>'
           '<w:bottom w:w="34" w:type="dxa"/><w:right w:w="76" w:type="dxa"/></w:tblCellMar>'
           '</w:tblPr><w:tblGrid>' % (TBL_W, bd)
           + "".join('<w:gridCol w:w="%d"/>' % w for w in raw) + "</w:tblGrid>"]
    for ri, r in enumerate(rows):
        head = (ri == 0)
        trpr = "<w:trPr>" + ("<w:tblHeader/>" if head else "") + "</w:trPr>"
        xml.append("<w:tr>%s" % trpr)
        for ci, cell in enumerate(r):
            shd = ('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % P["head_fill"]) if head else ""
            cx = ""
            for k, seg in enumerate(cell.split("\n")):
                if k:
                    cx += "<w:r><w:br/></w:r>"
                cx += runs(seg, P["tbl"], color=P["accent"] if head else None, bold_all=head)
            if not cx:
                cx = runs("", P["tbl"])
            xml.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s'
                       '<w:vAlign w:val="center"/></w:tcPr>'
                       '<w:p><w:pPr><w:jc w:val="left"/>'
                       '<w:spacing w:before="28" w:after="28" w:line="250" w:lineRule="auto"/>'
                       '<w:ind w:firstLine="0" w:left="0"/></w:pPr>%s</w:p></w:tc>'
                       % (raw[ci], shd, cx))
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    xml.append('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="140" '
               'w:lineRule="auto"/><w:rPr><w:sz w:val="14"/></w:rPr></w:pPr></w:p>')
    return "".join(xml)


def build_fig_para(cx, cy, rid, idx, name, keep):
    keep_xml = "<w:keepNext/>" if keep else ""
    return (
        '<w:p><w:pPr><w:jc w:val="center"/>%s'
        '<w:spacing w:before="120" w:after="140" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:left="0"/>'
        '<w:pBdr><w:top w:val="single" w:sz="4" w:space="6" w:color="D0D8E4"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="6" w:color="D0D8E4"/></w:pBdr>'
        '<w:shd w:val="clear" w:color="auto" w:fill="FCFDFE"/></w:pPr>'
        '<w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="%d" name="Figure %d" descr="流程图"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
        % (keep_xml, cx, cy, 2000 + idx, idx, 2000 + idx, name, rid, cx, cy))


def build(src_files, dst, P=None, template=None):
    P = P or NORMAL
    body = []
    fig_slots = []     # (body_index, 待渲染的ASCII 文本)

    for path in src_files:
        md = open(path, encoding="utf-8").read()
        for b in parse_blocks(md):
            k = b[0]
            if k == "h":
                lvl, txt = b[1], b[2]
                if lvl == 1:
                    body.append(
                        '<w:p><w:pPr><w:jc w:val="left"/><w:keepNext/>'
                        '<w:spacing w:before="%d" w:after="%d" w:line="300" w:lineRule="auto"/>'
                        '<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="8" w:color="%s"/></w:pBdr>'
                        '<w:ind w:firstLine="0" w:left="0"/>'
                        '<w:rPr><w:rFonts w:ascii="SimHei" w:hAnsi="SimHei" w:eastAsia="SimHei"/>'
                        '<w:color w:val="%s"/><w:sz w:val="%d"/></w:rPr></w:pPr>%s</w:p>'
                        % (P["before_h1"], P["before_h1"] * 2 // 3, P["accent"],
                           P["accent"], P["h1"],
                           runs(txt, P["h1"], af="SimHei", ef="SimHei", color=P["accent"])))
                else:
                    sz = P["h2"] if lvl == 2 else P["h3"]
                    col = P["accent"] if lvl == 2 else P["accent2"]
                    body.append(
                        '<w:p><w:pPr><w:jc w:val="left"/><w:keepNext/>'
                        '<w:spacing w:before="%d" w:after="140" w:line="290" w:lineRule="auto"/>'
                        '<w:ind w:firstLine="0" w:left="0"/>'
                        '<w:rPr><w:rFonts w:ascii="SimHei" w:hAnsi="SimHei" w:eastAsia="SimHei"/>'
                        '<w:color w:val="%s"/><w:sz w:val="%d"/></w:rPr></w:pPr>%s</w:p>'
                        % (300 if lvl == 2 else 200, col, sz,
                           runs(txt, sz, af="SimHei", ef="SimHei", color=col)))
            elif k == "p":
                if b[1].strip() in ("[图占位]", "[分页]"):
                    if b[1].strip() == "[分页]":
                        body.append('<w:p><w:pPr><w:spacing w:before="0" w:after="0" '
                                    'w:line="240" w:lineRule="auto"/><w:rPr><w:sz w:val="2"/></w:rPr>'
                                    '</w:pPr><w:r><w:br w:type="page"/></w:r></w:p>')
                    else:
                        fig_slots.append((len(body), None))
                        body.append("@@SLOT@@")
                    continue
                body.append(
                    '<w:p><w:pPr><w:jc w:val="both"/>'
                    '<w:spacing w:before="70" w:after="70" w:line="%d" w:lineRule="auto"/>'
                    '<w:ind w:firstLine="440" w:left="0"/></w:pPr>%s</w:p>'
                    % (P["line"], runs(b[1], P["body"])))
            elif k == "quote":
                body.append(
                    '<w:p><w:pPr><w:jc w:val="left"/>'
                    '<w:pBdr><w:left w:val="single" w:sz="20" w:space="8" w:color="%s"/></w:pBdr>'
                    '<w:shd w:val="clear" w:color="auto" w:fill="F2F6FB"/>'
                    '<w:spacing w:before="100" w:after="100" w:line="320" w:lineRule="auto"/>'
                    '<w:ind w:firstLine="0" w:left="200"/></w:pPr>%s</w:p>'
                    % (P["accent"], runs(b[1], P["body"], color=P["accent"])))
            elif k in ("ul", "ol"):
                for idx, it in enumerate(b[1], 1):
                    if k == "ol":
                        pref, ind_l, col = "%d. " % idx, 420, P["accent2"]
                    else:
                        pref, ind_l, col = "• ", 360, "6B7B90"
                    body.append(
                        '<w:p><w:pPr><w:jc w:val="left"/>'
                        '<w:spacing w:before="24" w:after="24" w:line="320" w:lineRule="auto"/>'
                        '<w:ind w:left="%d" w:hanging="240" w:firstLine="0"/>'
                        '<w:contextualSpacing/></w:pPr>%s%s</w:p>'
                        % (ind_l, runs(pref, P["body"], color=col), runs(it, P["body"])))
            elif k == "tbl":
                body.append(build_table(b[1], P))
            elif k == "fig":
                fig_slots.append((len(body), b[1]))
                body.append("@@SLOT@@")
            elif k == "code":
                for line in b[1].split("\n"):
                    if not line.strip():
                        body.append('<w:p><w:pPr><w:spacing w:before="0" w:after="0" '
                                    'w:line="200" w:lineRule="auto"/>'
                                    '<w:ind w:firstLine="0" w:left="200"/></w:pPr></w:p>')
                        continue
                    body.append(
                        '<w:p><w:pPr><w:jc w:val="left"/>'
                        '<w:shd w:val="clear" w:color="auto" w:fill="F7F7F7"/>'
                        '<w:spacing w:before="0" w:after="0" w:line="260" w:lineRule="auto"/>'
                        '<w:ind w:firstLine="0" w:left="120"/></w:pPr>%s</w:p>'
                        % runs(line, 19, af="Consolas"))

    # ---- 渲染图形 ----
    import tempfile
    from PIL import Image
    tmpdir = tempfile.mkdtemp(prefix="mgdocx_")
    media, rels_xml, rid_i = [], [], 0
    rel_items = []
    n_fig = 0
    for slot_i, txt in fig_slots:
        n_fig += 1
        # 渲染 ASCII
        png_path = os.path.join(tmpdir, "fig%02d.png" % n_fig)
        if txt is not None:
            render_ascii(txt, png_path)
        else:
            # [图占位]：优先用 env FIG_ASSET 指定的定制图，否则用默认主网络图
            custom = os.environ.get("FIG_ASSET")
            src = custom or os.path.join(HERE, "..", "assets", "01_完整线性因果网络图.png")
            if not os.path.exists(src):
                raise SystemExit("找不到图占位用的图片：%s" % src)
            png_path = src
        img = Image.open(png_path)
        w_px, h_px = img.size
        dw_ = int(USABLE * 0.92)
        dh_ = int(dw_ * h_px / w_px)
        MAXH = 12800
        if dh_ > MAXH:
            dh_ = MAXH; dw_ = int(dh_ * w_px / h_px)
        cx, cy = dw_ * EMU_PER_TWIP, dh_ * EMU_PER_TWIP
        data = open(png_path, "rb").read()
        name = "fig%02d.png" % n_fig
        media.append(("word/media/" + name, data))
        rid_i += 1
        rid = "rId%d" % (9000 + rid_i)
        rel_items.append((rid, "media/" + name))
        keep = dh_ <= 11000
        body[slot_i] = build_fig_para(cx, cy, rid, n_fig, name, keep)

    left = sum(1 for x in body if isinstance(x, str) and x.startswith("@@SLOT"))
    assert left == 0, "残留图槽 %d" % left

    # ---- 打包 ----
    if template and os.path.exists(template):
        z = zipfile.ZipFile(template)
        items = z.infolist()
        data_map = {i.filename: z.read(i.filename) for i in items}
        z.close()
    else:
        items = []
        data_map = {}

    rels = data_map.get("word/_rels/document.xml.rels") or (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    ).encode("utf-8")
    rroot = ET.fromstring(rels)
    RELNS = "http://schemas.openxmlformats.org/package/2006/relationships"
    ET.register_namespace("", RELNS)
    for rid, tgt in rel_items:
        r = ET.SubElement(rroot, "{%s}Relationship" % RELNS)
        r.set("Id", rid)
        r.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
        r.set("Target", tgt)

    sect = ('<w:sectPr><w:pgSz w:w="%d" w:h="16838"/>'
            '<w:pgMar w:top="%d" w:right="%d" w:bottom="%d" w:left="%d" '
            'w:header="851" w:footer="992" w:gutter="0"/>'
            '<w:cols w:space="720"/><w:docGrid w:linePitch="312"/></w:sectPr>'
            % (PAGE_W, MAR_T, MAR_R, MAR_B, MAR_L))
    doc_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
               '<w:document %s><w:body>%s%s</w:body></w:document>'
               % (NSDECL, "".join(body), sect))

    # styles.xml：没有就建一个最小可用的
    if "word/styles.xml" not in data_map:
        data_map["word/styles.xml"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="%s"><w:docDefaults><w:rPrDefault><w:rPr>'
            '<w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="SimSun" w:cs="SimSun"/>'
            '<w:sz w:val="%d"/><w:szCs w:val="%d"/>'
            '</w:rPr></w:rPrDefault><w:pPrDefault/></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>'
            % (W, P["body"], P["body"])).encode("utf-8")

    # ---- 包级关系 _rels/.rels（缺它 Word/WPS 打不开）----
    data_map["_rels/.rels"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
        'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>').encode("utf-8")
    if "docProps/core.xml" not in data_map:
        data_map["docProps/core.xml"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
            'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/'
            'XMLSchema-instance">'
            '<dc:title>3D-MG 文档</dc:title><dc:creator>WorkBuddy</dc:creator>'
            '<cp:lastModifiedBy>WorkBuddy</cp:lastModifiedBy>'
            '</cp:coreProperties>').encode("utf-8")
    if "docProps/app.xml" not in data_map:
        data_map["docProps/app.xml"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
            'extended-properties" xmlns:vt="http://schemas.openxmlformats.org/'
            'officeDocument/2006/docPropsVTypes">'
            '<Application>WorkBuddy</Application></Properties>').encode("utf-8")

    ct = data_map.get("[Content_Types].xml")
    if ct:
        s = ct.decode("utf-8")
        s = re.sub(r'<Override PartName="/word/media/[^"]*"[^>]*/>', "", s)
        if 'Extension="png"' not in s:
            s = re.sub(r'(<Types[^>]*>)',
                       r'\1<Default Extension="png" ContentType="image/png"/>', s, count=1)
        add = ""
        if "core-properties+xml" not in s:
            add += ('<Override PartName="/docProps/core.xml" ContentType="application/'
                    'vnd.openxmlformats-package.core-properties+xml"/>')
        if "extended-properties+xml" not in s:
            add += ('<Override PartName="/docProps/app.xml" ContentType="application/'
                    'vnd.openxmlformats-officedocument.extended-properties+xml"/>')
        if add:
            s = s.replace("</Types>", add + "</Types>")
        data_map["[Content_Types].xml"] = s.encode("utf-8")
    else:
        data_map["[Content_Types].xml"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>').encode("utf-8")

    data_map["word/document.xml"] = doc_xml.encode("utf-8")
    data_map["word/_rels/document.xml.rels"] = ET.tostring(rroot, encoding="UTF-8",
                                                          xml_declaration=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zo:
        for n, b in data_map.items():
            if n.startswith("word/media/"):     # 丢弃旧媒体
                continue
            zo.writestr(n, b)
        for n, b in media:
            zo.writestr(n, b)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    open(dst, "wb").write(buf.getvalue())

    # 清理临时目录
    import shutil
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass
    return {"tables": sum(1 for x in body if "<w:tbl>" in str(x)), "figs": n_fig,
            "bytes": os.path.getsize(dst)}


def render_ascii(text, outpath):
    """ASCII 制表图 → PNG（SimSun 逐字符定位，保证框线对齐）"""
    sys.path.insert(0, HERE)
    try:
        import gen_flowchart as G
    except Exception:
        # 脚本不可用时退化：原样写入占位
        open(outpath, "wb").write(b"")
        return
    lines = [l.rstrip("\n") for l in text.rstrip("\n").split("\n")]
    G.render("fig", lines, os.path.dirname(outpath),
             scale=1.0)  # 渲染到临时目录
    # G.render 生成的带序号文件名，取最新
    d = os.path.dirname(outpath)
    cands = sorted([os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")],
                   key=os.path.getmtime)
    if cands and os.path.abspath(cands[-1]) != os.path.abspath(outpath):
        try:
            os.replace(cands[-1], outpath)
        except Exception:
            open(outpath, "wb").write(open(cands[-1], "rb").read())


def main():
    ap = argparse.ArgumentParser(description="Markdown → 3D-MG 规范 Word")
    ap.add_argument("inputs", nargs="+", help="源稿.md（多个按顺序合并）")
    ap.add_argument("output", help="输出.docx")
    ap.add_argument("--brief", action="store_true", help="管理层简版样式")
    ap.add_argument("--template", help="复用已有 docx 的 styles/theme")
    a = ap.parse_args()
    P = BRIEF if a.brief else NORMAL
    r = build(a.inputs, a.output, P, a.template)
    print("已生成：%s" % os.path.abspath(a.output))
    print("  表格 %d ｜ 图形 %d ｜ 大小 %.1f KB"
          % (r["tables"], r["figs"], r["bytes"] / 1024))


if __name__ == "__main__":
    main()
