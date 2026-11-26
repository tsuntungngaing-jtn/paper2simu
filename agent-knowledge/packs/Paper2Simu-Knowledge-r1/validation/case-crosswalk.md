# 四个历史案例的规则核对

此处的回放使用当时的看板快照、本机报告、原文和官方资料。卡片通过对照意味着其建议能解释或排除记录中的某项错误路径。每个案例仍保留原来的求解与复刻资格。

| 案例 | 核对到的事实 | 规则与结果 |
| --- | --- | --- |
| P014 | C018 的 52 点配置在接口层回显全表，实际原生日志记录超限。对应本机 Fluent 23.1 头文件显示 100 个数据槽、存储成对值，且求值接口用 float。C022/C023 明确了该案例的精度差异和轴对称积分每弧度/全周差别。C026 标明 R1 19 案完成但均未达到数值终止门槛。R2 报告中的恢复工况和 PEC 分支也必须按各自资格评价。 | `PS-V-R04` 拒绝把设置回显视为物性验证。 `PS-V-R06` 只在原生量确为每弧度时做全周转换。 `PS-V-R01` 保留“已归档、数值未过”。50 对是本机 23.1 所核实现的容量。无需把 30 点写成通用配置。 [看板 C018/C022/C023/C026](https://docs.google.com/spreadsheets/d/19MxNKHp3cPE0alsO-9nEU8pdJhT0kLyK_f0VgLgki3U/edit#gid=676076419&range=A25:L33) |
| P031 | 布尔分域失败与外部曲面检查通过同时存在。R13 未明确实体维度。R16E 把域 2 的压力点从空集重绑到点 5，域 3 保持点 6，原生回读有记录。R16E 当时仍为 SOLVING，热误差字段为 NOT_RUN。 | `PS-V-R05` 要求核实际维度、有效集合与所属域。在历史记录中仅能证实重绑。 [逐轮记录](https://docs.google.com/spreadsheets/d/19MxNKHp3cPE0alsO-9nEU8pdJhT0kLyK_f0VgLgki3U/edit#gid=82347122&range=A3:J34) · [COMSOL 6.3 选区](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_api_general.47.11.html) |
| P010 | Case 4 保存热阻 0.0568186086 K/W，按实际 360 W 还原温差约 20.455 K，绝对差约 30.96%。只用同一温差除以推断的 480 W，绝对差约 1.78%。实际泵功 1.07122 W，尚未匹配 1.2 W。原页另有 Table 6 上下限标签与数值方向冲突。Table 7 的 D 标签与 §5 的下层高度文字不同。Eq. (24) 印刷温差方向及分子面积待核。 | `PS-V-R07`、`PS-O-R01`、`PS-O-R02` 复算后维持主比较资格，推断分母保留为诊断，回归编码待核。 `PS-V-F06` 阻塞自动算 Nu。 [原论文](https://doi.org/10.3390/en14123585) · [Case 4 看板](https://docs.google.com/spreadsheets/d/19MxNKHp3cPE0alsO-9nEU8pdJhT0kLyK_f0VgLgki3U/edit#gid=1833020081&range=A12:H29) |
| P048 | Re 117.1 平直锂通道的表列压降 35.159 Pa 对 35.3 Pa，相对差约 0.40%。Nu 的条件比较约 0.10494 对 20.09，差约 99.48%。后续有效物性求值、原生收敛、热量闭合及重开后仍得约 0.10488。原文式 (17) 将加热面积和接触面积区分，流体均温权重在已核处未展开。 | `PS-V-R03`、`PS-V-F03` 与 `PS-D-R04` 保留热流、面积、平均方式与物性四条证据链，鼓励从保存场复算。当前记录无法确认差异的最终原因。 [原论文](https://doi.org/10.3390/mi14071366) · [偏差封存](https://docs.google.com/spreadsheets/d/19MxNKHp3cPE0alsO-9nEU8pdJhT0kLyK_f0VgLgki3U/edit#gid=1102051526&range=A6:K6) |

CAND010 的 Eq. (15) 在分子和分母都出现 Nu 比值，正文同时描述摩擦因子。P048 的 Eq. (20) 则明确使用摩擦因子比。已目视核对原页，两份公式保持各自来源，CAND010 原意卡保留 BLOCKED。 [CAND010](https://doi.org/10.3390/en14206764) · [P048](https://doi.org/10.3390/mi14071366)

[复算与负例记录](checks.json) 含三网格 GCI、验证合成不确定度、Nu、Darcy/Fanning、体积加权温度、Morris/Jansen、编码符号、性能因子及两目标支配的计算。四个历史案例与六组算例在本轮均执行离线检查。实际求解、验证和独立留出继续沿用原项目证据与任务准入。
