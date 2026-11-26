# 材料与传热

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="F07"></a>

## F07 · 由总功率计算均匀体积热源

**verified** · 2019 R1 / 2021 R1

已知某实体的总发热量，单元区要求输入 W/m³。 用总功率除以实际受热实体区体积写入均匀能量源。几何变化后重新计算体积。

核对时，对相同区域积分源项并核对总瓦数。

适用于均匀体热源；表面热流和非均匀功率分布需要自己的换算。

来源 Fluent入门L05_物理模型设置 · src-130f1d19af3c09c2 · PDF p. 24 ｜ FLU_GSN_2021R1_EN_LE06_Physics · src-909d91d15468ce7a · PDF p. 28 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 23

关联阅读 [M11 · Heat Sink 教程用积分能量收支复查热源](thermal.md#M11)（不同求解器中输入功率与积分热量的检查。）

<a id="F11"></a>

## F11 · 核对辐射模型下的总热量收支

**verified** · 2019 R1 / 2021 R1

稳态模型同时计算辐射和其他传热或含体积源。 核验总能量时使用总传热率及相关源项；单独的辐射报告用于分解辐射贡献。

核对时，按控制体边界和各能量源记录总收支及符号；辐射净量还可能包含介质吸收。

有能量积累的瞬态控制体需要计入储能。

来源 Fluent入门L10_热传递 · src-52e016007fb8e14d · PDF p. 16 ｜ FLU_GSN_2021R1_EN_LE12_HeatTransfer · src-aba88872a907bade · PDF p. 16 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 35

<a id="F15"></a>

## F15 · 区分器件平均温度与热点温度

**verified** · 2021 R1

评价带散热器电子组件的温度。 在产热固体区建体积平均温度报告。目标是指定表面最高温时，求该面的相应极值；目标是器件内部热点时，在固体体域求最大值。

核对时，核对域、表面、采样算子和网格敏感性。与实验测点比较时另行匹配位置及测量范围。

整面极值不能代表任意测点。缺少探头位置或测量范围时，保留该项待核。

来源 FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 21 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 28 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 38 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 4 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 47

关联阅读 [M22 · Fluent 24.2 报告定义与保存的时间序列](post.md#M22)（把局部极值或体积均温定义成独立报告。）

<a id="F24"></a>

## F24 · 用实际外部环境确定壁面热边界

**verified** · 2021 R1 / 2019 R1

外界流体没有显式建模，同时存在对流或辐射散热。 区分已知壁温、热流和以外部环境近似的混合壁面，给后者提供有依据的换热系数、环境温度和辐射参数。

核对时，记录外侧区域是否显式求解、每个输入的来源及边界区域。

内部共轭界面应按实际模型处理，不能重复叠加用于替代外部区域的换热条件。

来源 FLU_GSN_2021R1_EN_LE12_HeatTransfer · src-aba88872a907bade · PDF p. 6 ｜ Fluent入门L10_热传递 · src-52e016007fb8e14d · PDF p. 6

<a id="F25"></a>

## F25 · 检查自然对流的密度与重力设置

**verified** · 2021 R1

需要由温差产生的浮力驱动流动。 联合核对重力方向、密度随温度变化的模型以及操作压力相关定义。

核对时，查边界的压力口径和实际区域中的密度设置。

常密度模型能否产生所需浮力须依所选近似核对。

来源 FLU_GSN_2021R1_EN_LE12_HeatTransfer · src-aba88872a907bade · PDF p. 10 ｜ FLU_GSN_2021R1_EN_WS12_Electronics_Cooling · src-b993fcca9e1b8f5f · PDF p. 20

<a id="M09"></a>

## M09 · COMSOL 6.3 的 Inflow 使用上游热状态

**verified** · 6.3

已知非固体入口上游温度，比较 Inflow 与入口定温模型时 按照实验的测温位置选择入口条件。Inflow 将上游状态换算为入口焓通量，入口面的解温度可以与上游值不同。

核对时，分别记录上游输入温度、边界解温度和附近热源。

若实验明确将入口面钳制为定温，需另行核查该定温条件。

来源 Heat Transfer Module User’s Guide · COMSOL63-HEAT-PDF · PDF p. 675

<a id="M10"></a>

## M10 · COMSOL 6.4 的 Inflow 使用上游热状态

**verified** · 6.4

已知非固体入口上游温度，比较 Inflow 与入口定温模型时 按照实验的测温位置选择入口条件。Inflow 将上游状态换算为入口焓通量，入口面的解温度可以与上游值不同。

核对时，分别记录上游输入温度、边界解温度和附近热源。

若实验明确将入口面钳制为定温，需另行核查该定温条件。

来源 Heat Transfer Module User’s Guide · COMSOL64-HEAT-PDF · PDF p. 702 ｜ COMSOL 6.4 - Inflow · COMSOL64-INFLOW · #567058 ｜ COMSOL 6.4 - Inflow · COMSOL64-INFLOW · Inflow，Eq. (6-16) 前后、Upstream Properties

关联阅读 [P07 · 核查实际热输运耦合和控制体能量项](thermal.md#P07)（COMSOL 上游流入热条件。）

<a id="M11"></a>

## M11 · Heat Sink 教程用积分能量收支复查热源

**verified** · 6.4

复查 COMSOL 6.4 电子散热器共轭换热示例时 分别读取基底总热源、净能量传输率及蓄能率。比较稳态净输出与基底总输入，同时观察基底温度。

核对时，核对热源输入的单位为 W，并核对积分区域与符号约定。

示例的 1 W 和绝热外表面属于该模型；迁移到论文模型时重新确认。

来源 COMSOL 6.4 - Heat Sink · COMSOL64-HEATSINK · #701817 ｜ COMSOL 6.4 - Heat Sink · COMSOL64-HEATSINK · #702731

关联阅读 [P07 · 核查实际热输运耦合和控制体能量项](thermal.md#P07)（以积分热量核查热源。） ｜ [F07 · 由总功率计算均匀体积热源](thermal.md#F07)（不同求解器中输入功率与积分热量的检查。）

<a id="M12"></a>

## M12 · Fluent 24.2 双侧壁的传热耦合

**verified** · 2024 R2 (24.2)

固体与流体相邻且界面由一对壁面表示时 检查壁面对应的 shadow 和相邻区域，将符合物理假设的双侧壁设置为热耦合，保留薄壁热阻的真实参数。

核对时，读回两侧名称、热条件及壁厚，确认热流能在正确的区域间交换。

适用于 two-sided wall；具有独立热边界或实际隔热层的界面另按实物建模。

来源 Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 1472

关联阅读 [P07 · 核查实际热输运耦合和控制体能量项](thermal.md#P07)（Fluent 双侧壁耦合语义。）

<a id="M13"></a>

## M13 · Fluent 24.2 的材料输入可能启用能量方程

**verified** · 2024 R2 (24.2)

材料中引入需要能量方程的物性关系时 重新查看已启用的物理模型，逐边界补核热条件和相关热参数。

核对时，检查能量方程状态，以及温度相关物性被分配到的材料区域。

是否自动启用取决于所选物性关系。

来源 8.1. Defining Materials · FLUENT242-MATERIAL · 8.1 Defining Materials, opening paragraphs ｜ 8.1. Defining Materials · FLUENT242-MATERIAL · §8.1 Defining Materials

<a id="M14"></a>

## M14 · Fluent 24.2 的温变物性线性分段表

**verified** · 2024 R2 (24.2)

材料属性选择 piecewise-linear 时 按温度递增输入不超过 50 个数据对，检查温度覆盖范围，在边界和内部采样点回读属性。

核对时，超出区间时按最近端值检查求值，与原实验有效温区分别记录。

该上限对应每种属性的此种输入类型；多项式与分段多项式须查各自定义。

来源 8.2. Defining Properties Using Temperature-Dependent Functions · FLUENT242-TABLE · #flu_ug_sec_material_piece ｜ Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 1619 ｜ Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 1620 ｜ 8.2. Defining Properties Using Temperature-Dependent Functions · FLUENT242-TABLE · 8.2.2 / Piecewise-Linear Profiles，Figure 8.13 后 Important

关联阅读 [M15 · Fluent 23.1 分段线性表的本机构建容量](thermal.md#M15)（相邻版本的文档与安装件各自限定适用域。）

<a id="M15"></a>

## M15 · Fluent 23.1 分段线性表的本机构建容量

**verified** · 2023 R1 (23.1)

检查安装的 23.1 表写入、数值截断或预期精度时 按本地头文件核对槽位和存储类型，再用安装版读回表。100 个 float 槽在交替存放 x、y 时最多容纳 50 对。

核对时，在节点及区间内部比较写入目标值、读回值和求值结果。

本地头文件只证明数据结构和接口类型；是否写入成功需原生读回。

来源 cxpoly · src-97a825e54bdaad1a · cxpoly.h lines 13, 61–67, 97–98 ｜ cxpoly · src-97a825e54bdaad1a · cxpoly.h lines 13–16, 57–68, 83–88, 95–100 ｜ cxpoly · src-97a825e54bdaad1a · lines 13-16

关联阅读 [M14 · Fluent 24.2 的温变物性线性分段表](thermal.md#M14)（相邻版本的文档与安装件各自限定适用域。）

<a id="P07"></a>

## P07 · 核查实际热输运耦合和控制体能量项

**verified** · COMSOL Automatic 0.7.0 / Paper2Simu 0.5.0

准备验收共轭传热，或热平衡表面上异常 读取求解域、流体对流速度来源、材料、热源和活动热边界，再按选定控制体列出适用的储能、焓流、导热和其他功热项。

核对时，逐项核对积分面、方向、单位和解身份，记录缺失通量。

旧版项目清单偏好特定耦合节点，新版按有效方程和耦合验证。旧默认阈值不作验收依据。

来源 cht-coupling-energy-gates · src-39663cbd8e2fabe1 · lines 7-26 ｜ cht-coupling-energy-gates · src-452b00d1885884b8 · lines 13-36 ｜ model-consistency · src-29e41f0e607e2681 · lines 2-6 ｜ cht-coupling-energy-gates · src-452b00d1885884b8 · lines 13-45

关联阅读 [M11 · Heat Sink 教程用积分能量收支复查热源](thermal.md#M11)（以积分热量核查热源。） ｜ [M12 · Fluent 24.2 双侧壁的传热耦合](thermal.md#M12)（Fluent 双侧壁耦合语义。） ｜ [M10 · COMSOL 6.4 的 Inflow 使用上游热状态](thermal.md#M10)（COMSOL 上游流入热条件。）

<a id="P08"></a>

## P08 · 区分对流热通量边界与流体入口温度

**verified** · Paper2Simu 0.5.0

在固体外壁设置对流散热时 在该模型对应的边界施加外部换热系数与外部温度，核对作用面和热流方向；以源项及积分热流作量纲一致的校验。

核对时，回读 h、外部温度、边界和总热流。

历史机构示例针对 COMSOL 6.4。不能把外部对流等同于显式求解的流固耦合。

来源 conduction-6.4 · src-7cc5bd4be54b8ae6 · lines 15-24 ｜ api-patterns · src-a6e3536594d5e151 · lines 4-5 ｜ repair-validation · src-0e1eac17ada03101 · lines 7-10 ｜ api-patterns · src-a6e3536594d5e151 · lines 2-5
