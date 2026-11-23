# COMSOL 可见运行与原生证据
v0.4.0 的 `comsol_open_desktop` 区分进程启动与显示身份。桌面连接和当前模型由操作者确认，连接器返回 `not_checked`。原生日志、曲线和恢复能力仍需实际版本和会话证据。

分别记录 backend_connected、desktop_process_started、desktop_connected、displayed_model_verified、native_monitor_available。绑定 endpoint/session_generation/model_tag/job_id/study/solution/dataset。客户端启动不代表已导入目标模型；没有屏幕观测能力时显示状态为 not_checked，不伪造截图或宣称实时可见。
[服务器连接及导入](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_running.38.20.html)

在实际版本验证 study.setGenConv(true) 等能力，使用发现的 study tag。完整历史保存、图生成、图归档分别验证。ModelUtil.showProgress 的返回值用于能力判断；文件输出在客户端文件系统，必须记录真实位置，避免把原生输出写入 stdio MCP 的 stdout。showPlots 需要相应图形能力，不是弹窗保证。
[Study API](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_api_general.47.60.html)
[历史 API](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_api_solver.51.59.html)
[ModelUtil](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_api_general.47.15.html)

阶段事件、原始求解日志、日志解析曲线、原生截图是四类不同证据。原始日志保留完整文件、身份、起止时间、哈希、日志级别和缺口；派生曲线注明解析器与列含义。
COMSOL 非线性、线性、分离式与瞬态图含义不同；瞬态可能显示时间步长倒数，不是残差。保存 MPH 不保证保留收敛图；官方要求 Copy Convergence Data to Model。自动化对应方式只有验证后才能声明支持，否则保留日志并明确图未归档。表格 NaN 可能是收敛循环分隔，不能一律判失败。
[Convergence Plots](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_solver.36.112.html)

保持单一原生求解执行者；同步 solve 阻塞时不要另开线程绕过锁访问 JVM。异步观察可读取独立作业元数据/日志。处理日志轮转和截断；定位实际运行账户的日志目录，不硬编码桌面用户路径。
[Log Window](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_solver.36.113.html)

分开记录 job 完成、原生正常终止、数值验收、论文复刻验收。取消能力按真实工具提供；不因教学可视化而绕过既有 MCP/权限边界。不用合成曲线补齐缺失记录。
