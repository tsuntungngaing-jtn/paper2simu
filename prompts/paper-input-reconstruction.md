# 文献输入重建与迭代记录

论文复刻时，与 [统一任务 prompt](paper-reproduction-task.md) 和 [条件校准操作卡](conditional-calibration.md) 一起读取。本卡补充提取、推理及记录方法，不增加求解器收敛门槛，也不改变任务卡验收阈值。

人读摘要优先维护任务卡中的 **REPRODUCTION_DASHBOARD**（来源 / 原始输入 / 逐轮更改 / 输出对标）。本节字段是对照板的详细落盘格式；不要只写 JSON 事件而不更新四表。

## 1. 先重建证据，再补输入

建立一次完整输入清单，后续只读取变化及相关证据，避免每轮重读全文：

- 几何、尺寸、对称/周期范围、真实装置与计算域的对应关系；
- 材料、温度/压力依赖、适用范围、各相物性；
- 方程、简化、耦合、初始条件、边界、源汇、参考压力；
- 工况、时间/频率、研究类型；网格、壁面处理、数值设置；
- 各输出的公式、选区、平均权重、时刻/窗口、基准和单位。

逐项标 `FOUND / DERIVED / AMBIGUOUS / MISSING / NOT_APPLICABLE`。没找到必须记查过的章节/补充材料；搜索未命中不等于文章未提供。先定位正文、表格、公式、图注和补充材料；影响建模的公式、尺寸、曲线点及 OCR 可疑项回看原页。保留 PDF 文件哈希、页码、图表编号、短证据片段或截图路径。正文与表图冲突时保留两者及适用工况，不能只选更接近目标的数值。

每个输入用以下记录扩展 INPUT_LEDGER；无须复制已存在的表：

`input_id | case_id | value/unit | extraction_status | source_id/location | origin | role | formula/dependency_ids | bounds_or_alternatives | bounds_basis | uncertainty | affects_QoI | effective_readback | revision`

- `origin` 是来源，`role` 是用途（lock/tentative/numerical），`fitted` 是估计状态。三者分别记录。已有工具只支持旧 layer 时，在附加字段保存这些信息，不能覆盖原来源。
- `derived` 不自动等于 `lock`：例如 U=Q/A，只有 Q、A 及几何解释均确定才锁定 U；否则传播其依赖关系及范围，调整根输入，不能独立任调 Q、A、U。
- 官方文档证明软件的含义、默认值和适用条件，不能证明作者使用了它。纯数值设置归 numerical；未明确的物理边界可作为有依据的 tentative 分支。
- 明确论文值保持锁定；怀疑笔误时建立证据冲突记录，先复核勘误、单位和定义。确需更正时另立模型/评分版本，保留旧结果，不暗中改参考。

输出建立 QOI_CONTRACT：`metric_id | case | formula | domain/boundary | weight | time_window | reference/unit | source | digitization_uncertainty | scorer_version`。校准前冻结。比如总体换热系数不能换成局部换热系数平均；底面极差不能换成全模型极差；温度与温升分别定义。更正提取错误后，同版本重新评价所有可比较保存解，不能只重算有利试点。

## 2. 缺失信息的推理顺序

在任务授权内依次尝试，并记录推理链：

1. 查原文相关章节、补充、勘误和作者公开模型。
2. 由已知量及物理约束推导，展示公式、单位和适用条件。守恒推导不得同时假定一个尚待验证的通量为零。
3. 查安装版本官方定义/材料数据和权威物性，记录状态范围；相似论文只作带适用条件的外部证据。
4. 为剩余缺口建立少量竞争假设，先做量纲、数量级、解析极限和已有结果检查，再决定是否值得求解。

每条 HYPOTHESIS_CARD：

`hypothesis_id | missing_input_ids | candidate/value_or_range | physical_mechanism | evidence | applicability | expected_signed_QoI_response | alternatives | falsification_observation | coupled_constraints | cheapest_discriminating_check`

范围有两类：物理/材料硬边界，和可因新证据调整的探索边界。边界最优不自动授权扩展硬边界；探索范围扩大须记录新依据及版本。入口类型等类别变量分别建分支，不把类别编码成连续区间。没有依据时记录未知，不伪造“±10%”概率或置信度。

优先解决会影响最差指标、预计可辨别且验证便宜的假设。影响未知先做敏感性筛查，不能直接宣称低影响。先取保存解/后处理/解析估算，再用求解预算。OAT 是筛查而非排除交互的证据；存在共同约束或交互机制时，在预算内设计联合点。端点无改善不能独自证明内部无可行点。

若多种物理解释都合理，执行已授权的条件分支并报告各自结果；无需等到信息完备。只有无法构成适定模型或缺口超出授权时，阻塞依赖项，列出最小所需信息，继续其他工况/准备。不要把 ASK_USER 或 BLOCK_FINAL_VALIDATION 解释成整个任务放弃。

## 3. 每轮落盘，再更新最佳记录

复用任务输出目录，每次尝试创建唯一 `trials/<trial_id>/`；提交前写计划，结束/失败/恢复后追加事件。建议 JSONL 或逐轮 JSON+日志，格式可随现有工具调整。更正追加 supersedes 事件，保留旧值，不改写失败历史。单一任务写入者记录，未知提交状态先核对作业，不重发。

每轮最低内容：

```json
{
  "trial_id": "T001", "event": "planned", "timestamp_utc": "<actual UTC>",
  "parent_trial_id": "T000", "parent_checkpoint": "<path/hash>",
  "paper_hash": "<hash>", "input_revision": "I1", "scorer_version": "Q1",
  "hypothesis_id": "H1", "change": {}, "expected_response": {},
  "solver_version": "<installed>", "session_id": "<actual>",
  "budget_before": {}, "job_id": null, "run_id": null,
  "effective_readback": null, "observed_outputs": null,
  "decision": "PENDING", "reason": null, "artifact_paths": []
}
```

完成事件补充实际设置、几何/网格/研究/解/数据集身份，原始输出、参考值、带符号误差、J、检查状态、预期与实际响应差异、日志/模型路径、实际预算消耗及 KEEP/REVERT/HOLD/FAILED 理由。计划事件不能当执行证据，缺失结果不能写零。

多阶段或定时任务沿用[研究计划与交接](../docs/research-plan-and-handoff.md)中的事件字段。每轮补记证据如何支持或削弱假设、下一步及其证据路径。从现有事件和作业观测刷新 `resume.md`，记录提交前的 operation ID，回执不明时保留待核对。

区分 `last_attempt`、`best_comparable_trial`、`accepted_checkpoint`；故障试点不会覆盖最佳可比较解。恢复任务时先读索引、未结束事件和实际作业状态，再读相关证据。指标/模型版本不同的 J 不直接排名；必要时重评保存解。

失败归因先分 API/连接、输入/选区、数值求解、物理模型、后处理、参数不可辨识。API 重载错误先查实际版本签名，不能用物理调参修复；模型改动未生效先修执行链，不能据此推断参数无敏感性。同一原因重复时记录新证据，否则不盲目重试。

## 4. 可行范围与独立验证

报告满足任务标准的联合参数点集及固定条件。单参数投影区间不代表其笛卡尔积都可行；不同模型分支或不连通区间不能合并成一个连续安全范围。有限通过点仍是有限通过点，插值或代理预测须标待实算确认。

任务误差门槛筛出的集合称“条件可行集/候选范围”。统计置信区间或贝叶斯可信区间需要明确观测误差、概率模型、先验（如使用）、方法及可辨识性，不能把任务的 15% 容差直接当噪声方差或后验覆盖率。

留出必须记录数据/工况的划分、冻结的参数及模型版本、实际留出 run、评分和证据。换 claim_id 不构成独立验证；校准同一工况上的另一个相关指标也不自动独立。留出被用于改参数后转为开发数据，原独立状态撤销；无剩余留出就诚实标未独立验证，不阻止交付条件结果。旧 helper 返回 VALIDATED 时也须检查这些证据，不能仅凭名称认证。

## 5. 从失败中改进，避免把个案写成普遍定律

每个暴露问题记录：`incident_id | symptom | evidence | root_cause_or_hypothesis | minimal_fix | applicable_context | counterexample | regression_case | verification_status`。

把 API 签名错误、单位转换、错误选区、旧解混用等确定性故障做成小回归检查；物理假设保留适用范围，不能因一次拟合成功升级为全局默认。修改 prompt/策略后先复查原失败案例及至少一个相关反例；未完成复查保持候选。需要量化性能时再使用项目的独立 RSI 评估，不声称改写说明文字已提高成功率或节省 token。

## 依据

- [COMSOL 6.4 参数估计](https://doc.comsol.com/6.4/doc/com.comsol.help.opt/opt_ug_solver.8.03.html)：参数尺度/界限、数据方差和求解预算。
- [Kennedy & O’Hagan, JRSS B (2001)](https://doi.org/10.1111/1467-9868.00294)：校准与模型偏差的统计区分。
- [Campolongo et al., Environmental Modelling & Software (2007)](https://doi.org/10.1016/j.envsoft.2006.10.004)：多因素敏感性筛查。

以上支持方法选择；本卡的目录、事件字段和决策流程是项目工程约定，不冒称厂商要求。
