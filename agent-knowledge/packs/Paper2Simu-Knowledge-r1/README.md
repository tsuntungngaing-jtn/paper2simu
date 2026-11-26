# Paper2Simu 知识包 r1

基于本机四机归档的 14 份 PDF，面向 Paper2Simu v0.5.2。用 textbook2skill 0.3.0（`1af584c`）处理了 117 页的原生文本与页面渲染。14 份都保留了独立证据位置与 SHA-256。P048 原文、四案记录及厂商手册另作交叉证据，未计入这 14 份。 [Paper2Simu v0.5.2 接入](https://github.com/tsuntungngaing-jtn/paper2simu/blob/ce42e0b/docs/paper-knowledge-and-solidworks.md) · [textbook2skill](https://github.com/tsuntungngaing-jtn/textbook2skill/tree/1af584c24d6639af65f8eab0b7c0236286507779)

| 包 | 面向角色 | 主要内容 |
| --- | --- | --- |
| [仿真与验证](simulation-validation/integration.md) | A01/A02/A03/A04/A05/A06/A07 | 原生有效读回、COMSOL 选区、Fluent 温变物性、轴对称积分、网格不确定度、换热与摩擦量 |
| [试验设计与条件校准](experiment-design/integration.md) | A03/A06/A09 | 做试验前冻结响应与变量、Morris、Sobol/Jansen、代理误差、模型偏差、可辨识与留出 |
| [多目标优化](multiobjective-optimization/integration.md) | A07/A09 | 同泵功比较、响应面编码和约束、PEC 公式口径。Pareto 候选流程保留为待核卡 |

## 接入 Paper2Simu

将这个目录作为任务可访问的本地知识包，或在仓库评审后置于 `agent-knowledge/packs/Paper2Simu-Knowledge-r1`。在任务卡登记包路径和 `manifest.json` 的版本或哈希。按 [role-index.json](role-index.json) 选择角色对应卡片，使用卡中的来源、版次和 locators 回看原文及实际模型。对仓库嵌入，可将角色已有文档或工作阶段指向索引。其原有 v0.5.2 角色登记、MCP 及验收准入逻辑由维护者管理。

先读每包的 `integration.md`，再按 ID 读取具体 JSONL 卡。 `verified` 表示首轮原文和适用范围已人工核对。 `candidate` 待追补证据或独立核验。 `blocked` 保留已知冲突并禁止自动算分。图索引可用 textbook2skill 的 `knowledge_cli.py validate` 和 `search` 检查或检索。把历史诊断与基于原文的任务签署保留在各自记录里。

| 核验记录 | 内容 |
| --- | --- |
| [四案对照](validation/case-crosswalk.md) | P014、P031、P010、P048 与规则卡的对照，含已查和未闭合项 |
| [复算记录](validation/checks.json) | 4 条历史证据检查与 6 组算术或逻辑检查 |
| [结构校验](validation/pack-checks.json) | 3 个知识包、3 个索引图的本轮校验结果和卡片计数 |
| [手册版本与缺口](validation/manual-coverage.md) | 版本、有效正文和本次未取得的来源 |
| [种子材料](validation/seed-manifest.json) | 14 份 PDF 的身份、版次、物理页范围与下载定位 |

本轮案例用于发现和核对规则。实机重跑、第二独立审查、留出对照、代理与 Pareto 优化试验均未进行。当前资料可支撑带泵功约束的响应面工作流，NSGA-II 和 qNEHVI 尚无本包原始方法卡。单篇时长、提交次数及停止授权从当前任务卡读取。原 PDF、厂商安装件及私有解析材料放在本机原位置或工作目录，ZIP 只含原创卡、索引、定位与核对记录。
