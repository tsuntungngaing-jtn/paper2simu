# 作业截止与停止契约
## v0.4.0 运行边界

在 COMSOL 调用 `comsol_execution_capabilities` 读取运行时停止能力。对要求硬截止的作业，在 `comsol_run_case`、`study_solve` 或 `study_solve_async` 中传 `require_hard_deadline=true`。共享 JVM 连接器返回 `HARD_DEADLINE_UNSUPPORTED`，不消耗提交额度，也不启动作业。取消仅覆盖未开始的队列任务。Fluent 的停止和截止能力须按安装的官方 provider 及实际运行模式单独验证。

下文用于明确作业约束和评估未来支持隔离运行的 provider。沿用任务对终止操作的实际授权。

## 必须先定义
deadline 覆盖排队、网格、初始化、求解、保存的哪些阶段；计时起点是提交还是 native 启动；是否包括保存时间；到点要求停止计算还是完成数据落盘。
从实际任务卡继承约束，包括预算数值和覆盖阶段。任务授权决定能否改用软预算。
记录 started_at、deadline_at、stop_requested_at、native_stopped_at、checkpoint_completed_at，使用可靠的时长计量；监督进程重启/机器睡眠后的截止状态也要恢复，不能重新计满额预算。

## 停止能力等级
queued_cancel：仅未开始任务。
cooperative_stop：运行中的原生协作停止，可能等到迭代/时间步安全点。
isolated_deadline_enforcement：独立监督者控制已隔离且归属明确的作业，具备经验证的升级终止策略。
这几类不可互相替代。发出停止请求不等于停止已经完成。

## 设计优先级
正常工作先使用受支持的原生停止与预先检查点。硬预算需求下，评估通过可信 MCP 内部启动隔离 native worker，由独立监督进程管理；监督者不持有求解长锁。
COMSOL batch stop/cancel、Fluent 受支持 interrupt/checkpoint 都需验证真实启动模式与响应条件；不要为“独立”直接并发调用同一非线程安全客户端。

官方参考：[COMSOL Windows batch 命令](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_running.38.31.html)、[Fluent 迭代边界 checkpoint](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_checkpointing.html)、[PyFluent 连接与退出 API](https://fluent.docs.pyansys.com/version/stable/api/connectivity/connectivity_contents.html)。
若需要升级终止，必须有已授权策略，且进程树/调度作业归属可验证，包括 PID 创建时间和子进程；绝不按进程名全局杀 COMSOL/Fluent/MPI。共享服务不能为一个 job 全局清除。无法隔离则不声明支持此等级。
强制结束可能丢失未保存数据；不能承诺硬截止同时保留活会话。普通桌面系统的故障边界需写明，不宣传覆盖主机失效的绝对保证。未达到所需截止语义时阻塞该求解，继续独立工作。

## 测试
先用 mock/受控测试 worker 验证长调用阻塞、命令队列占用、控制器退出、监督者重启、PID 复用及误伤防护。故障注入不得直接用于真实生产任务。
真实软件仅在已有许可与授权范围验证最小案例；区分“正常迭代停止实测通过”和“卡死条件有界终止经过验证”。模拟通过不能证明商业软件集成通过。
到点已发请求但仍在计算记 deadline_missed，不假记 cancelled。检查点必须重开读取目标解/数据集才算恢复验证。

## v0.6.1 clock enforcement

See [runtime reliability](runtime-reliability-v0.6.1.md). With local clock enforcement, queue submissions must carry the current `task_case_id`. A hard-required case is blocked on this shared JVM regardless of the caller's individual flag. A persistent clock can latch EXIT independently of Codex but does not stop active native jobs; report native stop as unverified. The single-solve cap is a task-level limit pending verified native enforcement.
