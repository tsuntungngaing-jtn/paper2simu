# 局部阻塞与持续推进
适用于 COMSOL/Fluent 论文复刻。状态必须基于证据，不根据模型文件存在推定已能求解。

## 两条独立进度
模型：inputs_partial → branch_specified → model_assembled → settings_verified → solve_ready。
作业：not_submitted → queued → running → terminal；terminal 细分 native_completed/failed/cancelled/deadline_terminated。状态未知用 unknown，不直接重提。
验收另外记录 native、conservation、discretization、paper_comparison，各自 PASS/FAIL/BLOCKED/NOT_RUN；模型状态不是验收。
已有项目如有状态机，建立映射并补字段，不创建相互矛盾的第二状态源。

## 阻塞条目
每项包含 task_id、观察时间、证据位置、类型、blocked_nodes、可继续节点、最小解除条件、last_attempt、next_discriminating_action。
类型至少区分 input_missing、physics_unresolved、model_incomplete、capability_missing、deployment_mismatch、transport_error、native_solver_failure、comparison_ambiguous。
无原生失败证据不使用 native_solver_failure。求解尚未提交时不得称“求解恢复”。

## 推进规则
只阻塞依赖它的节点。硬截止能力未验只阻塞相关求解，不阻塞阅读、条件明确的模型组装和静态审模。
当模型参数缺失且实际软件要求数值才能构建，标明该分支不能执行；仍可形成参数化规格，但不能将模板冒充可运行模型。
一次行动应产生模型有效节点、消除一个决定性未知、完成一项检验或验证一种控制能力。新文档可以是有效成果，但反复重复说明不能算模型进展。
无新证据时不重复相同失败操作。停下前检查依赖图中是否还有获授权且可执行节点；若有继续做。没有可执行节点则报告具体最小解除条件，不空轮询。
检查点保存输入/模型/设置哈希、证据版本、已完成节点、未决项、下一步、job/solution 身份。恢复时先验证已有成果，禁止无依据重做全部步骤或重复提交。

## 示例
干湿换热模型连接正常，研究为空且干湿方程未启用。记录 model_incomplete 和 physics_unresolved。先闭合干湿分支、质量与焓基准及耦合，再判定 solve_ready。保留缺失几何和未确认的面积、流路及关联式为条件分支。
Fluent 生产作业尚未提交，而短时停止演练已单独完成。生产 job 为 not_submitted，按已有记录保留诊断 job。硬截止能力只影响正式长求解。对标误差以实际任务卡为准。

## 在既有交接记录中使用

在 `task-plan.json` 的可选 `work_nodes` 清单中填写节点 ID、动作和依赖。把阻塞、解除和完成事件写进原 trial journal。运行 `python scripts/research_resume.py refresh <task-output-directory>` 后，`resume.md` 会显示可推进节点、传递依赖和阻塞证据。原来只有阶段和 trial 的记录可直接继续使用。字段、示例和原作业未决时的提交限制见 [研究计划与交接](research-plan-and-handoff.md#track-independent-work-in-the-same-plan)。
