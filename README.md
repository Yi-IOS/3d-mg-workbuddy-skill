# 三维镜像治理法（3D-MG）· WorkBuddy 技能

> 原创企业经营诊断方法论，三层镜像：**现状镜像 / 因果镜像 / 推演镜像**。
> 把经营结果反向拆解为可追溯、可计算、可滚动修正的因果链路，
> 定位「毛利掉了多少、掉在哪、动了谁才能拿回来」。

---
---

👉 [在线自适应3D-MG报告](index.html)

## ✨ 能力


## ✨ 能力

1. **上市公司 / 非上市公司经营诊断实操**——输入公司名或代码，输出结构化诊断报告
2. **7 项因果传导建模**——原材料-成本-毛利、客户年降、质量损失、共享资源、外部冲击预警等，输出文字版因果网络图
3. **一页式理论框架**——三层镜像 + 三大底层理论 + 七项模型 + 闭环修正，单页可入汇报
4. **自适应横竖屏 HTML 汇报文档**——手机窄屏单列 / 电脑宽屏两栏，同一文件自动适配 + 手动切换视图 + localStorage 记忆
5. **企业本地数据导入分析（私有数据）**——把本企业财报 / 审计报告 / 经营分析 / 中期事业计划（MTP）等资料放入本地目录，按与上市公司**完全一致**的 3D-MG 方法产出诊断报告；**全程本地处理，脱敏后外发**

---

## 📦 仓库结构

```
3d-mg-workbuddy-skill/
├── README.md                 # 本文件（Github 仓库首页）
├── LICENSE                   # MIT
├── .gitignore
└── skills/
    └── 3d-mg/
        ├── SKILL.md          # ✅ 技能定义（YAML 头 + 全套提示词）
        ├── references/        # 方法论、7 项模型、报告格式、因果网络图文本版、参考案例
        │   ├── methodology.md
        │   ├── models.md
        │   ├── report_format.md
        │   ├── deliverable.md
        │   ├── rollout.md
        │   ├── causal-network.txt
        │   ├── case-jianghuai.md
        │   └── enterprise-ingest.md
        ├── templates/         # 自适应 HTML 模板、一页框架、Mermaid 模板
        │   ├── report-template.html
        │   ├── one-pager-framework.md
        │   ├── mermaid-template.md
        │   └── enterprise-data-manifest.md
        ├── scripts/           # 可选：DSL→HTML / Markdown→Word / 流程图→PNG
        │   ├── gen_report_html.py
        │   ├── gen_docx.py
        │   └── gen_flowchart.py
        ├── assets/            # 因果网络图等配图（PNG）
        └── examples/          # 双端对照示例
```

---

## 📥 WorkBuddy 导入方式

**从 Github 仓库导入（社区分发）：**

1. 打开 WorkBuddy 客户端
2. 添加技能 → **从 Github 仓库导入**
3. 填入本仓库地址：`https://github.com/<你的账号>/3d-mg-workbuddy-skill`
4. 导入后技能名即 `3d-mg`，可直接对话调用

> 仓库根目录下的 `skills/3d-mg/SKILL.md` 是技能入口；WorkBuddy 按标准技能规范
> 自动识别 `skills/` 下的子目录。

**本地安装（备选）：**

```bash
# 作为用户技能（跨项目可用）
cp -r skills/3d-mg ~/.workbuddy/skills/

# 或作为项目技能（随仓库共享给协作者）
cp -r skills/3d-mg <你的项目>/.workbuddy/skills/
```

---

## 🧪 测试指令

1. 使用 3D-MG 对**江淮汽车（600418）**做完整经营诊断
2. 输出 3D-MG **一页式理论框架总图**
3. 生成**自适应横竖屏 HTML 汇报文档**

> 第 1 条可换任意公司名或代码（如 `600418`、`比亚迪`、`大疆创新`）。
> 参考案例见 `skills/3d-mg/references/case-jianghuai.md`。

---

## 🔧 生成自适应 HTML 汇报文档（两种路径）

**路径 A（默认，仅需 Read + Write）：**
模型读取 `skills/3d-mg/templates/report-template.html`，把诊断报告整理成 `blocks` JSON，
替换其中的 `__REPORT_JSON__` 占位符，Write 为 `公司名_3D-MG.html` 即可直接打开/分享。

**路径 B（需 Bash 权限）：**
把报告写成 DSL，再跑脚本：

```bash
python3 skills/3d-mg/scripts/gen_report_html.py 报告.dsl -o 报告.html --title "示例公司（600418.SH）"
```

12 模块格式与 DSL 规范见 `skills/3d-mg/references/report_format.md`。

---

---

## 🏢 企业本地数据导入分析（私有数据）

把本企业资料放进本地目录，即可像分析上市公司一样产出诊断报告——**方法完全相同，只是数据来源换成你的内部文档**。

1. 在仓库内（或任意本地路径）建 `data/`，按类型分放：
   `01_财务报表/`、`02_审计报告/`、`03_经营分析/`、`04_中期事业计划/`
2. 复制 `skills/3d-mg/templates/enterprise-data-manifest.md` 为 `data/00_资料清单.md`，登记每份资料的
   类型 / 期间 / 路径 / 责任人 / 密级。
3. 对模型说：「按这份清单，对【企业名】做 3D-MG 企业内数导入分析，导出报告。」
   模型会走 `skills/3d-mg/SKILL.md` 的**模式六**：读资料 → 三层镜像 → 导出 12 模块报告 + 自适应 HTML。

**保密红线**：全程本地、不上传；报告默认本地，外发前须按清单密级脱敏。完整约定见
`skills/3d-mg/references/enterprise-ingest.md`。

---

## ⚠️ 免责声明

本技能输出内容仅用于**企业内部战略研讨与经营诊断**，**不构成任何投资建议**。
分析质量高度依赖输入资料完整度；资料不足时优先输出资料补全清单，禁止强行生成确定性结论。
决策前请以公司正式披露为准。

---

## 📄 许可

[MIT License](LICENSE) · Author: IOS
