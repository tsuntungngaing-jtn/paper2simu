# 报告、守恒与验证

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="F08"></a>

## F08 · 区分边界通量、表面统计和域统计

**verified** · 2019 R1 / 2021 R1

将仿真输出与论文中的均值、极值或总量比较。 跨控制面质量或能量流用通量报告。面量用相应表面报告，域量选单元区报告。明确总和、平均或极值。

核对时，保存变量、算子、权重和所选面或域。

来源没有给出平均方式时保留候选定义。

来源 Fluent入门L06_后处理 · src-e8902e9070d84e42 · PDF p. 12 ｜ FLU_GSN_2021R1_EN_LE07_Results · src-a9586dd0517e692f · PDF p. 14

关联阅读 [M23 · Fluent 24.2 的表面积分依赖所选表面和数据来源](post.md#M23)（表面、数据来源与算子的语义。） ｜ [M24 · Fluent 24.2 质量加权平均使用绝对质量通量](post.md#M24)（质量加权与净流率有不同定义。）

<a id="F13"></a>

## F13 · 各开口分别导出有符号质量通量

**verified** · 2021 R1

单相、无体质量源的稳态管路包含多个入口或出口。 在同一解上列出各开口的质量流率，按报告符号求净值，再分别比较各出口分流。

核对时，以有量纲的净通量和明确分母报告相对失衡。

该练习的 Fluent Flux Reports 中流入为正；换算子或控制体时重查方向。总量闭合不能证明各支路分配正确。

来源 FLU_GSN_2021R1_EN_WS02_Mixing_Tee · src-0d8a671699481839 · PDF p. 38 ｜ FLU_GSN_2021R1_EN_WS05_Manifold · src-28341a206ac50804 · PDF p. 36

<a id="F14"></a>

## F14 · 用两个截面的静压均值定义压降

**verified** · 2021 R1

论文或试验定义压降为指定进出口截面的面积平均静压差。 对两个截面分别提取面积加权静压，再按入口减出口求差。

核对时，核对截面位置、单位、权重及压力基准。

只有出口截面均值确为零表压时才可直接报告入口均值。总压损失需另建报告。

来源 FLU_GSN_2021R1_EN_WS06_Duct_Vanes · src-df4a9e27a7a6b9e8 · PDF p. 30 ｜ FLU_GSN_2021R1_EN_WS07_Obstacles · src-b4615d12bb74dbf6 · PDF p. 28

关联阅读 [M23 · Fluent 24.2 的表面积分依赖所选表面和数据来源](post.md#M23)（压降依赖截面与报告定义。）

<a id="F20"></a>

## F20 · 用基础报告组合定义差值监控

**verified** · 2021 R1

监控两出口极值的差异。 先各建相同变量、相同统计方式的独立出口报告，再建按明确顺序相减的表达式，保存报告文件。

核对时，用两个基础报告的同一迭代数值重算差值。

顶点最大与面积平均不能混用，差的方向与出口次序联动。

来源 FLU_GSN_2021R1_EN_WS09_Solving · src-4666497a9c463eb9 · PDF p. 26 ｜ FLU_GSN_2021R1_EN_WS09_Solving · src-4666497a9c463eb9 · PDF p. 28

关联阅读 [M22 · Fluent 24.2 报告定义与保存的时间序列](post.md#M22)（报告定义和保存历史。）

<a id="F22"></a>

## F22 · 明确无量纲力系数采用的参考面积

**verified** · 2021 R1

同一几何需要与实验比较升阻力系数。 读取用于无量纲化的参考值，特别是面积和二维模型采用的厚度；使用原研究规定的面积定义。

核对时，把参考面积及组成尺寸并列报告，核实 Compute From 导入的值。

翼型示例的弦长与厚度只适用于该算例。

来源 FLU_GSN_2021R1_EN_WS10_Airfoil · src-8ea10782fb572eca · PDF p. 26

<a id="F26"></a>

## F26 · 用建立后的瞬态信号估计主频

**verified** · 2021 R1

从探针信号估计自然振荡或涡脱落频率。 记录采样间隔与时窗，截去初场影响明显的段，然后对剩余信号作频谱分析。

核对时，报告选窗和频率分辨率，并用较长记录检查主峰位置是否稳定。

练习中的起点与时窗只对当时的算例有效。

来源 FLU_GSN_2021R1_EN_WS13_Vortex_Shedding · src-33248bd8edea4f73 · PDF p. 44 ｜ FLU_GSN_2021R1_EN_WS13_Vortex_Shedding · src-33248bd8edea4f73 · PDF p. 46

<a id="M22"></a>

## M22 · Fluent 24.2 报告定义与保存的时间序列

**verified** · 2024 R2 (24.2)

需要比较迭代、时间步或网格间的量时 为指定变量、位置与运算建立 report definition，选择适当的输出频率和 report file 保存记录。

核对时，读取报告文件头和时间或迭代列，对照求解设置检查采样。

报告定义、报告文件和报告曲线属于不同对象；创建定义不代表已经保存历史。

来源 41.2. Monitoring and Reporting Solution Data · FLUENT242-MONITOR · 41.2 Monitoring and Reporting Solution Data ｜ Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 4132

关联阅读 [F20 · 用基础报告组合定义差值监控](post.md#F20)（报告定义和保存历史。） ｜ [F15 · 区分器件平均温度与热点温度](thermal.md#F15)（把局部极值或体积均温定义成独立报告。）

<a id="M23"></a>

## M23 · Fluent 24.2 的表面积分依赖所选表面和数据来源

**verified** · 2024 R2 (24.2)

比较入口、出口或任意截面的报告时 注明表面是 face zone 还是后处理截面，以及使用的量属于流率、积分还是平均。流率计算在区域面可使用面通量，后处理表面使用单元值。

核对时，保存报告定义的表面身份、所用运算和单位，再进行论文对照。

各运算的取值规则不同；普通平均与流率需分别解释。

来源 25.3. Surface Integration · FLUENT242-SURFACE · 25.3 Surface Integration ｜ Ansys Fluent Theory Guide · FLUENT242-THEORY-PDF · PDF p. 1086

关联阅读 [F08 · 区分边界通量、表面统计和域统计](post.md#F08)（表面、数据来源与算子的语义。） ｜ [F14 · 用两个截面的静压均值定义压降](post.md#F14)（压降依赖截面与报告定义。）

<a id="M24"></a>

## M24 · Fluent 24.2 质量加权平均使用绝对质量通量

**verified** · 2024 R2 (24.2)

解释带有局部回流的截面平均温度或焓时 先确定目标是质量加权平均还是净输运率。前者逐面使用质量通量绝对值作权重。

核对时，核对报告单位、表面和回流区域，另保留带方向的净流率。

多相时厂商仅推荐此报告用于混合物层级变量。

来源 Ansys Fluent Theory Guide · FLUENT242-THEORY-PDF · PDF p. 1089

关联阅读 [F08 · 区分边界通量、表面统计和域统计](post.md#F08)（质量加权与净流率有不同定义。）

<a id="M25"></a>

## M25 · Fluent 24.2 轴对称 UDF 宏的周向基准

**verified** · 2024 R2 (24.2)

用 F_AREA 或 F_FLUX 等适用的 C 宏计算轴对称全周积分时 先核实该宏给出每弧度量，只有从该基准转成整周积分时才乘 2π。

核对时，单独记录原宏、周向基准及最终单位，并与相同定义的原生报告比较。

仅限适用宏；其他报告、平均值或已全周积分的量需分别核查。

来源 3.2. Data Access Macros · FLUENT242-AXIS-UDF · #flu_udf_sec_axisymmetric_considerations

<a id="P15"></a>

## P15 · 解释收敛图前核对原生曲线含义

**verified** · Paper2Simu 0.5.0

归档 COMSOL 收敛图或据图诊断数值问题 读取求解类型、纵轴与原生日志，区分残差、解误差和时间步相关量。保存日志并验证曲线数据是否随模型归档。

核对时，回读图线指标及对应迭代或时间，说明未保存的数据。

仅有截图或文件存在无法确认原始序列。

来源 comsol-observability-and-desktop · src-520a7a834a8a849a · lines 9-14 ｜ native-convergence-policy · src-57899eb34decaabe · lines 16-22 ｜ comsol-observability-and-desktop · src-520a7a834a8a849a · lines 11-14
