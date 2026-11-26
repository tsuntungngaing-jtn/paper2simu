# 几何与选区

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="G01"></a>

## G01 · 添加零件后核对活动组件

**verified** · 19.0（文件标识） / 待核

多零件 CAD 装配需要增添对象 插入已有零件或创建组件后，在结构树定位它并激活目标组件，再在其中编辑。

核对时，检查新对象在预期父组件下，并区分顶层装配与当前编辑组件。

SpaceClaim 装配工作流。

来源 SCDM_CFD_Intro_19.0_M01_Lecture_Slides_Core_Skills · src-60e98536344bbf96 · PDF p. 21 ｜ Optional_Workshop_Module02_3D_Features · src-fa6b535c64d79b3d · slide 24

<a id="G02"></a>

## G02 · 把辅助轮廓设为布局曲线

**verified** · 19.0（文件标识）

草绘中心线或辅助定位线暂不参与成体 绘制前启用布局曲线选项，结束草绘后检查实际参与三维建模的轮廓。

核对时，辅助线与要拉伸的封闭轮廓分开。

仅适用于预期作为构造参考的曲线。

来源 SCDM_CFD_Intro_19.0_M02_Lecture_Slides_Creating_Geometry · src-b1ccce81caa63433 · PDF p. 9

<a id="G03"></a>

## G03 · 先定位实体干涉，再选择修复对象

**candidate** · 19.0（文件标识） / 待核

装配有重叠、接触关系不明或微小间隙 在剖面视图中定位交叠和间隙，检查待比较实体可见性，再选择要修改的体。

核对时，复查重叠区和接触面，确认改动发生在预期体上。

SpaceClaim 课件对自动选择待移除干涉体的度量描述不同。异形体须逐个核查实际修改对象。 复核缺口：修复课 p.18 写移除体积最大实体的干涉；另一份实际 PPT 第 6 张写包围盒较大的实体且仅通常体积较大。两种准则在异形体会不一致，自动删除对象需按具体部件与版本验证。

来源 SCDM_CFD_Intro_19.0_M03_Lecture_Slides_Repairing_Geometry · src-210c7f01383f7fbb · PDF p. 18 ｜ SCDM_CFD_Intro_19.0_WS4.2_Workshop_Instructions_Preparing_For_CFD_Analysis · src-5b04a65070cb276a · PDF p. 15 ｜ Optional_Workshop_Module03_Simplifications_Repairs · src-d3bd5f4cc77e00a4 · slide 6

<a id="G04"></a>

## G04 · 中面简化保留薄壁模型假设

**verified** · 19.0（文件标识）

拟用壳单元代表实体薄壁 按面选择或厚度范围生成中面，再核查所代表的壁厚和壳模型范围。

核对时，中面与原壁面成对，目标求解模型可承载壳表示。

对需要解析厚度方向梯度的实体须另判断。

来源 SCDM_CFD_Intro_19.0_M04_Lecture_Slides_CFD_Modeling · src-243f06402b095e66 · PDF p. 11

<a id="G05"></a>

## G05 · 记录传递到 Workbench 的几何入口

**verified** · 19.0（文件标识） / 2021 R1

从 SpaceClaim 或外部 CAD 启动几何前处理 选择关联已有几何单元或导入已保存模型，记录实际文件格式和目标分析系统。

核对时，在 Workbench 几何单元打开并核对预期模型。

中性格式和原生接口的能力取决于版本和许可。

来源 SCDM_CFD_Intro_19.0_M05_Lecture_Slides_SpaceClaim_to_Workbench · src-37923befea4d0a21 · PDF p. 10 ｜ FLU_GSN_2021R1_EN_LE01.1_SCDM_Basics · src-208d967c56b40424 · PDF p. 16

<a id="G06"></a>

## G06 · 编辑前区分面、体和组件

**verified** · 2019 R1 / 19.0（文件标识）

移动或拉伸看似完整的部件 确认选择层级及高亮实体，在属性面板读取当前选择，再用相应工具编辑。

核对时，编辑后核对目标是否整体移动，以及实体和曲面体数目。

SpaceClaim 直接建模的树结构未必记录每次位姿修改。

来源 CFX_GetStart_2019R1_L02.1_SCDM_基础 · src-c8139cc0ab687bae · PDF p. 8 ｜ CFX_GetStart_2019R1_L02.1_SCDM_基础 · src-c8139cc0ab687bae · PDF p. 12 ｜ SCDM_CFD_Intro_19.0_WS1.1_Workshop_Instructions_Basics · src-b6991b26653116a7 · PDF p. 8

<a id="G07"></a>

## G07 · 用内壁预览和独立显示核对流体域

**verified** · 2019 R1 / 19.0（文件标识） / 2021 R1

从管道、换热器或壳体的实体模型提取内流区域 先选界定开口的边面与腔内种子面，预览被润湿的面，生成后单独显示提取体。

核对时，树中出现新的体，入口、出口和内壁沿目标流道连通。

多个互不连通的腔体应分开核对。

来源 CFX_GetStart_2019R1_L03.1_SCDM_操作基础 · src-e16e6ae7b74f11d0 · PDF p. 6 ｜ SCDM_CFD_Intro_19.0_WS4.1_Workshop_Instructions_OPTIONAL_Mixing_Elbow · src-7aace50a4614e34e · PDF p. 9 ｜ SCDM_CFD_Intro_19.0_WS4.3_Workshop_Instructions_OPTIONAL_TubeBundle · src-53e635f848f883c2 · PDF p. 8 ｜ FLU_GSN_2021R1_EN_WS01.1_SCDM_Extracting_a_Fluid_Volume · src-7b4a276a5ea152eb · PDF p. 9 ｜ FLU_GSN_2021R1_EN_WS01.2_SCDM_Repair · src-e2fa966a5f4fea8c · PDF p. 8

<a id="G08"></a>

## G08 · 沿剖面检查内部孔径与相邻边

**verified** · 2019 R1 / 2021 R1 / 待核

内孔、接合或过渡的几何关系在外观图上不可见 在剖面模式定位实际截面与参考边，需要使孔径相接时将修改终点捕捉到相邻内边。

核对时，复核截面上的孔径、重叠和小台阶。

只有设计意图明确相接时才统一孔径。

来源 CFX_GetStart_2019R1_L04.1_几何处理和修复 · src-a3376486d960930d · PDF p. 5 ｜ FLU_GSN_2021R1_EN_LE01.2_SCDM_Geometry · src-4f6ca0df0471f295 · PDF p. 19 ｜ Optional_Workshop_Module02_3D_Features · src-fa6b535c64d79b3d · slide 38

<a id="G09"></a>

## G09 · 移动轴须与装配基准一致

**verified** · 2019 R1 / 2021 R1

支管旋转后交点或朝向错误 把移动控制器原点定位到两轴交点，选择所需轴和方向再旋转整个体。

核对时，从模型坐标检查支管朝向和交点，记录轴的正负方向。

示例旋转角依初始姿态而变。

来源 CFX_GetStart_2019R1_L05.1_SCDM_主要建模工具 · src-4cb3c0f70abf3ee7 · PDF p. 7 ｜ FLU_GSN_2021R1_EN_WS01.3_SCDM_Mixing_Tee_Geometry · src-7f6699545fc56a2b · PDF p. 22

<a id="G10"></a>

## G10 · 按设计意图分别新增或移除圆角

**verified** · 19.0（文件标识）

模型需要重建转角过渡或删除识别出的圆角 新增时选定边并设置来源规定的半径；删除时核对工具识别的圆角集合，再检查连接轮廓。

核对时，用截面或测量核对圆角半径、边界及是否误改邻边。

保留影响流阻或传热的有意圆角；课堂尺寸仅作练习。

来源 SCDM_CFD_Intro_19.0_WS1.2_Workshop_Instructions_Creating_Mixing_Elbow · src-9433e7c63fa17786 · PDF p. 10 ｜ SCDM_CFD_Intro_19.0_WS2.1_Workshop_Instructions_Creating_Geometry · src-b7fcfd05d3e1d1ba · PDF p. 14 ｜ SCDM_CFD_Intro_19.0_WS3.1_Workshop_Instructions_Repairing_Geometry · src-3a9cf8f0429193fe · PDF p. 12

<a id="G11"></a>

## G11 · 分割实体后核对所得体和切割对象

**verified** · 19.0（文件标识） / 待核

需要把单一实体划分成不同区域 分别指定目标实体与切割平面或曲面，并在操作后检查新生成的实体。

核对时，确认分割面位置、预期体数及各体相互关系。

仅对预期存在实体边界的部位分割。

来源 SCDM_CFD_Intro_19.0_WS2.1_Workshop_Instructions_Creating_Geometry · src-b7fcfd05d3e1d1ba · PDF p. 23 ｜ Optional_Workshop_Module02_Office_Chair · src-958b4ad6fce2090d · slide 48

<a id="G12"></a>

## G12 · 以命名驱动尺寸验证几何参数

**verified** · 19.0（文件标识）

尺寸或角度要用于参数化扫描 在参考面对或尺寸标注上建立命名驱动尺寸，试改一次并检查几何响应，再恢复基准值。

核对时，复测实际长度或角度并确认预期几何部位随之更新。

示例的试改数值和参数名按当前模型替换。

来源 SCDM_CFD_Intro_19.0_WS5.1_Workshop_Instructions_Parameters · src-910c57fd1f7ff75c · PDF p. 9 ｜ SCDM_CFD_Intro_19.0_WS5.2_Workshop_Instructions_OPTIONAL_Valve · src-78e6233ee9cc8ebd · PDF p. 8

<a id="G13"></a>

## G13 · 在新文档检查录制脚本的重建与参数类型

**verified** · 19.0（文件标识）

几何脚本需要重建模型并读取驱动尺寸 在可丢弃的测试文档回放录制步骤；读组数据时先确认组代表驱动尺寸并检查读取结果。

核对时，重建结果与预期拓扑一致，命名组能够返回期望的量。

避免将示例的清空动作作用在现有工作模型；组索引只对特定文件成立。

来源 SCDM_CFD_Intro_19.0_WS6.1_Workshop_Instructions_Recording_Script · src-568f0dc2df9afabe · PDF p. 12 ｜ SCDM_CFD_Intro_19.0_WS6.2_Workshop_Instructions_Core_API · src-10da57c44b3d3e7b · PDF p. 5

<a id="G14"></a>

## G14 · 把边界角色绑定到可查的命名选区

**verified** · 2021 R1 / 2019 R2 / 2019 R1

需要把上游模型中的进出口传递给流体求解器 在预期边界面创建有物理意义的选区，在下游点选名称验证高亮。

核对时，确认面集合与预期流道、位置和方向一致。

同名规则不能证明拓扑变化后仍选中同一边界。

来源 FLU_GSN_2021R1_EN_WS01.4_SCDM_NamedSelections_BOIs · src-349d07bc02c32977 · PDF p. 7 ｜ Mesh-Intro_19R2_WS1.1_CFD_Workshop_Instructions_ANSYS_WB_Meshing_Basics · src-6755132be8a0dbde · PDF p. 10 ｜ CFX_GetStart_2019R1_L02.2_ANSYS_Meshing_基础 · src-ca93b5983dc72028 · PDF p. 10 ｜ FLU_GSN_2021R1_EN_WS04.1_Heat_Sink · src-84e3684edf602cbe · PDF p. 4

关联阅读 [M01 · COMSOL 6.3 的选区首先要有正确的几何层级](geometry.md#M01)（命名角色与实体层级；两种软件各自实现。）

<a id="G15"></a>

## G15 · 删除小凹陷前检查面延伸结果

**verified** · 待核

计划简化零件表面的非功能性局部凹陷 只圈选拟删除的凹陷，预期依靠相邻面延伸填平。

核对时，操作后检查相邻曲面连续性及保留特征。

换热槽、密封槽等功能特征应有额外证据才可简化。

来源 Optional_Workshop_Module03_Simplifications_Repairs · src-d3bd5f4cc77e00a4 · slide 19

<a id="F05"></a>

## F05 · 从可定义的边界选择截断位置

**verified** · 2019 R1 / 2021 R1

只建整个装置中的一部分。 先定位工程目标和测量范围，再选有边界数据的进出口位置。必要时将模型延伸至已知截面。

核对时，为每个截面说明有何数据可支持所选边界类型。

二维或轴对称简化另需几何与物理对称性证据。

来源 Fluent入门L01_CFD 概述 · src-856e10a8aafe89e4 · PDF p. 6 ｜ FLU_GSN_2021R1_EN_LE02.1_CFD_Overview · src-43dae986b9473a93 · PDF p. 6

<a id="M01"></a>

## M01 · COMSOL 6.3 的选区首先要有正确的几何层级

**verified** · 6.3

为材料、物理边界条件或点约束划定作用位置时 先从物理角色确定应选域、边界、边或点，然后从对应节点查看实际选区。

核对时，在设置列表和图形高亮中对照选区内容与目标部件。

二维和三维模型的边界对应不同的几何维数。

来源 COMSOL 6.3 - About Selecting Geometric Entities · COMSOL63-SELECT · #1223699 ｜ COMSOL Multiphysics Reference Manual · COMSOL63-REFERENCE-PDF · PDF p. 512 ｜ COMSOL 6.3 - About Selecting Geometric Entities · COMSOL63-SELECT · About Selecting Geometric Entities，开篇、Table 6-2 前

关联阅读 [G14 · 把边界角色绑定到可查的命名选区](geometry.md#G14)（命名角色与实体层级；两种软件各自实现。）

<a id="M02"></a>

## M02 · COMSOL 6.3 的重建会重新映射物理选区

**verified** · 6.3

修改几何对象后重建几何时 用有明确物理角色的命名选区承接下游特征，重建后核对它们与最终几何的对应关系。

核对时，分别核对施加材料和边界条件的实际域、面或点。

几何映射可能存在歧义，命名选区也需要重新核对。

来源 COMSOL Multiphysics Reference Manual · COMSOL63-REFERENCE-PDF · PDF p. 598 ｜ COMSOL 6.3 - Associative Geometry and Selections of Geometry Objects · COMSOL63-ASSOC · #636448

关联阅读 [P05 · 重建后用物理角色重新识别选区](geometry.md#P05)（重建后的选区映射。）

<a id="M03"></a>

## M03 · COMSOL 6.4 的重建会重新映射物理选区

**verified** · 6.4

修改几何对象后重建几何时 用有明确物理角色的命名选区承接下游特征，重建后核对它们与最终几何的对应关系。

核对时，分别核对施加材料和边界条件的实际域、面或点。

几何映射可能存在歧义，命名选区也需要重新核对。

来源 COMSOL Multiphysics Reference Manual · COMSOL64-REFERENCE-PDF · PDF p. 618

<a id="M04"></a>

## M04 · COMSOL 6.0 选区区分输入与有效实体

**verified** · 6.0

物理特征已接收实体列表，但边界条件似乎没有生效时 按目标维度读取 selection.entities(dim)，与写入列表及活跃物理域的内外边界条件比对。

核对时，把有效集合为空、部分过滤、全部生效作为三个不同结果记录。

inputEntities() 可用于适用类型的输入查验；部分类型返回 null。

来源 COMSOL Multiphysics Programming Reference Manual · COMSOL60-PROGRAMMING · PDF p. 34

<a id="M05"></a>

## M05 · COMSOL 6.3 选区区分输入与有效实体

**verified** · 6.3

物理特征已接收实体列表，但边界条件似乎没有生效时 按目标维度读取 selection.entities(dim)，与写入列表及活跃物理域的内外边界条件比对。

核对时，把有效集合为空、部分过滤、全部生效作为三个不同结果记录。

inputEntities() 可用于适用类型的输入查验；部分类型返回 null。

来源 COMSOL Multiphysics Programming Reference Manual · COMSOL63-PROGRAMMING-PDF · PDF p. 35 ｜ COMSOL 6.3 - Selections · COMSOL63-API-SELECT · #5431382 ｜ COMSOL 6.3 - Selections · COMSOL63-API-SELECT · Selections / General Syntax，selection.entities(dim) 与 inputEntities()

关联阅读 [P05 · 重建后用物理角色重新识别选区](geometry.md#P05)（6.3 输入实体与实际有效实体。）

<a id="M06"></a>

## M06 · COMSOL 6.4 选区区分输入与有效实体

**verified** · 6.4

物理特征已接收实体列表，但边界条件似乎没有生效时 按目标维度读取 selection.entities(dim)，与写入列表及活跃物理域的内外边界条件比对。

核对时，把有效集合为空、部分过滤、全部生效作为三个不同结果记录。

inputEntities() 可用于适用类型的输入查验；部分类型返回 null。

来源 COMSOL Multiphysics Programming Reference Manual · COMSOL64-PROGRAMMING-PDF · PDF p. 35 ｜ COMSOL 6.4 - Selections · COMSOL64-API-SELECT · #5431382

关联阅读 [P05 · 重建后用物理角色重新识别选区](geometry.md#P05)（6.4 有效选区回读。）

<a id="P05"></a>

## P05 · 重建后用物理角色重新识别选区

**verified** · Paper2Simu 0.5.0

几何重建、布尔操作或 CAD 导入后，边界或域的编号变化 对入口、加热面和流固域逐一核验维度、实体数量和几何位置；按角色定义重绑，并回读有效实体。

核对时，用实际数目、几何测量和邻接确认目标。空集保留为待解决。

实体数目由几何及角色决定。单个示例的实体编号没有移植意义。

来源 selection-contract · src-ba9b2d68ec797c90 · lines 3-11 ｜ geometry-validation-results · src-4fd78e25cb6a1db5 · lines 19-26 ｜ cad-6.4 · src-3d47a868e093e9ae · lines 15-24 ｜ native-supervised-workflow · src-372b324b8313a104 · lines 16-20

关联阅读 [M02 · COMSOL 6.3 的重建会重新映射物理选区](geometry.md#M02)（重建后的选区映射。） ｜ [M05 · COMSOL 6.3 选区区分输入与有效实体](geometry.md#M05)（6.3 输入实体与实际有效实体。） ｜ [M06 · COMSOL 6.4 选区区分输入与有效实体](geometry.md#M06)（6.4 有效选区回读。） ｜ [M07 · COMSOL 6.3 的压力点约束用于确定压力水平](solver.md#M07)（压力基准点需取得实际点选区。）

<a id="P06"></a>

## P06 · 从论文剖面确定尺寸端点和材料占位

**verified** · Paper2Simu 0.5.0

同一标注可能指通道、槽口或总包络 从总视图追踪切面，在剖面标出两个物理端点，再检查流体和固体的宽度、周期或总尺寸是否闭合。

核对时，记下源图、尺寸角色和闭合关系。存在两种解释时保留两案。

示意图的比例不能替代缺失尺寸。

来源 geometry-workflow · src-4a708e8914bdb734 · lines 5-12 ｜ geometry-workflow · src-4a708e8914bdb734 · lines 5-11
