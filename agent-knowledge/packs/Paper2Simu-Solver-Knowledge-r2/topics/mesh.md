# 网格与近壁分辨率

经独立核对的核心原文标为 verified。candidate 供复核。每次应用保存当前版本及原生读回。

<a id="G16"></a>

## G16 · 批量选网格区域时核对标签匹配集合

**verified** · 2021 R1

过滤区名以同时操作多个区域 选择可持续标识的标签并先查看通配符匹配列表，确认参与操作的实际区。

核对时，核对匹配的区数与高亮对象，特别是自动全选匹配项时。

标签改善重建后的可追溯性；仍需回读。

来源 FLU_GSN_2021R1_EN_LE03_FM_Overview · src-5ad33be825f8843b · PDF p. 34

<a id="G17"></a>

## G17 · 先用尺寸预览和表面网格检查全局与局部设置

**candidate** · 2021 R1 / 2019 R2

体网格生成前已指定全局尺寸或边尺寸 先查看局部尺寸显示，再生成或预览表面网格，检查狭窄区并记录本次网格的最大偏斜。

核对时，保留表面网格预览、尺寸及质量统计。

示例页演示质量统计；最差单元的位置需另查该版本的原生诊断。 复核缺口：原页的图文示范尺寸预览、网格生成和读取最大偏斜数值；这些页未说明如何定位最大偏斜单元，位置需另取诊断依据。

来源 FLU_GSN_2021R1_EN_WS03_Mixer · src-e38aac3894a8f288 · PDF p. 6 ｜ Mesh-Intro_19R2_WS3.1_CFD_Workshop_Instructions_Global_Mesh_Controls · src-789f6092140693ff · PDF p. 14 ｜ Mesh-Intro_19R2_WS4.1_CFD_Workshop_Instructions_Local_Mesh_Controls · src-94774d70917b5f92 · PDF p. 15

<a id="G18"></a>

## G18 · 区分表面尺寸控制和分区体网格控制

**verified** · 2021 R1 / 待核

表面分辨率与内部体单元尺寸需要分别调节 在表面网格步骤设置面控制；在体网格步骤按区域调节可用的单元长度与增长参数。

核对时，分别查看表面网格和体网格剖面，确认控制生效的位置。

Fluent 2021 R1 水密流程的可用设置随填充方法变化；体尺寸可能是软目标。

来源 FLU_GSN_2021R1_EN_LE04_Regions_Vol_Mesh · src-40c34032980f1d8a · PDF p. 39 ｜ Fluent入门_L02_FM_概述 · src-c91606d1f843d8d0 · slide 35

<a id="G19"></a>

## G19 · 用鳍片厚度方向的单元数检查近距加密

**verified** · 2021 R1 / 2019 R2

散热片或薄板采用邻近尺寸函数 把近距控制作用到对应面标签，生成后截取薄壁剖面，数出厚度方向实际分层。

核对时，对影响固体温差的厚度分辨率另做加密比较。

Heat Sink 工作坊为运行练习降低了单元数；示例层数不作收敛判据。

来源 FLU_GSN_2021R1_EN_WS04.1_Heat_Sink · src-84e3684edf602cbe · PDF p. 7 ｜ Mesh-Intro_19R2_M04_Lecture_Slides_Local_Mesh_Controls · src-fb7cd688ab3b11cc · PDF p. 19

关联阅读 [M17 · Fluent 24.2 网格比较须注明正交质量算法](mesh.md#M17)（几何分辨率和单元质量是不同检查。）

<a id="G20"></a>

## G20 · 几何变化后使用可追踪的网格更新

**verified** · 2019 R1

Workbench 上游几何已修改 检查上游状态，再更新网格并检查与下游系统关联的网格单元状态。

核对时，确认新几何已进入网格，记录此次更新的范围。

单独生成新网格和更新已连接系统的依赖关系不同。

来源 CFX_GetStart_2019R1_L02.2_ANSYS_Meshing_基础 · src-ca93b5983dc72028 · PDF p. 9

<a id="G21"></a>

## G21 · 曲率与近距控制须结合最小尺寸核查

**verified** · 2019 R1 / 2019 R2

曲面尖转或窄缝仍显示过粗 检查曲率法向角和近距控制，并查看最小尺寸是否妨碍目标位置细化。

核对时，比较设置前后该处实际网格和几何拟合。

不要把课件中所用法向角推广到其他模型。

来源 CFX_GetStart_2019R1_L03.2_全局网格控制 · src-f0bf9bc357a2008a · PDF p. 6 ｜ Mesh-Intro_19R2_WS5.2_CFD_Workshop_Instructions_Auto_Ext_Aero · src-3b3629fd050fb9ae · PDF p. 17

<a id="G22"></a>

## G22 · 检查偏置边上的细网格方向

**verified** · 2019 R1 / 2019 R2

边界或端部需要不对称分布 设定边分布、偏置方向和增长方式，必要时反向，再预览边上的间距。

核对时，最密位置是否确实落在目标端；多条边逐条确认朝向。

偏置因子和相邻格增长率表征不同的比值。

来源 CFX_GetStart_2019R1_L04.2_局部网格控制 · src-18500dd62b0693fc · PDF p. 6 ｜ Mesh-Intro_19R2_WS5.1_CFD_Workshop_Instructions_Mixing_Tank · src-cbddd6352371a868 · PDF p. 16

<a id="G23"></a>

## G23 · 扫掠前检查源面、目标面及几何可扫掠性

**verified** · 2019 R1 / 2019 R2

拟在长通道或挤出实体上生成定向单元 检查可扫掠体识别结果，必要时手选源面和目标面；复杂体可先分成较简单的拓扑。

核对时，预览源面网格与扫掠方向；确认区域内实际单元类型。

旋转可扫掠体可能不被自动识别。

来源 CFX_GetStart_2019R1_L05.2_网格方法 · src-e02792da5ed08187 · PDF p. 6 ｜ Mesh-Intro_19R2_WS4.1_CFD_Workshop_Instructions_Local_Mesh_Controls · src-94774d70917b5f92 · PDF p. 18 ｜ Mesh-Intro_19R2_M02_Lecture_Slides_Meshing_Methods · src-32c6318be74245dd · PDF p. 20

<a id="G24"></a>

## G24 · 同时查看变形、细长单元和尺寸过渡

**candidate** · 2019 R1

用汇总质量数值评估 CFD 网格 在网格局部视图查变形、长宽比及相邻单元尺寸过渡，保留所用指标。

核对时，在局部视图核对最差单元，保留所用指标和位置。

这页只支持通用形状检查。近壁层的方向、可接受长宽比和物理分辨率需另查活动模型。 复核缺口：图文支持变形、细长程度和过渡平滑性；该页本身没有给出沿流向与近壁层可接受细长单元的条件或判据。

来源 CFX_GetStart_2019R1_L07_网格质量 · src-c8f5da5d61bae04a · PDF p. 4

关联阅读 [M17 · Fluent 24.2 网格比较须注明正交质量算法](mesh.md#M17)（区分形状评价指标和实际算法。）

<a id="G25"></a>

## G25 · 核对 MultiZone 自由区域的实际填充

**candidate** · 2019 R2

希望分区网格能处理非结构化区域 采用工作坊的 MultiZone 方案时，检查自由区域填充选项，再核对生成的单元族。

核对时，检查自由区域内实际产生的单元族。

工作坊显式选择四面体／金字塔。其他工况须核实适用性和该版本默认值。 复核缺口：此练习明确设 MultiZone 的 Free Mesh Type 为 Tetra/Pyramid；仅凭这页不能断言每次使用 MultiZone 均必须显式设定填充。

来源 Mesh-Intro_19R2_WS2.1_CFD_Workshop_Instructions_ANSYS_Meshing_Methods · src-b075081d52dbf53f · PDF p. 14

<a id="G26"></a>

## G26 · 用虚拟拓扑为网格分块建立参考边

**verified** · 2019 R2

汇流管侧面缺少所需的网格控制边 在相应位置创建虚拟面，使网格控制有明确的作用边。

核对时，查看新增虚拟实体的边界及其与目标网格区域的对应。

虚拟分面用于网格组织，实际物理边界应另行核对。

来源 Mesh-Intro_19R2_WS5.4_CFD_Workshop_Instructions_Manifold · src-091652f3101da963 · PDF p. 8

<a id="G27"></a>

## G27 · 按 Workbench 扩展版本回查多面体网格日志

**verified** · 待核

复查旧版 Poly Meshing for Fluent ACT 的网格执行 匹配 R17 或 R18 扩展兼容性；从项目文件识别命令记录与 transcript，提取实际质量和单元数。

核对时，核对 ACT 版本及 transcript 中生成结果。

特定旧扩展的文件及兼容性约束。

来源 WBPolyMeshingForFluent · src-d67879038726fe8d · PDF p. 33 ｜ WBPolyMeshingForFluent_ReadMe · src-59ed4bffbe07ab74 · PDF p. 1

<a id="G28"></a>

## G28 · 按实体连接关系检查网格显示

**verified** · 2019 R2

多体模型疑有意外连接或分离 切换为按体连接关系显示网格，必要时用线框辅助查看界面。

核对时，对照相邻体和应连续的边界，再检查网格接口。

图形显示用于诊断，不足以独立证明数值通量连续。

来源 Mesh-Intro_19R2_M01_Lecture_Slides_Core_Skills · src-5392e2ad482af6e6 · PDF p. 22

<a id="G29"></a>

## G29 · 区分面与体的网格尺寸上下限

**candidate** · 2019 R2

在 19R2 Workbench Meshing 中使用非 Adaptive 尺寸函数。 在该尺寸函数中分别辨认最小目标、最大面尺寸与体内部增长上限，再结合短边检查实际尺寸。

核对时，在表面和内部各取样，检查实际网格与定义相符。

CutCell 不支持原页所述的 Element Size 字段，其他方法按相应版本检查。 复核缺口：原页明确仅在非 Adaptive size function 时适用，并指出 CutCell 不支持其中的 Element Size；应将前者明确为检索和执行前提。

来源 Mesh-Intro_19R2_M03_Lecture_Slides_Global_Mesh_Controls · src-ca35c3b78baed425 · PDF p. 10

<a id="G30"></a>

## G30 · 记录网格连接容差及单元类型回退

**verified** · 2019 R2

面连接或四边形划分改变了预期拓扑 检查连接容差是否消除了应保留的窄面或短边；有回退警告时定位问题拓扑。

核对时，核实最终生成的是四边形还是三角形及相关区域。

具体回退行为取决于使用的网格方法。

来源 Mesh-Intro_19R2_M05_Lecture_Slides_Mesh_Quality_and_Advanced_Topics · src-6ac8c4084f88d0ab · PDF p. 30

<a id="G31"></a>

## G31 · 创建区域后以实际空间位置校核类型

**verified** · 待核

水密网格流程根据盖面和 CAD 拓扑自动生成各区 核对是否有空腔、流区、固区或旋转区；逐区用高亮和邻接关系辨认，再决定保留、改名或排除。

核对时，记录各区名称、类型和可见几何，检查需要连通的流区。

纯流体、阀体或搅拌槽的默认项和区域名称仅适用于各自算例。

来源 WS_aero-workshop · src-be4fa1145545bd09 · slide 7 ｜ WS_ball-valve · src-e515d4e4d966dd92 · slide 12 ｜ WS_mixing-tank · src-82fd8be48dfe8af3 · slide 9 ｜ WS_mixing-tank · src-82fd8be48dfe8af3 · slide 12

<a id="G32"></a>

## G32 · 对局部表面细节与空间加密区分别指定作用范围

**verified** · 待核

孔面附近和指定体积内要求不同网格密度 用面标签设置局部面尺寸，再以区域选择影响体以控制指定体积内的网格。

核对时，核对两个控制各自选中的标签、区域及生成网格。

BOI 表示网格控制区域，其实体不自动代表物理材料。

来源 WS_mixer-workshop · src-bd10ab4ad07d7fc3 · slide 5

<a id="G33"></a>

## G33 · 把按名称分配的边界类型当作初值复查

**verified** · 待核

从带 inlet、outlet 等名称的上游几何创建网格边界 在 Update Boundaries 检查每个区域的初始类型，必要时分组修正并回读。

核对时，核对下游求解器里的边界名、类型与物理角色。

命名匹配可能产生与目标问题不一致的初值。

来源 Fluent入门_L03_体网格划分 · src-6e26acb18a89e91c · slide 20

<a id="F06"></a>

## F06 · 导入网格后核对物理尺寸

**verified** · 2019 R1 / 待核

从外部工具导入网格或换用几何单位。 读取域包围尺寸，与源几何的同一已知尺寸比较，证实单位不符后再缩放。

核对时，重复读取尺度后运行网格检查并保存单位。

显示单位与几何缩放分别记录；比例不可从外观推定。

来源 Fluent入门L04_计算域设置 · src-1259f7a9ca3fe904 · PDF p. 4 ｜ Fluent_NACA机翼算例_课件 · src-ddc6cde233c479de · PDF p. 12

<a id="F23"></a>

## F23 · 将近壁策略与实际网格联合检查

**verified** · 2021 R1 / 待核

壁面热流、摩擦等是目标量。 按所选近壁处理设计首层和棱柱层；求解后在目标壁面查看 y+ 的空间分布，再决定需细化的位置。

核对时，同时核对模型、首层尺寸、目标壁面分布及 QoI 网格敏感性。

解析黏性底层和壁面函数有不同适用条件。讲义的 y+ 目标不可当作所有模型的统一门槛。

来源 FLU_GSN_2021R1_EN_LE11_Turbulence · src-50c9d528fbd380b0 · PDF p. 12 ｜ FLU_GSN_2021R1_EN_LE11_Turbulence · src-50c9d528fbd380b0 · PDF p. 14 ｜ FLU_GSN_2021R1_EN_WS11_Backward_Step · src-a418724f2c74aace · PDF p. 28 ｜ Fluent-湍流模拟 · src-0c5f093967aa524a · PDF p. 20

关联阅读 [M18 · Fluent 24.2 近壁处理应与网格分辨率配套](mesh.md#M18)（按模型与近壁分辨率联合检查。）

<a id="M16"></a>

## M16 · Fluent 23.1 表面网格修复阈值的语义

**verified** · 2023 R1 (23.1)

在 Watertight Geometry 表面划分流程设置 Quality Improve Skewness Limit 时 记录设定的偏斜度阈值并定位超限三角面，执行质量改进后重新计算质量。

核对时，前后比较超限面和几何特征保真度。

该控件决定哪些三角面会被尝试修复，不能单凭设置值判定网格达标。

来源 fluent_gui_help · src-b811ca1cdc5700b7 · #enablecleancad_generatethesurfacemeshwtm_smqualityimprovelimit ｜ fluent_gui_help · src-b811ca1cdc5700b7 · lines 225-228

<a id="M17"></a>

## M17 · Fluent 24.2 网格比较须注明正交质量算法

**verified** · 2024 R2 (24.2)

比较不同单元类型、网格版本的最小正交质量时 记录单元类型与默认或增强算法。默认四面体、棱柱和金字塔取正交性与一减偏斜度的较小值；六面体和多面体使用正交性。

核对时，以相同算法复算，定位最差单元对应区域。

启用增强算法后指标定义改变。

来源 Ansys Fluent User’s Guide · FLUENT242-USER-PDF · PDF p. 1147

关联阅读 [G24 · 同时查看变形、细长单元和尺寸过渡](mesh.md#G24)（区分形状评价指标和实际算法。） ｜ [G19 · 用鳍片厚度方向的单元数检查近距加密](mesh.md#G19)（几何分辨率和单元质量是不同检查。）

<a id="M18"></a>

## M18 · Fluent 24.2 近壁处理应与网格分辨率配套

**verified** · 2024 R2 (24.2)

流动主要由近壁区域或小间隙控制时 成对审查湍流模型的近壁处理和壁面首层分辨率；记录实际近壁网格是否能解析目标区域。

核对时，把壁面分辨率与采用的增强壁面处理及其适用情形逐项对照。

该节介绍 ε 方程的增强处理；不同湍流闭合的要求需分别核对。

来源 Ansys Fluent Theory Guide · FLUENT242-THEORY-PDF · PDF p. 191

关联阅读 [F23 · 将近壁策略与实际网格联合检查](mesh.md#F23)（按模型与近壁分辨率联合检查。）

<a id="P13"></a>

## P13 · 两套网格只支持有条件的误差推断

**verified** · Paper2Simu 0.5.0

只有两级系统细化结果，需要描述网格敏感性 报告两级尺寸、同定义响应量和差值。估算两网格 GCI 前需有适用的外部阶数、渐近区间依据以及迭代／提取噪声评估。

核对时，当响应接近零时给带单位绝对差，并说明噪声尺度。

两点不能同时推定观测阶数或证明渐近收敛。

来源 grid-refinement-reporting · src-cc324b677242b28b · lines 5-14 ｜ grid-refinement-reporting · src-cc324b677242b28b · lines 7-14

<a id="P14"></a>

## P14 · 跨网格对照先对齐物理坐标和场

**verified** · Paper2Simu 0.5.0

比较两份独立网格上的标量场 核对几何、边界条件、场单位与节点映射；在两网格共同覆盖的区域比较，并单独报告覆盖范围。

核对时，记录空间重叠情况，附有单位的误差和未覆盖部分。

所引项目实现只支持特定线性三角形节点标量，比较不能证明网格独立。

来源 mesh-native-diagnostics · src-6de1c335a8043248 · lines 7-13 ｜ mesh-native-diagnostics · src-6de1c335a8043248 · lines 51-55

<a id="X01"></a>

## X01 · 复用网格文件时登记导出产物

**verified** · 2021 R1

需要把网格从生成会话交给求解会话。 完成体网格后显式写出网格文件，记录交付的是网格及其格式。

核对时，重新读取时核实文件、网格和区域身份。

这里只提取通用文件交接步骤。

来源 FLU_GSN_2021R1_EN_WS04.2_Arcjet · src-4a5188785a14bf92 · PDF p. 14

<a id="X02"></a>

## X02 · 建立网格设置前确认长度单位

**candidate** · 2019 R2

几何或网格工程采用不同的显示或输入单位。 在设置尺寸前查看工程使用的单位系统，确认它与本算例预期一致。

核对时，后续可用换算后的已知尺寸作物理尺度核查，此为额外检查。

讲义中的 mm 是该例选择，目标项目按原始单位建账。 复核缺口：原页仅指示选择 Metric (mm...) 单位；书中此页未给出原几何量换算、读回与已知尺寸比较等额外步骤。

来源 Mesh-Intro_19R2_WS5.3_CFD_Workshop_Instructions_2d_Combustion_Chamber · src-a3f73293a4d8cf4f · PDF p. 5
