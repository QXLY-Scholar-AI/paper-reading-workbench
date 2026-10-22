# reading.json

UTF-8 JSON，物理页码从1开始。五个steps的id分别为1到5。

```json
{
  "schema": "paper-reading-workbench/v1",
  "paper": {"title": "论文标题", "authors": "作者", "doi": "可为空"},
  "summary": "整篇论文的连贯概括",
  "steps": [{
    "id": 1, "title": "作者想解决什么问题",
    "paragraphs": [{"title": "具体问题", "text": "精读正文", "layer": "author", "refs": ["E01"]}]
  }],
  "annotations": [{
    "id": "E01", "step": 1, "page": 1,
    "title": "批注标题", "kind": "method", "quote": "从原文复制的实际短引句",
    "explanation": "中文解释", "layer": "author"
  }]
}
```

一个引句应尽量在同一页且能唯一定位。用原文中的词句而非中文翻译或生成的概括。`layer`仅取`author`或`analysis`，引用ID必须存在。

`kind`为`background`、`method`、`result`、`question`或`implication`，表示批注用途，与作者/AI来源标签独立。发现结果冲突也可标为question。旧记录未提供kind时按所属步骤补默认值。

五部分正文还应包含研究地图、可检验问题、作者声称的缺口、方法适配、直接证据结论与作者主张对照，以及有机制和区分检验的替代解释。先记录`evidence-conclusions.md`，说明是否已接触作者结论及实际材料范围，再写最终JSON。

网页展示的原页由PDF直接渲染，坐标由实际引句匹配产生。若唯一匹配失败，脚本保留未定位状态；禁止仅为通过定位而填写与解读无关的引句。

兼容旧 schema `jzks-pdf-viewer/v1`。其他 schema 将报错而不会静默通过。`page` 始终是原 PDF 物理页；期刊印刷页码必须根据原页单独核实，不用公式猜测。报告的 `page_map` 记录物理页、PDF 标签（若存在）及批注 PDF 页，不虚构印刷页码。未知顶层或段落字段会出现在 warnings；仅约定字段进入正文。

## layer的判断依据

layer反映观点来源而非整理者身份。author用于作者原有重要观点/方法/结果/结论的引用或归纳；analysis用于AI额外分析。含两种来源的段落必须拆分。完整五步新卡片须有两类实质内容，代码检查不能证明语义归属正确。上方JSON只展示字段结构，不是完整卡片。

paper里的标题、作者和DOI不得复制到annotations充当独立证据；单位、日期、学位等同样默认只作基本信息。第一页若有实质摘要或正文仍可标注，不按页码一概排除。
