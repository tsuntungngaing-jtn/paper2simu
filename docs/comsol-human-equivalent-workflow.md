# COMSOL 按人工逻辑建模
沿用现有 MCP、生命周期、求解控制和执行权限。对未执行的原生检查记录 NOT_RUN。
每步记录：物理意图、论文/手册出处、UI 位置、版本验证过的 API/工具、预期设置、实际读回、差异处理、证据路径。
状态为 planned/executed/verified/failed/blocked；不能读取的项标 not_checked。调用成功不等于设置有效。

| 步骤 | 人工操作位置/意图 | agent 检查与交付 |
|---|---|---|
| 0 环境 | 确认软件、模块及任务模式 | 版本/build、许可证能力、会话代次、model tag、job id；区分加载、建模、求解 |
| 1 原理图 | 解读论文图及尺寸 | 坐标、单位、固体/流体、入口出口、加热区；标页码/图号；假设单列 |
| 2 问题定义 | Model Wizard | 维度、物理接口、未知量、研究类型；区分给定 h 和共轭传热 |
| 3 几何 | Parameters、Geometry | 参数化原生特征；检查尺寸、域数、体积、布尔操作和连通性；保存几何 MPH |
| 4 选择 | Definitions/Selections | fluid、solid、inlet、outlet、heater 等命名选择；检查维度、非空、面积和重叠 |
| 5 材料 | Materials | 域覆盖、单位、来源、温度依赖及范围；读取真实属性和函数引用 |
| 6 物理 | Physics/Multiphysics | 域/边界、初值、热源、耦合引用、默认条件与覆盖优先级；不能只看节点存在 |
| 7 网格 | Mesh | 单元数、质量、关键部位分辨率，按需要设置边界层；网格独立性另验 |
| 8 研究 | Study/Solver Configurations | 研究实际启用的物理及耦合、初始解、参数/时间、容差和求解器 |
| 9 计算前 | 人工核对后 Compute | 保存设置快照与 MPH；build-only 在这里结束，不调用求解 |
| 10 计算 | Progress/Log/Convergence | 采集原生日志、真实终止状态及可获得的曲线，按独立监控文档执行 |
| 11 后处理 | Results/Derived Values | 明确 solution/dataset/时间/参数点/选择；核对守恒、敏感性和论文指标 |
| 12 复查交付 | 保存并重新打开 | MPH、设置台账、日志及图表可追溯；确认结果属于当前输入 |

步骤按模型依赖调整，不强制统一的菜单点击顺序。几何/材料/物理/研究变化后，旧解应标 stale，除非有证据证明变更不影响解。图中没有的尺寸不能由教程默认值冒充论文事实。

## 手册回放
从空模型按官方教程几何附录建立特征树，记录每步来源；导入几何序列或加载完整 MPH 分别标明，不能宣称全部从零完成。
指定 h 的 `heat_sink_3d` 用作简化案例。共轭传热采用单独案例，包含流体域、流动与传热接口及相应耦合。用目录里的 `conjugate_heat_sink` 作为持证主机的对照模型，或按官方教程从空白开始构建并保留操作记录。按 [CHT 耦合与能量检查](cht-coupling-energy-gates.md) 核对有效耦合、界面热流和能量余额。迁移到论文时依据论文重新决定参数与边界。
[官方 Heat Sink 教程](https://doc.comsol.com/6.4/doc/com.comsol.help.models.heat.heat_sink/heat_sink.html)

## API 与有效设置
使用实际安装版本的官方 API、Copy as Code/Record Method 验证属性；不要猜 setter。关键默认值需要读回，复制修改项可能漏掉默认值。6.4 的 Set All Displayed Settings 可辅助记录，但不能替代有效设置验证。
几何变化后重新求值选择，不跨模型沿用实体编号。Inspector 的 not_checked 项必须补检查器或明确未验，不能推定通过。
[编程工具](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/application_programming_guide.15.07.html)
[6.4 更新](https://www.comsol.com/release/6.4/application-builder)
[耦合参考](https://doc.comsol.com/6.4/doc/com.comsol.help.heat/heat_ug_multiphysics_features.12.12.html)
