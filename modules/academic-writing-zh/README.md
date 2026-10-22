# Academic Writing ZH · 中文学术写作

根据研究者当前的任务，协助选题、梳理文献、分析材料、起草论文、修改翻译和准备审稿回复。

它把常见的中文学术工作整理成四个模块，按需读取；一次只处理用户要求的范围，修改时保留事实、数据、结构和引用关系。

## 功能

| 模块 | 适用任务 |
| --- | --- |
| [研究设计](references/research-design.md) | 选题、研究问题、开题、理论框架和可检验假设 |
| [文献与证据](references/evidence-and-analysis.md) | 文献综述、概念梳理、数据口径、方法和参考文献核对 |
| [论文起草](references/manuscript-writing.md) | 提纲、章节、摘要、关键词和结论 |
| [修改与投稿](references/revision-and-submission.md) | 润色、压缩、翻译、逐条审稿回复和投稿格式 |

## 安装

下载仓库 ZIP 并解压，将包含 `SKILL.md` 的目录命名为 `academic-writing-zh`。可以把目录或 GitHub 地址交给 Codex：

> 请安装这个仓库中的 academic-writing-zh，保留脚本和资源文件，并检查是否能调用。

手动安装（在该仓库根目录运行 Windows PowerShell）：

```powershell
$skillHome = Join-Path $env:USERPROFILE '.agents\skills'
$skillTarget = Join-Path $skillHome 'academic-writing-zh'
New-Item -ItemType Directory -Force $skillHome | Out-Null
if (Test-Path -LiteralPath $skillTarget) { throw '已安装同名 Skill，请先备份再更新。' }
Copy-Item -LiteralPath (Get-Location).Path -Destination $skillTarget -Recurse
```

安装后确认 `academic-writing-zh/SKILL.md` 位于 Skill 目录的第一层，再重新打开对话。不要只复制 SKILL.md。其他宿主请使用它实际扫描的 Skill 目录。

macOS / Linux（同样在仓库根目录运行）：

```sh
mkdir -p ~/.agents/skills
test ! -e ~/.agents/skills/academic-writing-zh && cp -R . ~/.agents/skills/academic-writing-zh
```

## 调用示例

> 用 academic-writing-zh 润色下面这两段。保留数据、引用和小标题，让衔接更自然，直接给修改稿。

> 根据我提供的五篇论文，围绕供应链库存波动梳理共识、差异和待研究问题，每项判断注明来源。

> 评估这个研究问题是否足够具体，只给评价和需要补充的材料，先不要代写开题报告。

> 逐条整理这些审稿意见的回复。已完成的修改写清楚，尚未做的实验单独列出，不补造结果或行号。

## 提供什么材料

修改已有文本时，给出原文、需要修改的范围和期望格式即可。涉及研究判断时，尽量提供研究问题、文献、数据或原始结果。材料不足时先处理可完成的部分，缺失项明确标记。

研究尚未完成的摘要会写成研究计划；相关关系不会被改写成因果结论；引用信息不完整时保留待核实字段。润色目标是自然、准确、易读的语言，不承诺检测分数。

## 环境与交付

核心流程只有 Markdown 指令和参考规则，不需要 Python、额外模型密钥或独立网页。由已安装 Skill 的宿主 AI 执行；文献检索、统计计算、DOCX 或 PDF 文件制作需要宿主提供相应工具。

可以交付修改稿、提纲、评价或逐条回复，也可按用户要求处理文档。生成具体文件时保留用户未要求修改的章节和格式，并使用宿主的文档能力检查文件。

## 目录与检查

```text
academic-writing-zh/
├── SKILL.md
├── README.md
└── references/
    ├── research-design.md
    ├── evidence-and-analysis.md
    ├── manuscript-writing.md
    └── revision-and-submission.md
```

本轮已针对润色保留数字、相关与因果、综述缺文献、未完成研究摘要等情景独立审读与推演。实际长文质量仍应以具体任务产物评估；这个仓库不包含虚构的“自动整篇论文测试通过”成绩。
