# 条件可取校准操作卡（Conditional Calibration）

本文件是 Paper2Simu **skill 包内**标准附件，由 [`paper-reproduction-task.md`](paper-reproduction-task.md) 在论文复刻任务中引用。人不手抄全文；agent 在需要缩小论文指标相对误差、且存在有界 `tentative` 输入时遵循本卡。

目标：**条件可取复刻**——锁定论文给定输入，调整少量待定假设，使指定输出进入门槛，并报告条件可行假设区间。不是 1:1 找回作者真参。

## 1. 何时启用

同时满足：

1. 任务为论文复刻，且主要指标已有锁定参考与定义；
2. 基线已完成，定义/选区/单位审计已排除“假误差”；
3. 存在一个或多个带物理先验盒的 `tentative` 变量；
4. 任务卡已给出校准预算（最大联合求解次数、可调变量上限）。

不启用：纯执行任务；仅缺守恒/网格检查；误差来自错误 QoI 定义或错误选区。

## 2. 变量分层（唯一可调集）

| 层 | 标签 | 可否调 | 用途 |
|---|---|---|---|
| 锁定 | `paper_reported` / `derived` | 否 | 几何表、Tin、流量、热流、物性表、指标定义与截面 |
| 软件默认真源 | `software_documented` | 一般不调 | 官方推荐 BC/耦合/稳定化默认；只换文档推荐项并记账 |
| 待定假设 | `tentative`（可与 `inferred` 同记录，须标 tentative） | **唯一可调** | 论文未消歧且物理合理的入口剖面、界面集合解释等 |
| 数值诊断 | `numerical` | 不作贴合旋钮 | 网格、阶次、稳定化：只估数值不确定度 |
| 拟合产物 | `fitted` | 校准输出 | 写入可行区间；不得再标成 paper_reported |

禁止进入 `tentative`：诊断热源、任意接触热阻、改参考值、改平均方式、为过线删点。

## 3. 多指标目标

对每个指定主要指标 \(i\)（非近零）：

\[
e_i = \lvert S_i - D_i\rvert / \lvert D_i\rvert
\]

任务默认门槛 \(\tau=0.15\)（严格小于；任务卡可覆盖）。综合目标：

\[
J(\theta)=\max_i(e_i/\tau)
\]

可取条件：\(J(\theta)<1\) 且每一项 \(e_i<\tau\)（近零指标用任务卡绝对容差）。  
先压最差项，禁止用压降小误差掩盖温差大误差。  
本 \(J\) 是本项目建议目标，不是 ASME/厂商通用公式。

## 4. 推荐调参阶梯（按预算）

### 4.1 小预算（默认，联合求解约 ≤6）

1. 锁定基线 \(\theta_0\)，记录 \(e_i\) 与 \(J\)。
2. 每个高优先级 `tentative` 只做**先验盒端点**（OAT），流量/归一化保持论文锁定值。
3. 仅当某因子使超限指标**单调改善**且其他指标不系统性恶化时，再试中点或该因子上的短线搜索。
4. 单指标“夹住目标”不代表多指标有共同可行区；无单调性或无有效括区则停止该因子，换下一有据变量。
5. 不得无限二分；用尽预算则交付最佳已知点与失败原因。

### 4.2 中预算（`tentative` ≥3 或交互可疑）

用 **Morris / elementary effects**（或等价径向 OAT 筛选）在先验盒内筛主效应，再对少数主因子做有界 1D/2D 扫描。  
依据：Campolongo, Cariboni & Saltelli, *Environ. Model. Softw.* 22:1509–1518 (2007)；Saltelli 等筛选与定量敏感性衔接方法。  
筛选只排序影响，不自动给出统计可信区间。

### 4.3 有 Optimization Module 时（可选）

COMSOL **Parameter Estimation / Optimization**：

- 必须设每个控制变量的 **Lower/Upper bound** 与 **Scale**；
- 几何/剖面/非方程内参数优先 **BOBYQA**；方程内参数可试 Levenberg–Marquardt；
- 目标优先表达相对误差（或加权 \(e_i\)），勿默认无归一绝对温标最小二乘掩盖温升问题；
- 官方说明逆问题常不可辨识、依赖初值——交付**条件可行集**，不宣称唯一真值。

文档入口：

- https://doc.comsol.com/6.4/doc/com.comsol.help.opt/opt_ug_solver.8.03.html
- https://www.comsol.com/blogs/how-to-use-the-parameter-estimation-study-step-for-inverse-modeling

Fluent 侧用任务授权的参数研究/优化工具，同样要求先验盒、试验矩阵与 \(J\)；不得用未记录的 GUI 手拧。

### 4.4 默认不上

Kennedy & O’Hagan 贝叶斯校准（含 discrepancy）：仅在任务明确要求后验/模型偏差分离时启用。  
“接近论文表值”的常规条件复刻用 4.1–4.3 即可。

## 5. 必须记录的三张表

### INPUT_LEDGER（节选列）

`id | name | value | unit | origin | layer | prior_box | affects_QoI | notes`

### TRIAL_MATRIX

`trial_id | run_id | θ 变化 | e_i 向量 | J | decision(continue/stop/switch_factor) | artifact`

### FEASIBLE_SET

`θ 描述（区间或离散包络） | 达标工况 | J_best | holdout 结果 | identifiability | claim_scope`

条件可行区间名称可用 **条件校准可行区间**；禁止写成统计可信区间或“作者真实设置”。

## 6. 验证与停止

- 在校准工况上拟合的 \(\theta\) **不得**再当该工况的独立验证；至少用另一流量、另一结构或任务指定留出数据检查迁移。
- 多组 \(\theta\) 均使 \(J<1\)：报告不可辨识与可行集，不压成单点“真值”。
- 停止：预算用尽；改动小于数值/提取不确定；主指标相互冲突无共同改善；先验盒内无端点改善且无依据扩盒。
- 不笼统等待“更多作者资料”；缺的是可导出分项或先验盒时，只阻塞依赖项并列最小证据请求。

## 7. 与 V&V 框架的对齐（诊断用）

ASME V&V 20 / NIST IR 8298：将 `tentative` 视为 **input uncertainty**，网格等为 **numerical uncertainty**，残余系统偏差为 **model form**；分账报告。  
项目验收仍可用相对误差门槛，但不得用假物理源项吸收 model form 来强行过线。

## 8. 交付句式（强制）

条件复刻通过时写：

> 在锁定论文输入 \(\ldots\)、软件文档默认 \(\ldots\)、以及条件假设 \(\theta\in\Theta_{\mathrm{feasible}}\) 下，指定指标相对误差均 \(<\tau\)。\(\Theta_{\mathrm{feasible}}\) 为条件校准可行区间，不是作者设置的唯一还原。

失败时写最佳 \(J\)、超限指标、已排除因子与下一步有据假设。
