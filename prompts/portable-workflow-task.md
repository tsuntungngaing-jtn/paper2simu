# 原生工作流移植任務卡

適用於已獲授權的工程打包、恢復、重開取數或參數重放。沿用 canonical SKILL 的執行邊界；本卡不自行授權 solve。論文復刻另外加載現有 paper-reproduction-task/input-reconstruction/conditional-calibration。

## 填寫一次
- task_id / workflow_id / contract_revision：
- 目的：archive / restore / zero_iteration_readback / fresh_replay / cross_solver_comparison
- 來源 solver/build/platform/provider；目標 solver/build/platform/provider：
- 既有 input ledger / QoI contract / execution spec / acceptance spec / journal 的路徑及 hash：
- 授權的階段、目標 session、最大求解數/時間/重試數：
- 原生工程、外部資產、受控輸出目錄：
- 基準設計點與一個幾何擾動點；擾動合理性與預期響應：
- 恢復、讀回、重放、科學比較各自判據；未設判據時僅報告觀測：

## 執行
1. 讀取 [合同規格](../docs/portable-workflow-contract.md)，核對每個階段的能力和現有 job。保存資產 hashes、版本和相對路徑。從[範本](../examples/portable-workflow-template.json)建立任務內的工作流記錄；用合同中的離線指令檢查聲明與資產。規劃只產生計畫證據。
2. 保留原生工程及 recipe。在獨立目錄恢復，不覆蓋唯一來源。確認外部資料/UDF/CAD 可用；記錄 restore 結果。
3. 有保存解時零迭代重新取數：鎖定 dataset/solution 和 QoI 算子，記錄有效選區與量綱。重新取數不需要擅自啟動 solve。
4. 已授權且資料足夠時從 recipe 重建基線及擾動點。幾何與 mesh 重新讀回；參數變動未生效時先修執行鏈，不能宣稱不敏感。
5. 需要 staged solve 才加載 [階段規範](../docs/staged-solve-contract.md)。每個真實提交落盤 operation/job/run ID；恢復先核對原 job。
6. 用事先凍結的判據判定每個檢查，保留失敗與不確定結果。比較不同 solver 時附離散化、物性和 QoI 綁定差異；結果接近本身不是物理真值證明。

## 交付表
| 檢查 | 狀態 | 判據版本 | 觀測/差異 | 原生工件與身份 | 限制 |
|---|---|---|---|---|---|
| archive_restore | NOT_RUN | | | | |
| zero_iteration_readback | NOT_RUN | | | | |
| fresh_parametric_replay | NOT_RUN | | | | |
| scientific_validation | NOT_RUN | | | | |

允許狀態：NOT_RUN、PASS、FAIL、BLOCKED、NOT_APPLICABLE。尚在執行的 job 另報其執行狀態，勿提前填 PASS。沒有判據則保留觀測並標 BLOCKED（無法判定），不把未知記成零。

## 原生界面交接（0.4.5）
- 依[原生監督流程](../docs/native-supervised-workflow.md)声明 setup/geometry/mesh。确认模型身份，在副本改参、读回、重建、另存重开；记录操作者、build、路径、预期/实际变化、原件和副本哈希及重开回执。无真实人工界面回执则 desktop_editability=NOT_RUN 或 BLOCKED；新求解独立记录。仅 Solver case 不代表几何可编辑。
- 交付表增加 desktop_editability 一行，使用 portable schema 对应 receipt。
