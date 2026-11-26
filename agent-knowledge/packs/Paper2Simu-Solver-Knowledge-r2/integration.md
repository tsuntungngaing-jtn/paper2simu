# Paper2Simu 接入

解压后让 Paper2Simu agent 读取本目录的 README.md。按 routes.json 的角色或问题选一个 topics 文件。机器读取对应 rules.jsonl 条目，通过 source-index.json 将 source_id 映射到版本、原始文件名/URL 和 SHA-256。本机原件依同一 ID 或哈希对应先前的输入清单。

采纳时在当前案例已有的输入或证据台账中登记包版本、卡 ID、source_id、原页/章节、工况、单位、实际构建及原生读回。candidate 需原文复核。跨版本的关联表示可对照的概念；执行时确认目标版本与界面。训练中的示例值按原案例保存，运行时长与提交安排由当前任务提供。

本目录符合 textbook2skill v0.3.0 的 knowledge-pack 文件约定，并采用 Paper2Simu v0.5.2 的外部知识包读取路径。文件层面的验证记录在 validation-report.md。使用它无需覆盖本机旧版 skill。
