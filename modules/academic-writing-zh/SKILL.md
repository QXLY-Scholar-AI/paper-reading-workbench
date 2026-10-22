---
name: academic-writing-zh
description: Use when the user asks for Chinese academic research planning or writing, including topic selection, literature review, data interpretation, thesis or manuscript drafting, revision, translation, peer-review responses, or journal preparation.
---

# 中文学术写作

把用户的自然语言请求路由到当前最相关的学术工作，不要求用户记 Skill 名称，也不要一次展开所有模块。保持作者提供的事实、数据、观点和结构；不确定之处标出证据位置与待确认项，不用猜测补齐。

## 路由

- 选题、研究问题、可行性、开题、理论框架或假设：读取 [references/research-design.md](references/research-design.md)。
- 文献综述、理论与概念梳理、方法/数据分析、统计结果核对或参考文献：读取 [references/evidence-and-analysis.md](references/evidence-and-analysis.md)。
- 论文结构、章节、摘要、关键词、结论或分步起草：读取 [references/manuscript-writing.md](references/manuscript-writing.md)。
- 改写润色、删冗、翻译、学术表达、审稿回复或期刊格式：读取 [references/revision-and-submission.md](references/revision-and-submission.md)。

若请求只要求评估、摘要或指出问题，就只交付该项，不自动改写全文。一个请求跨多个模块时，先确定主要交付物，只加载完成它所必需的相邻模块；有会改变结果的歧义时再简短询问，否则按明确请求推进。

## 共同工作边界

1. 先分清用户要的是评估、规划、写作、改稿还是核验。按其明确的范围、对象、语言、长度、格式和输出位置交付；处理文件时优先使用相应文档技能。
2. 事实、数据、引文和结论必须能回到用户材料或已核验来源。禁止编造论文、作者、DOI、样本、统计量、研究发现和引文页码。找不到依据时标为“未提供/待核实”，不要把占位符伪装成事实。
3. 编辑时保留未被要求改动的内容、编号、引文关系、图表和论证。不得悄悄替作者选定冲突数据、补写研究过程、提高结论强度或改变因果含义；发现实质性矛盾时先指出，再将可安全编辑部分与待作者确认部分分开。
4. 统计与推论都要核对口径：样本量、分母、缺失值、单位、四舍五入、组别和时间范围；相关性不能直接写成因果，便利样本不能无条件推广。展示计算或判断依据，使作者能复查。
5. 一次完成用户要的工作，不为了“完整”追加无关章节。材料不足但仍可做局部工作的，先交付有依据的部分，并列出最少的待补项。
6. “去 AI 味/降低 AI 痕迹”只按语言质量处理：让表达具体、自然、清楚，减少空话、机械套句和无根据的重复；不承诺绕过检测器、不伪装作者身份，也不删除必要的限定和证据。
