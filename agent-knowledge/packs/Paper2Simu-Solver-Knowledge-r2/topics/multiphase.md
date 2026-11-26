# 多相与相间耦合

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="F01"></a>

## F01 · 选择多组分或多相描述

**verified** · 2020 R1

同一流域包含多种物质。 先判断是否存在需表示的宏观相界面。分子级混合可用组分描述，互不相溶且形状是目标时考虑 VOF。

核对时，把要解析的界面尺度和局部网格尺度并列记录。

小于网格的分散结构不能靠此项判据确认已被 VOF 解析。

来源 FLU_Mphase_2020R1_EN_ILT_LE01_Introduction · src-d5c41cd411c24dd0 · PDF p. 8 ｜ FLU_Mphase_2020R1_EN_ILT_LE02_VOF · src-ac3eedd502ab8012 · PDF p. 4

关联阅读 [M19 · Fluent 24.2 VOF 的流体和求解器前提](multiphase.md#M19)（明确 VOF 的使用条件。）

<a id="F02"></a>

## F02 · 确定离散相与连续相的反馈方向

**verified** · 2020 R1

采用 DPM 描述稀疏颗粒或液滴。 先说明颗粒是否反过来影响载流体；仅载流体影响颗粒对应单向，两相相互作用对应双向。

核对时，记录反馈假设及涉及的质量、动量或热交换。

耦合方向定义本身不证明指定工况可忽略反馈。

来源 FLU_Mphase_2020R1_EN_ILT_LE03_DPM · src-7ccc48e431ee2dc8 · PDF p. 12

<a id="F03"></a>

## F03 · 核对离散相轨迹的终态

**verified** · 2020 R1

从颗粒追踪输出统计逃逸或滞留。 核对已追踪、逃逸、未完成及其他终态；出现未完成时检查最大追踪步数与回流滞留两种解释。

核对时，保留终态计数及轨迹。区分数值轨迹与其代表的粒子流率。

一个数值轨迹可以代表大量真实颗粒。终止计数不能直接充当物理粒子数。

来源 FLU_Mphase_2020R1_EN_ILT_WS03.1_Using_DPM · src-80dc00c76a506baa · PDF p. 14 ｜ FLU_Mphase_2020R1_EN_ILT_WS03.1_Using_DPM · src-80dc00c76a506baa · PDF p. 22

<a id="F04"></a>

## F04 · 按初始液面设置体积分数

**verified** · 2020 R1

容器的气液区在初始时刻已知。 先选定初始液体占据的单元区域，在 Patch 中明确所编辑的相、变量和区域，再赋相应体积分数。

核对时，检查初场分布与实际液位相符，复核相名称和区域选择。

水箱练习对空气相赋零的做法只适用于该纯水区。

来源 FLU_Mphase_2020R1_EN_ILT_WS02.1_VOF_Tank_Flush · src-e478da9cd788d7dc · PDF p. 14 ｜ FLU_Mphase_2020R1_EN_ILT_WS02.1_VOF_Tank_Flush · src-e478da9cd788d7dc · PDF p. 16 ｜ FLU_Mphase_2020R1_EN_ILT_WS02.1_VOF_Tank_Flush · src-e478da9cd788d7dc · PDF p. 17

<a id="M19"></a>

## M19 · Fluent 24.2 VOF 的流体和求解器前提

**verified** · 2024 R2 (24.2)

需要追踪互不相溶流体的界面时 核实控制体被一相或多相填满，配置相体积分数和压力基求解器，共用一组动量方程。

核对时，确认任务关注界面和体积分数，并核对相定义及求解器类型。

无法用相体积分数为零的空域代替待定义流体。

来源 Ansys Fluent Theory Guide · FLUENT242-THEORY-PDF · PDF p. 651

关联阅读 [F01 · 选择多组分或多相描述](multiphase.md#F01)（明确 VOF 的使用条件。）
