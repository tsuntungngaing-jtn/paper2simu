# 分階段求解：轉段不等於最終收斂

依據 Yang 等 2024，PDF pp.3–5（期刊 pp.700–702），Fig.2、算法3。原文在中間場初步穩定時轉段，完整耦合後再完成計算。本規格的 checkpoint、身份追蹤、恢復和失敗狀態是 Paper2Simu 工程擴展。

對需要 staged initialization/coupling 的任務，每段登記：stage_id、active_physics、entry_predicate、monitor definitions（原生表達式/選區/單位/採樣窗）、transition_predicate、native termination evidence、budget、checkpoint、on_failure。判據由具體模型提供，不硬編通用 residual 或 SOC 四段順序。

狀態：PLANNED → READY → SUBMITTED → RUNNING → TRANSITION_READY → COMPLETED；失敗支路 FAILED/TIMED_OUT/BLOCKED。SUBMISSION_UNKNOWN 表示回執不明，先核對原作業，不能直接重發。TRANSITION_READY 只准許已授權後續階段，並不賦予 scientific PASS。

先保存上一段可恢復 checkpoint，再按本次 provider 支持的調用轉段。缺監控、NaN、單位錯誤、未達最低採樣窗、超時均不能被當成通過。最終收斂判據另外評估；即使上一段正常轉換，最終失敗仍如實交付。

若原生 solver 在單一 job 內完成多段，記錄同一 job 的 stage events；不強制每段啟動新 session。若 provider 不支持所需監控/切換，輸出 BLOCKED_CAPABILITY 的原因，保留可執行獨立階段。恢復時對照 stage、checkpoint hash、有效模型與原 job，防止回到錯誤物理配置。
