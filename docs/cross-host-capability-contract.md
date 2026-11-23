# 跨电脑运行能力契约
能力取 supported/unsupported/unknown。记录适用版本、模式、观测时间和证据。未知能力只限制依赖该能力的操作。

## v0.4.0 读取入口

在当前注册的 Paper2Simu COMSOL MCP 调用 `comsol_execution_capabilities`，或用 `comsol_queue_status` 查看运行时指纹。返回实际加载的解释器、模块路径、启动时计算的 `server/*.py` 内容哈希、版本、传输、操作系统、启动时间、运行实例和输出根目录。哈希覆盖 Python 运行时代码。运营者可对脱敏后的记录独立补充安装包、Skill、供应商依赖和案例哈希。 `comsol_doctor` 报告可见依赖和安装路径。实际求解器 build、许可证和模型相关能力从原生环境补证。

COMSOL 的元数据轮询和排队取消是连接器实现的能力。读模型、建模、求解、有效设置、原生日志和目标解重开仍需该会话证据。运行中停止、硬截止和 Desktop 显示身份自动验证在此连接器标为 unsupported。Fluent 从实际官方 provider 的工具清单和原生日志填表。

## 脱敏运行指纹
skill 路径/版本/内容哈希；runtime commit/源码或包哈希；实际启动解释器及模块路径；provider 名称/版本/进程启动时间；MCP transport/服务实例；COMSOL/Fluent build 和模块；MPh/JPype/PyFluent 版本；OS、MPI 实现/进程数、资源限额；输出路径写入及恢复可读性；代理对目标回环地址的有效规则；运行身份类别。
不得导出 token、完整环境变量或许可证密钥。文档、安装包和内存中运行进程可能是三个版本，分别取证。共享 SKILL 文件不意味着共享后端能力。

## 能力维度
read_model、build_model、verify_effective_settings、solve、poll_metadata、native_log、queued_cancel、running_stop、checkpoint_reopen、desktop_identity、deadline_enforcement。
每项关联 provider/solver/session/run_mode。第二个 chat 或第二个 MCP 请求不是独立停止通道的证明。停止通道必须不依赖被长调用占用的锁/执行队列。

## 两机最小对照
1. 先静态比较指纹及已落盘日志，不启动新 solver。
2. 在已有授权下，用同一小案例、相同物理、相同进程数及输入哈希进行 build-only、短求解、保存复开和停止测试。
3. 对差异一次改变一项，例如 MPI；不要同时换版本、核数和模型然后宣布唯一原因。
4. 记录预期、实际、原始日志、身份、通过范围。代理响应、gRPC 就绪、native 求解与论文对标分开。
没有两机原始证据时，只给差异假设和最小检验，不宣布环境根因。

## 部署验收
升级后核对 live runtime 指纹，而非只看磁盘 SKILL 版本；按已有授权滚动切换并保留回滚。共享运行中的会话不可为升级直接中断。
COMSOL 与 Fluent 保留独立 provider/环境；统一的是科学流程与能力描述，不强迫它们共用相同 API 或停止策略。
