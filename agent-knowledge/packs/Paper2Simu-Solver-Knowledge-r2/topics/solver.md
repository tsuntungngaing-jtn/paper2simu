# 求解、湍流与瞬态

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="F09"></a>

## F09 · 将残差、守恒与目标量分别判读

**verified** · 2019 R1 / 2021 R1 / 待核

判断稳态迭代是否充分。 并列查看方程残差、整体收支和目标量历史，例如压降是否仍有系统漂移。

核对时，分别记录残差轨迹、收支及目标量平台期。

残差是离散方程失衡尺度。判断物理准确性还需另核网格、边界和模型。

来源 Fluent入门L07_求解 · src-12aa76c26dc11eff · PDF p. 14 ｜ FLU_GSN_2021R1_EN_LE09_Solution · src-73db8a9374dc4acc · PDF p. 16 ｜ FLU_GSN_2021R1_EN_LE09_Solution · src-73db8a9374dc4acc · PDF p. 22 ｜ Fluent Solver进阶 · src-b246ff73e1ad908a · PDF p. 20 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 32 ｜ FLU_GSN_2021R1_EN_WS09_Solving · src-4666497a9c463eb9 · PDF p. 11

关联阅读 [M21 · Fluent 24.2 把目标积分量与残差一起监测](solver.md#M21)（残差与工程目标积分交叉审查。）

<a id="F10"></a>

## F10 · 记录入流与回流的湍流条件

**verified** · 2019 R1 / 2021 R1

湍流从入口或压力出口的回流区域进入计算域。 记录输入的是湍流强度配长度尺度、水力直径、黏度比，还是直接输入模型变量。

核对时，用实验入口剖面可得性及所选模型核对，并记录默认值来源。

倒台阶案例中入口剖面改善结果，不能据此确认网格独立或其他案例精度。

来源 Fluent入门L09_湍流 · src-eb1a343ac9985e26 · PDF p. 20 ｜ FLU_GSN_2021R1_EN_WS11_Backward_Step · src-a418724f2c74aace · PDF p. 40

<a id="F12"></a>

## F12 · 以最快相关变化选瞬态时间步

**verified** · 待核 / 2021 R1

慢变的平均温度与快变的速度或周期信号同时存在。 比较相关物理时间尺度，选择可解析关心变化且满足数值稳定性的步长。

核对时，在更小步长下比较目标历程或周期，分开记录步内迭代收敛。

课件中的每周期采样数及 Courant 数为示例，取值取决于格式、网格和物理过程。

来源 Fluent入门L11瞬态分析 · src-ce3eec896a95d917 · PDF p. 8 ｜ FLU_GSN_2021R1_EN_LE13_Transient · src-9c3596455d29210f · PDF p. 8 ｜ FLU_GSN_2021R1_EN_LE13_Transient · src-9c3596455d29210f · PDF p. 10

关联阅读 [M20 · Fluent 24.2 选择瞬态自适应步长的时间尺度](solver.md#M20)（按物理时间尺度选择步长。）

<a id="F17"></a>

## F17 · 记录表压与绝对压力的基准

**verified** · 2021 R1

边界、材料或论文使用不同的压力口径。 解释相对压力时读取 operating pressure，核对同一单位下的绝对压等于操作压力加相对压力。

核对时，比较两个点的差压前统一压力变量、静压或总压口径。

含重力时还要查对应版本对压力变量的定义。

来源 FLU_GSN_2021R1_EN_LE06_Physics · src-909d91d15468ce7a · PDF p. 12 ｜ FLU_GSN_2021R1_EN_LE12_HeatTransfer · src-aba88872a907bade · PDF p. 10

<a id="F19"></a>

## F19 · 跨网格插值后按区域复核初场

**verified** · 2021 R1

用旧解向改变分区或物理范围的新网格提供初始条件。 完成插值后查控制台变量列表，在切面上分别检查流体及固体场；若旧场错误映入固体，按有依据的初值局部修补。

核对时，保留修补区域和更新后的初场视图。

插值只建立初场，仍需在目标工况上重新收敛。

来源 FLU_GSN_2021R1_EN_WS09_Solving · src-4666497a9c463eb9 · PDF p. 17 ｜ FLU_GSN_2021R1_EN_WS09_Solving · src-4666497a9c463eb9 · PDF p. 18

<a id="F21"></a>

## F21 · 用同一目标量比较网格与离散方案

**verified** · 2021 R1

关注最大 Nu 等对分辨率敏感的指标。 在相同工况与物理模型下，用一组网格比较同一目标量，再分别评估离散格式变化。

核对时，记录网格标识、离散格式、目标量定义和变化趋势。

单一培训算例中高阶解更接近细网格结果，无法据此建立跨案例误差界限。

来源 FLU_GSN_2021R1_EN_LE10_BestPractices · src-96476ef97c4e6c45 · PDF p. 9 ｜ FLU_GSN_2021R1_EN_LE10_BestPractices · src-96476ef97c4e6c45 · PDF p. 10

<a id="M07"></a>

## M07 · COMSOL 6.3 的压力点约束用于确定压力水平

**verified** · 6.3

流动边界条件没有给定压力水平时 确认该流体区域需要压力基准，再在合适点上约束压力，记录界面参考压力和输入的相对压力。

核对时，核对所选点、参考压力及重力/静水压补偿设置。

已有压力边界时先审查约束是否冗余。

来源 CFD Module User’s Guide · COMSOL63-CFD-PDF · PDF p. 153 ｜ COMSOL 6.3 - Pressure Point Constraint · COMSOL63-PRESSURE · #4474497 ｜ COMSOL 6.3 - Pressure Point Constraint · COMSOL63-PRESSURE · Pressure Point Constraint / Pressure Constraint

关联阅读 [P05 · 重建后用物理角色重新识别选区](geometry.md#P05)（压力基准点需取得实际点选区。）

<a id="M08"></a>

## M08 · COMSOL 6.4 的压力点约束用于确定压力水平

**verified** · 6.4

流动边界条件没有给定压力水平时 确认该流体区域需要压力基准，再在合适点上约束压力，记录界面参考压力和输入的相对压力。

核对时，核对所选点、参考压力及重力/静水压补偿设置。

已有压力边界时先审查约束是否冗余。

来源 CFD Module User’s Guide · COMSOL64-CFD-PDF · PDF p. 161

<a id="M20"></a>

## M20 · Fluent 24.2 选择瞬态自适应步长的时间尺度

**verified** · 2024 R2 (24.2)

考虑用 CFL 自适应步长进行瞬态计算时 明确所用时间尺度。默认对流设置适合相应的低速不可压流动，若过程由表面张力或网格变形时间尺度控制，需重新选择步长策略。

核对时，记录 CFL 方法、所选时间尺度和实际步长范围。

给定的 CFL 数本身不能证明对目标物理过程已有时间精度。

来源 Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 3694

关联阅读 [F12 · 以最快相关变化选瞬态时间步](solver.md#F12)（按物理时间尺度选择步长。）

<a id="M21"></a>

## M21 · Fluent 24.2 把目标积分量与残差一起监测

**verified** · 2024 R2 (24.2)

判定稳态解是否收敛时 登记残差的缩放方式，同时监测热传递或压降等当前研究关心的量，检查这些量的迭代历史。

核对时，核对残差和目标量是否同时支持稳态判断。

初始化方式和缩放影响残差量级，默认残差门槛的适用性依算例判断。

来源 Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 3772 ｜ Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 3773

关联阅读 [F09 · 将残差、守恒与目标量分别判读](solver.md#F09)（残差与工程目标积分交叉审查。）

<a id="P09"></a>

## P09 · 按活动湍流接口设置入口变量

**verified** · Paper2Simu 0.5.0

复用 COMSOL 的 k-ε 入口处方或移植到其他湍流接口 读回湍流模型和入口变量模式。选用强度与长度尺度模式时，输入无量纲强度及带长度单位的尺度，并核对活动字段。

核对时，检查接口标识、变量模式、数值与单位。

该处方在 6.4 的特定 k-ε 接口有项目证据。SST 需另查 k、ω 与近壁处理。

来源 kepsilon-6.4 · src-938b5203a3071ad6 · lines 15-29 ｜ api-patterns · src-a6e3536594d5e151 · lines 7-12 ｜ repair-validation · src-0e1eac17ada03101 · lines 8-11 ｜ api-patterns · src-a6e3536594d5e151 · lines 8-12

<a id="P10"></a>

## P10 · 将 SST 停滞定位到变量组

**verified** · Paper2Simu 0.5.0

稳态 SST 与传热耦合迭代停滞 逐组读取残差或解误差、缩放与终止条件，区分流场、温度和 k/ω。用隔离副本分别检查流动、固定流场传热、全耦合。

核对时，保留每个诊断分支的初场、实际活动物理与最终数据集。

单物理分支仅回答对应问题。

来源 sst-pressure-validation · src-e0dadaf01330705d · lines 3-9 ｜ sst-diagnostics-6.4 · src-82166b30b6896ce1 · lines 11-25 ｜ sst-diagnostics-6.4 · src-82166b30b6896ce1 · lines 17-23

<a id="P11"></a>

## P11 · 区分分阶段初始化、转段和最终收敛

**verified** · Paper2Simu 0.5.0

求解从简化方程或初始化阶段转入目标全耦合模型 记录每段的活动物理、转段条件、继承的初始场和最终阶段原生终止原因。

核对时，后处理所用解须对应完整目标阶段。另查目标量与守恒。

转段标准随模型定义；不从训练案例移植阈值。

来源 staged-solve-contract · src-4183c40acbc17ef4 · lines 3-9 ｜ native-convergence-policy · src-57899eb34decaabe · lines 16-25 ｜ staged-solve-contract · src-4183c40acbc17ef4 · lines 5-11

<a id="P12"></a>

## P12 · 筛选数值设置时对照物理响应

**verified** · Paper2Simu 0.5.0 / fluent-cfd

准备改变非线性、离散或分离式求解设置 在可恢复的基线副本上登记发生变化的设置，比较终止原因、迭代轨迹与预先定义的物理量。

核对时，只有目标方程与可比工况一致时才比较耗时和结果。

模拟时长、重试与提交安排由当前运行任务给定。

来源 nonlinear-solver-tuning · src-bcfa81651395912f · lines 55-65 ｜ numerics-and-convergence · src-68414424d4a1b189 · lines 5-11 ｜ nonlinear-solver-tuning · src-bcfa81651395912f · lines 55-61

<a id="P18"></a>

## P18 · 按流动及近壁目标选择求解设置

**verified** · fluent-cfd

新建 Fluent 内流换热工况 先记录可压缩性、雷诺数、分离或转捩可能、壁面目标和热条件，再挑选求解器、湍流模型和近壁分辨率。

核对时，核对实际壁面处理、局部网格和目标可观测量。

层流或湍流判别需要与几何和工况相符。

来源 solver-selection · src-de39b03dc959542b · lines 5-11 ｜ turbulence-and-wall-treatment · src-c801dbcc01c70598 · lines 5-15 ｜ SKILL · src-9b594492ca6de9c6 · lines 10-15 ｜ validation-checklist · src-99c4c33e642a5e7d · lines 13-18
