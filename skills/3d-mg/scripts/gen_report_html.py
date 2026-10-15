#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3D-MG 自适应 HTML 汇报文档生成器
============================================================
把行式 DSL（@HERO/@CARD/@KPI/@TABLE/@ROW/@LI/@CHAIN/@NOTE）渲染成
一份自包含的 HTML：窄屏（≤768px）竖向单列，宽屏（≥769px）横向两栏，
自带「强制横向 / 强制竖向 / 恢复自动」切换按钮 + localStorage 记忆。

格式规范见 references/report_format.md（唯一权威定义）。
小程序里的 utils/report-html.js 是同一规范的 JS 移植版，两边行为对齐。

用法：
    python3 gen_report_html.py 输入.dsl -o 输出.html
    python3 gen_report_html.py 输入.dsl -o 输出.html --title "公司名（代码）"
    echo "@HERO A | B | C" | python3 gen_report_html.py - -o out.html

DSL 每行一个动作，行首 @ 开头（大小写不敏感），字段用 | 分隔。
模型写歪时能容错：直接写 Markdown 表格（| a | b |）或 ## 标题也可解析。
"""
import argparse
import io
import json
import os
import re
import sys

# ------------------------------------------------------------
# 一、DSL → 结构化块
# ------------------------------------------------------------

def _clean(s):
    """清掉行内 Markdown 标记，保留纯文本。"""
    s = '' if s is None else str(s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
    return s.replace('`', '').strip()


def _split(s):
    return [x.strip() for x in str('' if s is None else s).split('|')]


_TAG_RE = re.compile(r'^\s*@([A-Za-z]+)[\s:：]*(.*)$')
_HEAD_RE = re.compile(r'^\s*(#{1,6})\s+(.*)$')


def parse_blocks(raw):
    """解析 DSL，返回 [{type:'hero'|'card', label, title, sub, items, k, wide}]"""
    text = '' if raw is None else str(raw)
    lines = text.split('\n')
    out = []
    state = {'cur': None, 'table': None, 'md': []}

    def new_card(label, title):
        c = {'type': 'card', 'label': label, 'title': title, 'sub': '', 'items': []}
        c['k'] = 'c%d' % len(out)
        out.append(c)
        state['cur'] = c
        state['table'] = None
        return c

    def push(item):
        if state['cur'] is None:
            new_card('', '')
        item['k'] = 'k%d_%d' % (len(out), len(state['cur']['items']))
        state['cur']['items'].append(item)
        return item

    def flush_md():
        if not state['md']:
            return
        head = state['md'][0]
        rows = state['md'][1:]
        t = push({'t': 'table', 'head': head, 'rows': rows})
        state['md'] = []
        state['table'] = t

    for line in lines:
        line = re.sub(r'\s+$', '', line)
        if not line.strip():
            flush_md()
            continue

        m = _TAG_RE.match(line)

        # 容错：模型直接写 Markdown 表格
        if m is None and re.match(r'^\s*\|', line):
            cells = [_clean(c) for c in
                     re.sub(r'^\s*\|', '', line).rstrip().rstrip('|').split('|')]
            if not all(re.match(r'^:?-{2,}:?$', c) for c in cells):
                state['md'].append(cells)
            continue
        flush_md()

        # 容错：模型直接写 Markdown 标题
        if m is None:
            mh = _HEAD_RE.match(line)
            if mh:
                t = _clean(mh.group(2))
                parts = re.split(r'[｜|]', t)
                new_card(_clean(parts[0]) if len(parts) > 1 else '',
                         _clean('｜'.join(parts[1:])) if len(parts) > 1 else t)
                continue

        # 非 DSL 行当段落
        if m is None:
            push({'t': 'p', 'text': _clean(line)})
            continue

        tag = m.group(1).upper()
        body = m.group(2)

        if tag == 'HERO':
            hp = _split(body)
            hero = {
                'type': 'hero', 'label': _clean(hp[0]) if hp else '',
                'title': _clean(hp[1]) if len(hp) > 1 else '',
                'sub': _clean(hp[2]) if len(hp) > 2 else '',
                'items': []
            }
            hero['k'] = 'h%d' % len(out)
            out.append(hero)
            state['cur'] = hero
            state['table'] = None

        elif tag == 'CARD':
            cp = _split(body)
            new_card(_clean(cp[0]) if len(cp) > 1 else '',
                     _clean('｜'.join(cp[1:])) if len(cp) > 1 else _clean(cp[0]))

        elif tag == 'SUB':
            if state['cur']:
                state['cur']['sub'] = _clean(body)

        elif tag == 'P':
            push({'t': 'p', 'text': _clean(body)})

        elif tag == 'KPI':
            kp = _split(body)
            push({'t': 'kpi',
                  'v': _clean(kp[0]) if kp else '',
                  'n': _clean(kp[1]) if len(kp) > 1 else '',
                  'd': _clean(kp[2]) if len(kp) > 2 else ''})

        elif tag == 'TABLE':
            state['table'] = push({'t': 'table',
                                   'head': [_clean(c) for c in _split(body)],
                                   'rows': []})

        elif tag == 'ROW':
            row = [_clean(c) for c in _split(body)]
            if state['table'] and state['table']['t'] == 'table':
                state['table']['rows'].append(row)
            else:
                state['table'] = push({'t': 'table', 'head': [], 'rows': [row]})

        elif tag == 'LI':
            push({'t': 'li', 'text': _clean(body)})

        elif tag == 'NOTE':
            np_ = _split(body)
            if len(np_) > 1:
                push({'t': 'note', 'mark': _clean(np_[0]),
                      'text': _clean('｜'.join(np_[1:]))})
            else:
                push({'t': 'note', 'mark': '★', 'text': _clean(np_[0])})

        elif tag == 'CHAIN':
            chp = _split(body)
            flow = _clean('｜'.join(chp[1:])) if len(chp) > 1 else _clean(chp[0])
            steps = [s for s in re.split(r'\s*(?:→|->|➜)\s*', flow) if s]
            push({'t': 'chain',
                  'name': _clean(chp[0]) if len(chp) > 1 else '',
                  'flow': flow, 'steps': steps})

        else:
            # 未知标记：当段落，不丢内容
            push({'t': 'p', 'text': _clean(line)})

    flush_md()
    _mark_wide(out)
    return out


def _mark_wide(blocks):
    """通栏判定：小程序与 HTML 共用同一套规则（见 references/report_format.md）。"""
    for b in blocks:
        if b['type'] == 'hero':
            b['wide'] = True
            continue
        items = b['items']
        tables = [i for i in items if i['t'] == 'table']
        wide = False
        if len(tables) >= 2:
            wide = True
        if any(len(t['head']) >= 5 for t in tables):
            wide = True
        if any(len(t['rows']) >= 8 for t in tables):
            wide = True
        if any(i['t'] == 'chain' for i in items):
            wide = True
        if re.search(r'封面|摘要|总览|因果链|三段归因|结论|方法论|优先级|情景',
                     b['title'] or b['label'] or ''):
            wide = True
        b['wide'] = wide


def stats(blocks):
    s = {'cards': 0, 'tables': 0, 'kpis': 0, 'notes': 0, 'chains': 0}
    for b in blocks:
        s['cards'] += 1
        for i in b['items']:
            if i['t'] == 'table':
                s['tables'] += 1
            elif i['t'] == 'kpi':
                s['kpis'] += 1
            elif i['t'] == 'note':
                s['notes'] += 1
            elif i['t'] == 'chain':
                s['chains'] += 1
    return s


# ------------------------------------------------------------
# 二、HTML 模板（窄屏单列 / 宽屏两栏，视图可手动切换）
# ------------------------------------------------------------

_CSS = """
*{margin:0;padding:0;box-sizing:border-box;-webkit-text-size-adjust:100%;}
body{background:#f4f6fa;color:#16203a;line-height:1.65;font-size:15px;
  font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  padding:16px 14px 40px;}
.wrap{max-width:1400px;margin:0 auto;}
.bar{max-width:1400px;margin:0 auto 14px;display:flex;flex-wrap:wrap;gap:10px;
  align-items:center;justify-content:space-between;}
.bar .status{font-size:13px;color:#4d5875;}
.bar .status b{color:#2b6cb0;}
.btn{border:1px solid #dbe2ee;background:#fff;color:#2b6cb0;border-radius:8px;
  padding:7px 14px;font-size:13px;cursor:pointer;font-family:inherit;}
.btn:hover{background:#f2f6fd;}
.btn.primary{background:#2b6cb0;border-color:#2b6cb0;color:#fff;}
.btn.primary:hover{background:#1f4680;}
.grid{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start;}
.grid>.card,.grid>.hero{flex:1 1 100%;min-width:0;}
.hero{padding:26px 22px 24px;border-radius:14px;
  background:linear-gradient(135deg,#1f4680,#2b6cb0);color:#fff;
  box-shadow:0 6px 20px rgba(31,70,128,.18);}
.hero .kicker{font-size:12px;letter-spacing:3px;opacity:.82;margin-bottom:8px;}
.hero .t{font-size:28px;font-weight:700;line-height:1.3;}
.hero .s{font-size:16px;margin-top:8px;opacity:.95;}
.hero .x{font-size:13px;margin-top:14px;padding-top:12px;
  border-top:1px solid rgba(255,255,255,.25);opacity:.88;}
.card{background:#fff;border:1px solid #e5e9f2;border-radius:14px;
  padding:16px 16px 18px;box-shadow:0 2px 10px rgba(22,32,58,.05);}
.card .hd{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:4px;}
.card .lb{font-size:12px;font-weight:600;color:#2b6cb0;
  background:rgba(47,91,216,.1);border-radius:5px;padding:2px 9px;}
.card .ttl{font-size:18px;font-weight:700;color:#16203a;line-height:1.4;}
.card .sub{font-size:13px;color:#8b93a8;margin-bottom:4px;}
.bd{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;align-items:stretch;}
.kpi{flex:1 1 calc(50% - 5px);min-width:0;background:#f7f9fc;
  border-radius:10px;padding:11px 12px;}
.kpi .v{font-size:22px;font-weight:700;color:#2b6cb0;line-height:1.2;word-break:break-all;}
.kpi .n{font-size:13px;color:#4d5875;margin-top:3px;font-weight:600;}
.kpi .d{font-size:12px;color:#8b93a8;margin-top:2px;}
.tbwrap{flex:1 1 100%;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch;}
table{width:100%;border-collapse:collapse;min-width:100%;}
th,td{border:1px solid #e5e9f2;padding:8px 10px;font-size:13px;
  text-align:left;vertical-align:top;line-height:1.55;}
th{background:#edf2f7;color:#16203a;font-weight:700;white-space:nowrap;}
td{color:#4d5875;}
.li{flex:1 1 100%;display:flex;gap:8px;align-items:flex-start;}
.li .dot{flex:none;color:#2b6cb0;font-weight:700;}
.li .tx{flex:1;font-size:14px;color:#4d5875;}
.p{flex:1 1 100%;font-size:14px;color:#4d5875;line-height:1.75;}
.chain{flex:1 1 100%;background:#f7f9fc;border-left:3px solid #5b7cea;
  border-radius:0 8px 8px 0;padding:11px 12px;}
.chain .cn{font-size:13px;font-weight:700;color:#2b6cb0;margin-bottom:7px;}
.chain .cf{display:flex;flex-wrap:wrap;align-items:center;gap:6px;}
.chain .cs{font-size:13px;color:#16203a;background:#fff;border:1px solid #e5e9f2;
  border-radius:6px;padding:3px 9px;}
.chain .ca{color:#5b7cea;font-weight:700;}
.note{flex:1 1 100%;display:flex;gap:8px;align-items:flex-start;
  background:#fdf8ee;border:1px solid #ecd9b4;border-radius:8px;padding:10px 12px;}
.note .mk{flex:none;font-size:12px;font-weight:700;color:#9a6b16;
  background:#f6e8cd;border-radius:5px;padding:1px 8px;}
.note .tx{flex:1;font-size:13.5px;color:#7a5a1c;}
@media (min-width:769px){
  body{padding:24px 24px 60px;}
  .grid{gap:20px;}
  .grid>.card{flex:1 1 calc(50% - 10px);}
  .grid>.card.wide,.grid>.hero{flex:1 1 100%;}
  .kpi{flex:1 1 calc(25% - 8px);}
  .hero{padding:36px 34px 32px;}
  .hero .t{font-size:34px;}
  .card{padding:20px 22px 22px;}
  .card .ttl{font-size:19px;}
}
@media (max-width:480px){
  th,td{padding:6px 7px;font-size:12px;}
  th{white-space:normal;}
  .kpi .v{font-size:20px;}
  .hero .t{font-size:23px;}
}
@media print{.bar{display:none;}body{background:#fff;padding:0;}
  .card,.hero{box-shadow:none;break-inside:avoid;}}
.grid.force-landscape{display:flex !important;flex-wrap:wrap !important;gap:20px !important;}
.grid.force-landscape>.card{flex:1 1 calc(50% - 10px) !important;}
.grid.force-landscape>.card.wide,.grid.force-landscape>.hero{flex:1 1 100% !important;}
.grid.force-landscape .kpi{flex:1 1 calc(25% - 8px) !important;}
.grid.force-portrait{display:flex !important;flex-direction:column !important;gap:16px !important;}
.grid.force-portrait>.card,.grid.force-portrait>.hero{flex:1 1 auto !important;}
.grid.force-portrait .kpi{flex:1 1 calc(50% - 5px) !important;}
"""

_JS = """
(function(){
  var FALLBACK = "__REPORT_JSON__";
  var raw = document.getElementById("report-data").textContent.trim();
  var data;
  if (!raw || raw === FALLBACK) { data = JSON.parse(document.getElementById("demo-data").textContent); }
  else { try { data = JSON.parse(raw); } catch (e) { data = null; } }
  if (!data) return;
  if (data.title) document.title = data.title;
  function el(tag, cls, text){
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }
  function buildCard(b){
    var root = el("div", (b.type === "hero" ? "hero" : "card") + (b.wide ? " wide" : ""));
    if (b.type === "hero") {
      root.appendChild(el("div","kicker","3D-MG \\u00b7 \\u4e09\\u7ef4\\u955c\\u50cf\\u6cbb\\u7406\\u6cd5"));
      root.appendChild(el("div","t", b.label || ""));
      if (b.title) root.appendChild(el("div","s", b.title));
      if (b.sub) root.appendChild(el("div","x", b.sub));
      return root;
    }
    if (b.label || b.title) {
      var hd = el("div","hd");
      if (b.label) hd.appendChild(el("span","lb", b.label));
      if (b.title) hd.appendChild(el("div","ttl", b.title));
      root.appendChild(hd);
    }
    if (b.sub) root.appendChild(el("div","sub", b.sub));
    var bd = el("div","bd");
    (b.items || []).forEach(function(it){ if (it) bd.appendChild(buildItem(it)); });
    root.appendChild(bd);
    return root;
  }
  function buildItem(it){
    if (it.t === "kpi") {
      var k = el("div","kpi");
      k.appendChild(el("div","v", it.v || ""));
      if (it.n) k.appendChild(el("div","n", it.n));
      if (it.d) k.appendChild(el("div","d", it.d));
      return k;
    }
    if (it.t === "table") {
      var w = el("div","tbwrap"), t = el("table");
      var head = it.head || [];
      var cols = Math.max(head.length, (it.rows || []).reduce(function(m,r){
        return Math.max(m,(r||[]).length);},0));
      if (head.length) {
        var tr = el("tr");
        for (var i=0;i<cols;i++) tr.appendChild(el("th",null,head[i]||""));
        var th = el("thead"); th.appendChild(tr); t.appendChild(th);
      }
      var tb = el("tbody");
      (it.rows || []).forEach(function(r){
        var tr2 = el("tr");
        for (var j=0;j<cols;j++) tr2.appendChild(el("td",null,(r&&r[j])||""));
        tb.appendChild(tr2);
      });
      t.appendChild(tb); w.appendChild(t); return w;
    }
    if (it.t === "li") {
      var li = el("div","li");
      li.appendChild(el("span","dot","\\u00b7"));
      li.appendChild(el("span","tx", it.text || ""));
      return li;
    }
    if (it.t === "note") {
      var nt = el("div","note");
      nt.appendChild(el("span","mk", it.mark || "\\u2605"));
      nt.appendChild(el("span","tx", it.text || ""));
      return nt;
    }
    if (it.t === "chain") {
      var c = el("div","chain");
      if (it.name) c.appendChild(el("div","cn", it.name));
      var cf = el("div","cf");
      var steps = (it.steps && it.steps.length) ? it.steps : [it.flow || ""];
      steps.forEach(function(s,i){
        cf.appendChild(el("span","cs", s));
        if (i < steps.length-1) cf.appendChild(el("span","ca","\\u2192"));
      });
      c.appendChild(cf);
      return c;
    }
    return el("div","p", it.text || "");
  }
  var grid = document.getElementById("grid");
  (data.blocks || []).forEach(function(b){ grid.appendChild(buildCard(b)); });
  if (data.footer) {
    var f = el("div","p");
    f.style.marginTop="6px"; f.style.fontSize="12px"; f.style.color="#8b93a8";
    f.textContent = data.footer;
    grid.appendChild(f);
  }
  var KEY = "3dmg_view_mode";
  var status = document.getElementById("status");
  function apply(mode){
    grid.classList.remove("force-landscape","force-portrait");
    if (mode === "force-landscape") grid.classList.add("force-landscape");
    if (mode === "force-portrait") grid.classList.add("force-portrait");
    status.innerHTML = "\\u5f53\\u524d\\u89c6\\u56fe\\uff1a<b>" + (
      mode === "force-landscape" ? "\\u5f3a\\u5236\\u6a2a\\u5411\\uff08\\u53cc\\u680f\\uff09" :
      mode === "force-portrait" ? "\\u5f3a\\u5236\\u7ad6\\u5411\\uff08\\u5355\\u5217\\uff09" :
      "\\u81ea\\u52a8\\u9002\\u914d") + "</b>";
    try { if (mode) localStorage.setItem(KEY,mode); else localStorage.removeItem(KEY); } catch(e){}
  }
  document.getElementById("bLand").onclick = function(){ apply("force-landscape"); };
  document.getElementById("bPort").onclick = function(){ apply("force-portrait"); };
  document.getElementById("bAuto").onclick = function(){ apply(null); };
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch(e){}
  apply(saved);
})();
"""

_DEMO = {
    "title": "3D-MG 诊断报告 · 版式示例",
    "blocks": [
        {"type": "hero", "label": "示例公司（000000.SH）", "wide": True,
         "title": "核心痛点诊断与经营决策推演",
         "sub": "现状镜像 → 因果镜像 → 推演镜像　·　本页为版式示例，公司与数字均为虚构"},
        {"type": "card", "label": "摘要", "title": "一句话结论与三大痛点", "wide": True,
         "items": [
             {"t": "p", "text": "不是「毛利不够」，是「毛利增速追不上费用增速 + 三条结构性失血点同时开着」。"},
             {"t": "kpi", "v": "13.2%", "n": "费用率", "d": "高于毛利率 11.8%"},
             {"t": "kpi", "v": "4.5 亿", "n": "经营缺口", "d": "占归母亏损 70%"},
             {"t": "kpi", "v": "48%", "n": "产能利用率", "d": "近半产能折旧空转"},
             {"t": "note", "mark": "★", "text": "「营收增、利润亏、销量降」并存，必须拆开看。"}
         ]},
        {"type": "card", "label": "因果链", "title": "外生冲击 → 三条失血链 → 断点",
         "items": [{"t": "chain", "name": "链① 销量失血",
                    "flow": "销量 -3.1% → 固定成本无法摊薄 → 产能利用率 48%",
                    "steps": ["销量 -3.1%", "固定成本无法摊薄", "产能利用率 48%"]}]}
    ],
    "footer": "本报告基于公开信息整理，不构成投资建议。"}

# 注：内置示例的公司与数字均为虚构，仅用于演示版式，不代表任何具体企业。


def _esc(s):
    return (str('' if s is None else s)
            .replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _jsafe(obj):
    """JSON 里转义 </，避免提前闭合 script 标签。"""
    return json.dumps(obj, ensure_ascii=False).replace('</', '<\\/')


def build_html(content, title='', footer=''):
    """content 可以是 DSL 文本，也可以是已解析的 blocks 列表。"""
    blocks = content if isinstance(content, list) else parse_blocks(content)
    payload = {'title': title or '3D-MG 诊断报告',
               'blocks': blocks,
               'footer': footer or ''}
    data_js = _jsafe(payload)
    demo_js = _jsafe(_DEMO)
    js = _JS.replace('__REPORT_JSON__', '__REPORT_JSON__')
    doc = []
    doc.append('<!DOCTYPE html>')
    doc.append('<html lang="zh-CN">')
    doc.append('<head>')
    doc.append('<meta charset="UTF-8">')
    doc.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    doc.append('<title>%s</title>' % _esc(payload['title']))
    doc.append('<style>%s</style>' % _CSS)
    doc.append('</head>')
    doc.append('<body>')
    doc.append('<div class="bar">')
    doc.append('  <div class="status" id="status">当前视图：<b>自动适配</b></div>')
    doc.append('  <div>')
    doc.append('    <button class="btn primary" id="bLand">强制横向（双栏）</button>')
    doc.append('    <button class="btn" id="bPort">强制竖向（单列）</button>')
    doc.append('    <button class="btn" id="bAuto">恢复自动适配</button>')
    doc.append('  </div>')
    doc.append('</div>')
    doc.append('<div class="wrap"><div class="grid" id="grid"></div></div>')
    doc.append('<script id="report-data" type="application/json">%s</script>' % data_js)
    doc.append('<script id="demo-data" type="application/json">%s</script>' % demo_js)
    doc.append('<script>%s</script>' % js)
    doc.append('</body>')
    doc.append('</html>')
    return '\n'.join(doc)


def to_plain_text(blocks, title=''):
    out = []
    if title:
        out.append(title)
        out.append('')
    for b in blocks:
        if b['type'] == 'hero':
            out.append('■ ' + ' '.join([x for x in [b['label'], b['title']] if x]))
            if b['sub']:
                out.append('  ' + b['sub'])
            out.append('')
            continue
        out.append('■ ' + ' ｜ '.join([x for x in [b['label'], b['title']] if x]))
        if b['sub']:
            out.append('  ' + b['sub'])
        for it in b['items']:
            if it['t'] == 'p':
                out.append('  ' + it['text'])
            elif it['t'] == 'kpi':
                out.append('  · ' + ' ｜ '.join([x for x in [it['v'], it['n'], it['d']] if x]))
            elif it['t'] == 'li':
                out.append('  - ' + it['text'])
            elif it['t'] == 'note':
                out.append('  ' + (it.get('mark') or '★') + ' ' + it['text'])
            elif it['t'] == 'chain':
                out.append('  ' + (it['name'] + '：' if it.get('name') else '') + it['flow'])
            elif it['t'] == 'table':
                head = it['head'] or []
                rows = it['rows'] or []
                cols = max([len(head)] + [len(r) for r in rows]) if rows else len(head)
                widths = [0] * cols
                for r in [head] + rows:
                    for i, c in enumerate(r[:cols]):
                        widths[i] = max(widths[i], _dw(c))
                if head:
                    out.append('  ' + '  '.join(_pad(head[i] if i < len(head) else '', widths[i])
                                                for i in range(cols)))
                    out.append('  ' + '  '.join('─' * widths[i] for i in range(cols)))
                for r in rows:
                    out.append('  ' + '  '.join(_pad(r[i] if i < len(r) else '', widths[i])
                                                for i in range(cols)))
        out.append('')
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()


def _dw(s):
    """显示宽度：中文按 2 列算。"""
    w = 0
    for ch in str(s or ''):
        o = ord(ch)
        w += 2 if (0x1100 <= o <= 0x115f or 0x2e80 <= o <= 0xa4cf or
                   0xac00 <= o <= 0xd7a3 or 0xf900 <= o <= 0xfaff or
                   0xfe30 <= o <= 0xfe6f or 0xff00 <= o <= 0xff60 or
                   0xffe0 <= o <= 0xffe6) else 1
    return w


def _pad(s, width):
    s = str('' if s is None else s)
    return s + ' ' * max(0, width - _dw(s))


# ------------------------------------------------------------
# 三、CLI
# ------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description='3D-MG 自适应 HTML 汇报文档生成器（窄屏单列 / 宽屏两栏）')
    ap.add_argument('input', help='DSL 文件路径，"-" 表示标准输入')
    ap.add_argument('-o', '--output', help='输出 .html 路径（默认打印到 stdout）')
    ap.add_argument('--title', default='', help='报告标题（默认取 @HERO 主标题）')
    ap.add_argument('--footer', default='', help='页脚文字')
    ap.add_argument('--txt', action='store_true', help='额外输出一份 .txt 纯文本')
    ap.add_argument('--stats', action='store_true', help='打印结构统计')
    args = ap.parse_args(argv)

    if args.input == '-':
        raw = sys.stdin.read()
    else:
        with io.open(args.input, encoding='utf-8') as f:
            raw = f.read()

    blocks = parse_blocks(raw)
    if args.stats:
        s = stats(blocks)
        sys.stderr.write('模块 %d ｜ 表格 %d ｜ KPI %d ｜ 判断 %d ｜ 链路 %d ｜ 通栏 %d\n' % (
            s['cards'], s['tables'], s['kpis'], s['notes'], s['chains'],
            sum(1 for b in blocks if b['wide'])))

    title = args.title
    if not title:
        for b in blocks:
            if b['type'] == 'hero':
                title = b['label'] or b['title']
                break

    html = build_html(blocks, title=title, footer=args.footer)

    if args.output:
        with io.open(args.output, 'w', encoding='utf-8', newline='\n') as f:
            f.write(html)
        sys.stderr.write('已生成 %s（%d 字节）\n' % (args.output, len(html.encode('utf-8'))))
        if args.txt:
            tp = os.path.splitext(args.output)[0] + '.txt'
            with io.open(tp, 'w', encoding='utf-8', newline='\n') as f:
                f.write(to_plain_text(blocks, title))
            sys.stderr.write('已生成 %s\n' % tp)
    else:
        sys.stdout.write(html)
    return 0


if __name__ == '__main__':
    sys.exit(main())
