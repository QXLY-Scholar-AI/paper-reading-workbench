# Paper Reading Workbench · 论文精读工作台

把一篇论文读成可回查的五步精读，并生成带原文高亮、中文批注和个人笔记的离线阅读网页。

**Skill 名称：`paper-reading-workbench` · 曾用名：`jzks-pdf-viewer`**

适合需要认真读一篇论文、核对结论依据、保留阅读笔记的研究者。AI 负责阅读与解读，脚本负责证据定位、网页和批注 PDF；生成后的网页无需模型密钥，也不依赖 CDN。

## 能做什么

| 阅读环节 | 得到的内容 |
| --- | --- |
| 问题 → 方法 → 结果 → 证据与结论 → 局限与启发 | 五部分连贯精读，可按节或整篇复制 |
| 点击正文中的证据编号 | 跳到原 PDF 物理页，并显示对应高亮和中文解释 |
| 专注阅读、筛选与缩放 | 保留原页版式，按方法、结果、疑问或个人笔记筛选 |
| 框选和个人纠正 | 保存手工勾画，在 AI 批注旁补充自己的理解 |
| 导出 | Markdown、结构化记录、批注 PDF、个人笔记 JSON |

浏览器会尝试保存阅读位置和个人笔记；换浏览器、清理浏览器数据或迁移文件前，请先导出 JSON。

## 安装

下载仓库 ZIP 并解压，将包含 `SKILL.md` 的目录命名为 `paper-reading-workbench`。可以把目录或 GitHub 地址交给 Codex：

> 请安装这个仓库中的 paper-reading-workbench，保留脚本和资源文件，并检查是否能调用。

手动安装（在该仓库根目录运行 Windows PowerShell）：

```powershell
$skillHome = Join-Path $env:USERPROFILE '.agents\skills'
$skillTarget = Join-Path $skillHome 'paper-reading-workbench'
New-Item -ItemType Directory -Force $skillHome | Out-Null
if (Test-Path -LiteralPath $skillTarget) { throw '已安装同名 Skill，请先备份再更新。' }
Copy-Item -LiteralPath (Get-Location).Path -Destination $skillTarget -Recurse
```

安装后确认 `paper-reading-workbench/SKILL.md` 位于 Skill 目录的第一层，再重新打开对话。不要只复制 SKILL.md。其他宿主请使用它实际扫描的 Skill 目录。

macOS / Linux（同样在仓库根目录运行）：

```sh
mkdir -p ~/.agents/skills
test ! -e ~/.agents/skills/paper-reading-workbench && cp -R . ~/.agents/skills/paper-reading-workbench
```

## 快速开始

给 Codex 一篇 PDF，说：

> 用 paper-reading-workbench 精读这篇论文，围绕研究问题、方法、结果、证据与结论、局限与启发整理正文，并生成可以对照原文的批注阅读器。

AI 应先读取全文及关键图表，按 [精读规则](references/deep-reading.md) 整理证据，再创建 [reading.json](references/card-schema.md)。已有结构化记录时可直接重建网页。

```sh
python -m pip install -r requirements.txt
python scripts/build_viewer.py --pdf paper.pdf --card reading.json --out output
```

打开 `output/index.html` 即可阅读。生成需要 Python 3.10+、PyMuPDF；查看结果需要现代浏览器。首次安装依赖需要网络，生成器本身不上传论文、不调用模型。

## 输出文件

| 文件 | 用途 |
| --- | --- |
| `index.html` | 自包含阅读器，内嵌原页、精读、原 PDF 和导出代码 |
| `paper-card.md` / `reading.json` | 精读正文 / 结构化记录 |
| `annotated-paper.pdf` | 原始页面加高亮和中文边栏，包含构建时的 AI 批注 |
| `evidence-index.json` / `annotation-map.json` | 判断与出处、证据坐标 |
| `build-report.json` | 成功、歧义、未定位、页码映射和字段警告 |

网页里的“下载批注PDF”会另外合并当前个人勾画和纠正；这些后续笔记不会自动回写最初生成的 PDF。分享 HTML 相当于分享其中内嵌的论文与精读内容。

## 定位规则与旧记录兼容

- 页码统一使用原 PDF 的物理页码。批注 PDF 可能有续页，报告会保存映射；不会根据公式猜测期刊印刷页码。
- 同一页唯一匹配才生成高亮。重复、过短或未找到的引句会保留“待定位”提示和真实状态。
- 对部分旧字体的 `fi/ff/fl` 编码问题，先标准匹配，检测到重复旧编码特征后才尝试连字回退，并记录使用方法。可用 `--legacy-ligatures off` 关闭，或 `on` 明确启用。
- 接受新 schema `paper-reading-workbench/v1` 和旧 schema `jzks-pdf-viewer/v1`。旧个人笔记的存储键和 JSON 格式继续兼容。
- 文字型 PDF 可定位；扫描 PDF 需要先取得带坐标的 OCR。大论文生成的 HTML 会较大。

## 检查与排错

```sh
python -m unittest discover -s tests -v
```

生成后先看 build-report.json，再打开网页检查链接、页码和笔记导出。找不到 PyMuPDF 时，在实际运行脚本的 Python 环境安装 requirements.txt。仅有页面跳转没有高亮时，查看具体状态，核对页码与完整原文引句；不要删掉关键语义只为通过匹配。

## 目录与第三方组件

`scripts/` 是构建器，`assets/viewer.html` 是固定模板，`assets/export-pdf.js` 是合并导出逻辑，`references/` 是精读及数据规范，`tests/` 使用合成材料。

PDF 导出内置 [pdf-lib](https://github.com/Hopding/pdf-lib)，许可见 [pdf-lib-LICENSE.md](assets/vendor/pdf-lib-LICENSE.md)。PyMuPDF 为独立依赖，其许可按[官方项目](https://github.com/pymupdf/PyMuPDF)执行。
