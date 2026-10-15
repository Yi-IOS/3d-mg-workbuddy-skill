# 交付物规范

> 用户要出正式文档（手册、报告、PPT）时读本文。

## 一、成品参考（作为质量标准对照）

下面这套成品是 3D-MG 的落地样例，**用来对照"什么算合格"**，不是必须复现的文件。
按本规范生成的同类文档，规模与结构应对齐：


| 文件 | 规模 | 用途 |
|---|---|---|
| `3D-MG 管理层决策简版（5-10分钟速读）.docx` / `.pdf` | 15 页 / 18 表 | **给管理层看的决策提案**。封面即全部结论，只需三个决定 |
| `三维镜像治理法（3D-MG）管理者实操指引手册（正式落地版）-排版修订版.docx` / `.pdf` | 94 页 / 144 表 / 21 图 | **部门执行主文件**。表格列宽自适应 + 全左对齐 + 9pt |
| `源稿-分章节/`（11 个 md + 全文源稿） | 10.6 万字符 | 单独修改某章时只改对应文件 |
| `00_资料说明.md` | — | 本目录导航与分工说明 |

Word 编辑版若内容被包进浮动文本框（顺序错乱 + ASCII 图断行），**不要使用**。

**生成纪律：内容改 md 源稿再重新生成，不要直接改 docx**（改 docx 会导致全文样式不统一）。

---

## 二、首次搭建的19 项交付物

| 序 | 交付物 | 责任 | 验收标准 |
|---|---|---|---|
| 1 | 推行授权书 | 总经办 | 含签字、范围、时限 |
| 2 | 推行启动会纪要（含六条承诺） | 推行工作组 | 含承诺宣读记录 |
| 3 | 数据口径确认单 16 份 | 财务 + 业务 | 签字率 100% |
| 4 | 现状镜像基期表 | 经营分析部 | 三段归因误差 < 0.05pp |
| 5 | 数据来源索引表 | 经营分析部 | 可追溯到原始台账行 |
| 6 | 毛利率变动归因表 | 经营分析部 | 合计误差 < 0.05pp |
| 7 | 异常项清单 | 经营分析部 | 归因量化，无「其他」类 |
| 8 | 现状镜像 V1.0（封版） | 三方会签 | 版本号 + 生效期 |
| 9 | 因果图（含符号标注） | 战略 MTP 部 | 节点 ≤25，边 ≤40 |
| 10 | 结构化访谈记录与编码表 | 战略 MTP 部 | ≥6 人，含离职/退休专家 |
| 11 | 三角验证报告 | 战略 MTP 部 | 采纳/剔除/待验证三分 |
| 12 | 弹性系数与时滞估计表 | 战略 MTP + 财务 | 含回归输出、R²、显著性 |
| 13 | 置信度标注表 | 战略 MTP 部 | 全部关系有分级 |
| 14 | 阈值规则表 | 推行工作组 | ≥3 条，含责任人与授权 |
| 15 | 敏感性分析表 + 龙卷风图 | 战略 MTP 部 | 前 8 变量，含 EBIT 绝对值 |
| 16 | 四情景对比表 | 战略 MTP 部 | 含治理干预情景 |
| 17 | MTP 可实现条件反推表 | 战略 MTP 部 | 每目标对应条件清单 |
| 18 | 模型说明书 + 月度更新 SOP | 经营分析部 | 他人可照做 |
| 19 | 90 天总结报告 | 推行工作组 | 含量化战绩 |

## 三、七道门（交付前逐项自检）

| 门 | 门槛 | 不通过处理 |
|---|---|---|
| G1 | 总办书面授权 | 不得启动 |
| G2 | 口径签字率 100% | 不得建模 |
| G3 | 三段归因合计误差 < 0.05pp | 不得定稿 |
| G4 | 因果图节点 ≤25、边 ≤40 | 拆分或降级 |
| G5 | 全部关系有置信度标注 | 不得进模型 |
| G6 | 模型预测偏差 ≤ 15% | 修正系数后再验证 |
| G7 | 90 天内产生 1 次可量化决策 | 停止扩张，重做 |

---

## 四、排版规范（出正式文档时照此执行）

### 4.1 表格

| 项 | 设定 | 原因 |
|---|---|---|
| **列宽** | 按内容长度**平方根加权**：`col_w = TBL_W × (content_len^0.62) / Σ` | 线性加权会让长文本列吃掉整行；等宽列会把短列压成每行 2—3 字 |
| 最小列宽 | 700—760 twips | 防止「现状镜像」这类词被压成两行 |
| 表格总宽 | `TBL_W` = A4 宽 − 左右边距（本机 9070 twips） | 铺满版心 |
| 字号 | 9pt（18 half-points） | 比正文小一号，视觉层次分明 |
| **对齐** | **全部单元格 `jc=left`（含表头）** | 用户明确要求 |
| 表头 | 底色 `E8EDF4` 或 `DEE7F2` + `<w:tblHeader/>` | 跨页自动重复表头 |
| 垂直对齐 | `vAlign=center` | |
| 边框 | 全框线 + 淡蓝灰细线（`8FA0B8` / `9AAFC8`），`sz=4` | |
| 单元格边距 | 上下 28—46，左右 68—90 twips | |
| 段落缩进 | `firstLine=0, left=0` | **必须显式覆盖继承的首行缩进** |

### 4.2 图形（流程图）

**ASCII 制表图不能直接放进 Word/PPT** —— 换行符（`w:br`）会丢失，整块被压成一个段落，Word 只能折行错位。

**正确做法：用 `scripts/gen_flowchart.py` 渲染成 PNG 再插入。**

```bash
python scripts/gen_flowchart.py --list# 列出全部 20 张
python scripts/gen_flowchart.py               # 渲染全部到 scripts/figs_out/
python scripts/gen_flowchart.py --index 10    # 只渲染第 10 张
python scripts/gen_flowchart.py --scale 2     # 放大 2 倍（插入 PPT 用）
```

**插入参数**：
- 宽度：版心宽度 × 0.92
- 高度上限：12800 twips（超出则按高度等比缩放）
- 段落居中，上下加细边框 + 极浅底色`FCFDFE`
- `keepNext`（仅当图高 ≤ 11000 twips 时加，防止图与标题分离）

### 4.3 标题层级

| 层级 | 字号 | 字体 | 间距 | 其他 |
|---|---|---|---|---|
| 一级（章） | 18—20pt | SimHei | before 360/ after 300 | 下加粗横线（`sz=18`, `1F3864`）；一级标题加 `keepNext` |
| 二级（节） | 15pt | SimHei | before 300 / after 140 | 颜色 `1F3864`；**不加 keepNext**（会导致空白页） |
| 三级 | 12.5pt | SimHei | before 200 / after 140 | 颜色 `2F5496` |
| 正文 | 11.5—12pt | SimSun | 行距 1.5（350 twips） | 首行缩进 440—480 twips，两端对齐 |

⚠️ **`keepNext` 不能滥用**：给二级标题和图片段落加会导致多个空白页。只给一级标题加。

### 4.4 中文标点

**必须用中文弯引号「」和 —— ，不要用 ASCII 直引号 `"`。** U+0022 在宋体里渲染成斜杠状直引号，中文文稿里很难看。

### 4.5 页面

| 项 | 规范设定 |
|---|---|
| 纸张 | A4（11906 × 16838 twips） |
| 页边距 | 上下 1276—1418，左右 1276—1418 |
| 版心宽 | 9354（边距 1276）/ 9070（边距 1418）twips |

---

## 五、生成 Word 的技术路线

### 5.1 用 editor_sdk（推荐，适合插入长文）

```bash
cd "<tencent-local-office-edit skill 目录>"
FID=$(python3 edsdk.py call create_doc | grep -o 'new_doc_[A-Za-z0-9_]*')

# 1) 先配样式（顺序很重要：必须在插入内容之前）
python3 edsdk.py call doc_update_named_style --json "{\"file_id\":\"$FID\",\"named_style_type\":\"NORMAL_TEXT\",\"paragraph_style\":{\"line_spacing\":1.5,\"line_spacing_rule\":1,\"first_line_indent\":24},\"text_style\":{\"font_family\":\"SimSun\",\"font_size\":12}}"
python3 edsdk.py call doc_update_named_style --json "{\"file_id\":\"$FID\",\"named_style_type\":\"HEADING_1\",\"paragraph_style\":{\"jc\":\"center\",\"first_line_indent\":0},\"text_style\":{\"font_family\":\"SimHei\",\"font_size\":18}}"

# 2) 插入全文（分章节插，单次不超过 7 万字符）
python3 edsdk.py call doc_insert_markdown --json "{\"file_id\":\"$FID\",\"idx\":0,\"markdown\":\"file://E:/路径/成稿.md\"}"

# 3) 保存
python3 edsdk.py call save_file --json "{\"file_id\":\"$FID\",\"file_path\":\"E:/路径/成稿.docx\"}"
```

**三个硬坑（务必避开）**：

1. **单次插入上限约 10 万字符**，超了报 `HTML segment insertion failed`。必须分章节插入。
2. **续接坐标必须用返回值里的 `last_edit_index`，不能用 `position`**。用 `position` 直接失败。
3. **绝不能固定 `idx=0`** —— 那样每次都插到最前面，章节顺序会完全错乱。
   正确写法：`idx = re.search(r'"last_edit_index":(\d+)', out).group(1)` 循环传递。

**已知限制**：`doc_update_named_style` 的 `jc: both` 会落到右对齐。两端对齐需事后改`styles.xml`。

### 5.2 直接构造 XML（适合精确控制排版）

需要精确控制列宽、图形插入、五道验收门自检时，用字符串拼 XML + `ElementTree` 解析（本技能 `scripts/gen_docx.py` 即此写法的完整实现）。

**嵌图的三个硬坑**：

1. **前缀会被改名**：`ET.SubElement(el, "{ns}tag")` 写进去后 `wp`/`a`/`pic` 被重写成 `ns3`/`ns4`/`ns5` → **Word 认不出，图片全丢**。含图片的 XML 必须字符串拼接 + `ET.fromstring` 解析。
2. **占位符替换失效**：`<w:t>@@PIC0@@</w:t>` 会被 run 拆分规则打散，`str.replace` 匹配不到。改用唯一英文标记 + 正则定位**整段**。
3. **根元素 `xmlns` 会被丢**：ET 只保留用过的声明，输出前检查 `<w:document>` 缺什么补什么。

---

## 六、校验（三层，缺一不可）

### 6.1 内容层

```python
import zipfile
import xml.etree.ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
z = zipfile.ZipFile('目标.docx')
root = ET.fromstring(z.read('word/document.xml'))
full = ''.join((t.text or '') for t in root.iter(W+'t'))
print('正文字符:', len(full))
print('段落:', len(list(root.iter(W+'p'))), '表格:', len(list(root.iter(W+'tbl'))))
```

⚠️ **不要用正则取 `<w:t>`** —— `re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)` 会跨段落串行，把 XML 属性引号当正文引号（虚报几百个ASCII 引号）。

### 6.2 结构层（图形是否真嵌入的唯一可靠判据）

```python
import win32com.client as win32, os
app = win32.Dispatch('Word.Application'); app.Visible = False
doc = app.Documents.Open(os.path.abspath('目标.docx'), ReadOnly=True, AddToRecentFiles=False)
print('页数:', doc.ComputeStatistics(2), '表格:', doc.Tables.Count, '图片:', doc.InlineShapes.Count)
doc.ExportAsFixedFormat('预览.pdf', 17)
doc.Close(False); app.Quit()
```

⚠️ 校验/渲染 docx **必须用 venv python**（`~/.workbuddy/binaries/python/envs/default`，装了 pymupdf），managed python 没装。

### 6.3 渲染层

```python
import pymupdf
d = pymupdf.open('预览.pdf')
d[4].get_pixmap(dpi=110, alpha=False).save('检查页.png')
```

**逐页检查留白**（章末页留白正常，段中留白说明keepNext 用过头了）：

```python
for p in range(d.page_count):
    blocks = d[p].get_text('blocks')
    ymax = max((b[3] for b in blocks), default=0)
    if ymax < d[p].rect.height * 0.45:
        print(f'  p{p+1} 留白多')
```

---

## 七、常见排版问题速查

| 现象 | 根因 | 修法 |
|---|---|---|
| 表格内容被压成每行 2—3 字 | 等宽列 | 按内容长度平方根加权重新分配 |
| 首行缩进在表格里没去掉 | 继承了正文样式 | 单元格段落显式设 `ind firstLine=0 left=0` |
| 流程图框线断裂、文字乱| `w:br` 丢失，ASCII 图被压成一段 | 渲染成 PNG 插入 |
| 有序编号跳号（1.→8.→9.） | 多组列表共用同一 numId | 不用 Word 编号，自己渲染「1. 」+ 悬挂缩进 |
| 章节顺序错乱（第二章跑到第一页） | 插入时固定 `idx=0` | 用返回的 `last_edit_index` 续接 |
| 内容被包在文本框里导致顺序错乱 | Word 编辑时把内容拖进了浮动文本框 | **从源稿重建 docx**，别修补 |
| 图片全部丢失（`InlineShapes=0`） | ET 改了 `wp`/`a`/`pic` 前缀 | 含图片的 XML 用字符串拼接 |
| 多个空白页 | `keepNext` 用过头 | 只给一级标题加 |
| 表格整块被推到下一页 | 表格太长放不下 | 简化表格/拆表，不要加 `cantSplit`（那是禁止跨页） |
| ASCII 直引号渲染成斜杠状 | 用了 U+0022 | 换中文弯引号「」 |
