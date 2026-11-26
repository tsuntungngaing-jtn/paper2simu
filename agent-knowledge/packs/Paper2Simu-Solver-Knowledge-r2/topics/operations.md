# 版本、连接与恢复

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="F16"></a>

## F16 · 确认工作流支持当前几何及许可

**verified** · 2021 R1

把旧版单窗口培训步骤转为自动化工作流。 先核实几何是否适用 Watertight Geometry 工作流，再按已安装版本和许可证核对任务所需的模块。

核对时，记录可用功能、版本与使用的网格工作流。

课程介绍和演示页只适合作路由。2021 课件的许可范围不直接用于其他发行版。

来源 FLU_GSN_2021R1_EN_LE01.0_Intro_to_ANSYS · src-f6d101962053404f · PDF p. 2 ｜ FLU_GSN_2021R1_EN_LE02.2_Single_Win_Demo · src-c825db2d1a869ad1 · PDF p. 2 ｜ FLU_GSN_2021R1_EN_LE05_Workspace · src-9f01d7790355eb97 · PDF p. 4

<a id="F18"></a>

## F18 · 让每个设计点具有可回查的数值输出

**verified** · 2021 R1

使用 Workbench 扫描几何或入口参数。 把所需报告设为输出参数，按输入组合建立设计点。将输出表和对应工况一并归档。

核对时，重开算例前核对 Current 设计点以及结果是否保留。

工作坊中可把已保留设计点切换为 Current。表中有数值不能证明任一工况都保留完整场文件。

来源 FLU_GSN_2021R1_EN_LE08_Parameteric_Workflow · src-445e08614f98975c · PDF p. 22 ｜ FLU_GSN_2021R1_EN_LE08_Parameteric_Workflow · src-445e08614f98975c · PDF p. 28 ｜ FLU_GSN_2021R1_EN_WS08_Valve · src-8f4082e6a9929f89 · PDF p. 50

<a id="P01"></a>

## P01 · 确认求解器会话、工具能力和模型身份

**verified** · Paper2Simu 0.5.0 / COMSOL Automatic 0.7.0

重新连接 COMSOL，或在不同主机上复用旧项目时 读取实际服务模式、求解器版本、跟踪中的模型和已暴露的工具，再选择执行路径。

核对时，用读操作核实目标模型身份；未识别的连接单独记录。

工程环境做法。历史启动配置只说明原主机。

来源 connectors · src-fe2275dcf285d6f6 · lines 6-10 ｜ connectors · src-a2e99ffc1fa0ac6a · lines 6-10 ｜ SKILL · src-7ae7c7f9307028cf · lines 48-57 ｜ SKILL · src-7ae7c7f9307028cf · lines 50-55

<a id="P02"></a>

## P02 · 判断 Fluent 历史连接方式能否复用

**verified** · fluent-2022r1-autonomy / fluent-cfd / fluent-paper-reproduction

读到旧的 2022 R1 自主运行示例，或当前 MCP 的工具名称与示例不同 先取得当前求解器、提供方和会话能力。需按历史桥接重现实验时记录 batch/journal 路线，在副本上准备输入。

核对时，记录本次真实后端、目标 case/data 和工具回读。

示例中的机器路径、进程数和工具名仅属于对应部署。

来源 SKILL · src-41f87fb814e1b604 · lines 8-15 ｜ tool-guide · src-d5797504c4e856e4 · lines 3-9 ｜ pyfluent-mcp · src-15deca0d9fd1d5ab · lines 3-12 ｜ fluent-execution · src-e46446b5855e99e1 · lines 5-17

<a id="P03"></a>

## P03 · 把启动失败定位到许可、计算节点或连接握手

**verified** · Paper2Simu 0.5.0 / fluent-cfd

Fluent 启动超时或已有监听端口却无法进入求解会话 对齐本次启动的许可记录、求解器日志和连接器日志，记录最后成功阶段，并核对原进程身份后再安排诊断。

核对时，区分许可 checkout、计算节点和 gRPC readiness 三种证据。

旧主机的端口和权限调整不能直接推广。

来源 fluent-windows-mpi-preflight · src-91f186886d6b7bc5 · lines 5-13 ｜ fluent-licensing-preflight · src-195f0a5cb1c9d444 · lines 7-17 ｜ error-recovery · src-7e8d89cdbaeb350f · lines 5-10

<a id="P04"></a>

## P04 · 用版本手册和活动节点核对设置名

**verified** · Paper2Simu 0.5.0

跨 COMSOL 版本迁移，或设置被 API 拒绝 从活动节点枚举属性、对照同版参考；必要时用桌面录制的原生设置名。再次读取实际节点值与选择。

核对时，保存求解器 build、接口、设置前后值，复核方程与输入单位。

这里只核实 API 和当前设置；接口同名仍可能含义不同。

来源 agentic-official-alignment · src-2b174d5e686d3f12 · lines 55-63 ｜ api-patterns · src-a6e3536594d5e151 · lines 14-16 ｜ version-compatibility · src-677864e4a33c079d · lines 16-20 ｜ comsol-human-equivalent-workflow · src-09440e7d47085f70 · lines 24-31 ｜ comsol-human-equivalent-workflow · src-09440e7d47085f70 · lines 29-31

<a id="P16"></a>

## P16 · 冻结诊断假设后再归因

**verified** · Paper2Simu 0.5.0 / comsol-debug / fluent-paper-reproduction

模型结果与参考不符，准备改变材料、边界或参数 记录基线解、候选成因、可判别观测和预期方向，跟踪设置的实际读回，再报告修复、无效或仍待确认。

核对时，对照同定义目标量，保留原始失败与候选解。

离线记录只能验证提交的数据结构与内部一致性。

来源 knowledge-guided-recovery · src-e0fe986bbe016fbc · lines 7-21 ｜ SKILL · src-fbddb9c91bc7743a · lines 16-27 ｜ provenance · src-98050a7e1c17d0d9 · lines 5-11

<a id="P17"></a>

## P17 · 论文复刻时给每个关键输入保留来源

**verified** · fluent-paper-reproduction / COMSOL Automatic 0.7.0

材料、几何或边界参数来自论文、手册或默认库 把值、单位、物理定义、来源位置和确定性写入当前案例台账。原文空缺与条件假设分别追踪。

核对时，证据冲突保留各分支；模型保存后仍可回查所采用的输入。

项目技能对可追踪性的要求不构成求解器事实。

来源 evidence-workflow · src-a723a36a78931e52 · lines 3-12 ｜ SKILL · src-7959c091be421452 · lines 11-18 ｜ SKILL · src-7f468e60dc467640 · lines 55-63 ｜ evidence-workflow · src-a723a36a78931e52 · lines 3-13

<a id="P19"></a>

## P19 · 用边界与报告清单交接可复核的 Fluent 案例

**verified** · fluent-cfd / Paper2Simu 0.5.0

准备交接网格、设置、求解和后处理结果 按区域核对物理类型与输入单位，再记录终止原因、目标量、守恒、报告定义及实际解。重开保存的 case/data，复算同一报告。

核对时，检查复算前后的区域、单位、时间及运行身份。

各阶段验证保留自己的状态。求解器成功结束仅覆盖其中一项。

来源 boundary-conditions · src-057c1cba87272279 · lines 5-12 ｜ validation-checklist · src-99c4c33e642a5e7d · lines 20-32 ｜ workflow · src-fb935b7f0b0bcae5 · lines 5-12 ｜ native-supervised-workflow · src-372b324b8313a104 · lines 14-24 ｜ native-supervised-workflow · src-372b324b8313a104 · lines 19-24

<a id="X03"></a>

## X03 · 同一讲义按步骤限定 Fluent 发布版

**verified** · 2021 R1

使用 Mixing Tee 中生成表面网格的按角度分区选项。 先读取实际 Fluent release。课件第 10 页把这一步限定为 2021 R2，指示 R1 及更早跳过该步。

核对时，同时记录讲义封面版次与该页局部说明。

在更新版本上需查该版本相应菜单或任务定义。

来源 FLU_GSN_2021R1_EN_WS02_Mixing_Tee · src-0d8a671699481839 · PDF p. 1 ｜ FLU_GSN_2021R1_EN_WS02_Mixing_Tee · src-0d8a671699481839 · PDF p. 10
