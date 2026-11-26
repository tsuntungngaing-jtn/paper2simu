# 检索、重试与结果写回

主协调器选取各任务都能访问的本机私有 SQLite 路径，后续会话沿用同一路径。每台主机使用自己的数据库。以下命令从修订版根目录运行。

1. 首次故障及重试前运行 `python scripts/recovery_memory.py --db <经验库路径> lookup "故障现象"`。默认读取仓库内 `agent-knowledge/packs/Paper2Simu-Solver-Knowledge-r2/rules.jsonl`。如显式指定其他经过审查的版本，使用 `--cards <r2/rules.jsonl>`，检查 cards_loaded，必要时用同义词或案例编号补查。核对历史中的版本、上下文及反例。
2. 决定确有必要尝试后，由协调器运行 `python scripts/recovery_memory.py --db <经验库路径> reserve --case <稳定案例ID> --build <求解器构建> --revision <模型内容哈希> --action <规范化修复ID> --symptom "现象"`。有能改变诊断的新证据才附加 `--evidence <证据内容哈希>`。禁止使用时间戳、改写描述或流水号制造新尝试。同一键仅首次返回 NEW；NEW 仍须满足原任务授权、会话和作业检查。HOLD 时查原作业及记录，保留回访条件。
3. 执行器交回原生读回与作业身份，记录员提出记录，由协调器执行 `python scripts/recovery_memory.py --db <经验库路径> finish <预约ID> failed "观察、作业ID和证据路径"`。另外可用 observed 或 inconclusive。中断后遗留 reserved 时先核实原作业；已确认没有运行或结果不可判时如实记录。写入失败时保留证据并恢复写入。
4. 历史结果用于提示和排除重复尝试。把经验提升为通用知识卡须走已有独立审查。跟进时长、提交上限和切换论文条件沿用单次任务 prompt。

## v0.6.0 经验库安全约束

使用每台仿真机私有的 SQLite 路径，例如 `runtime/recovery-memory.sqlite3` 或仓库外的持久化目录；不要把 `references/recovery-history.json` 用作 `--db`，它是只读种子。数据库、WAL/SHM 和任务日志不得上传。`revision` 及可选的 `evidence` 使用真实 SHA-256。协调器是唯一负责预约和写回的角色；原子事务避免并发重复预约和冲突终态。查询及 NEW/HOLD 只是诊断信息，不能绕过 v0.5.2 的原生读回、权限、作业身份、预算及独立准入。

示例：`python scripts/recovery_memory.py --db runtime/recovery-memory.sqlite3 lookup "压力点选区为空"`。历史点编号不可跨模型沿用。
