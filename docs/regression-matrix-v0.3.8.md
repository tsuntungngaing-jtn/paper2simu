# 0.3.8 回歸矩陣

離線 fixture 證明軟體判定邏輯。原生行為與實機反例依其配方逐項驗收，目前為 NOT_RUN。

| ID | 輸入/操作 | 預期可觀察行為 | 類別 |
|---|---|---|---|
| R01 | 完整 JSON、無 native run | schema 可過；native 狀態 NOT_RUN | 離線 |
| R02 | restore 缺 required 物性/UDF | 精確列缺件；依賴階段 BLOCKED | 離線+原生 |
| R03 | ID 改變、角色簽名合格 | 接受新映射並保留新 IDs | 離線+原生 |
| R04 | 名稱保留但面積/鄰接錯 | 阻止相關邊界賦值/solve | 離線+原生 |
| R05 | 中段滿足、最終不收斂 | 轉段成功；final FAIL 或未完成 | 離線+原生 |
| R06 | 監控 NaN/缺失/超時 | 不自動轉段，保存 checkpoint/原因 | 離線 |
| R07 | 提交回執丟失後 resume | 原 job 核對前無第二提交 | 既有調度測試 |
| R08 | geometry 變而 solution 未變 | 過時證據拒絕評分 | 離線 |
| R09 | 兩網格無階數或漸近依據、三網格不適用 | 只報敏感性；符合 Roache 條件的兩網格估計另標 conditional GCI | 報告規則與既有 admission 測試 |
| R10 | 將 calibration run 換 claim_id | 不能視作獨立 holdout | 現有校準測試 |
| R11 | 路徑 ..、絕對路徑、symlink、Windows junction | 離線檢查拒絕越界和連結路徑 | 離線；Windows junction 實機待驗 |
| R12 | 純建模無論文參考 | 正常執行；無 reproduction PASS | 行為回歸 |
| R13 | 一條 solver 可用，另一不可用 | 已授權獨立工作繼續；缺能力分項標記 | 行為回歸 |
| R14 | 發布/安裝後讀新 prompt | 所有引用存在；版本一致；無私有工件 | 包裝 |
| R15 | CAND 3 mm 宣稱無 Wr/域證據 | derived 條件未滿，不能標 paper_reported | 案例 |
| R16 | 復刻時欲優化鎖定幾何 | 不進校準；另立 DISCOVERY 任務 | 行為回歸 |

新增的 `tests/test_portable_workflow.py` 覆蓋模板狀態、缺件、雜湊、舊模型 lineage、重放與讀回區別、預算和路徑檢查。選區檢查及轉段仍由實際 provider 執行。

原生最低驗收：每個聲稱支持的 solver/build/provider 組合，至少一個已定義基線、一個幾何擾動、新目錄恢復與保存解讀回；記錄實際預算。只有經授權才執行，不能以本矩陣作授權來源。版本更新後重新評估適用的兼容性測試。
