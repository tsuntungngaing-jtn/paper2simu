# 可移植工作流合同

使用 [JSON Schema](../schemas/portable-workflow.schema.json) 與[範本](../examples/portable-workflow-template.json) 記錄工作流。離線檢查器查核聲明一致性及選填的檔案雜湊。原生階段的執行和獨立核驗沿用任務已設定的 MCP provider。

## 單一真相來源
workflow 只引用既有 task/inputs/QoI/journal 的版本及 hash，不新建互相矛盾的 ledger。共同層：物理模型、尺寸及來源、域/邊界角色、材料狀態範圍、工況、QoI 公式和單位、預算及驗收。原生層：solver/build/module/provider、幾何/網格/求解/取數配方和產物。

每次結果綁定 workflow_revision、input_revision、geometry_id、mesh_id、solution_id、dataset_id、scorer_version、run_id。任何相關輸入改變使依賴檢查過期；原生變更後未重建的 mesh 或未更新的解不能進入新模型結果。

## 原生配方的最低字段
- recipe_id、solver、build、OS、required_modules、provider_namespace、capability_evidence。
- 每階段：stage_id、depends_on、implementation、versioned_entrypoint、inputs、expected_outputs、readback_checks、budget、checkpoint、retry_policy。
- 外部資產：relative_path、sha256、purpose、required、redistribution_status。腳本/資料/可編譯 UDF 與編譯環境分開記錄；二進制不保證跨平台可用。
- 規劃、離線檢查與原生執行的 evidence_kind 分開。沒有 provider 原生觀測的 capability 不可標 VERIFIED。

## 語義選區
role 與 native selection 不是同一欄位。每次重建保存 native IDs/維度/count、幾何量、bbox/質心、法向（適用時）、鄰接域、連通性、選取規則和容差。許多合法變形會改變面積，應以參數推導的預期簽名比較，不強求與基線面積相等。
角色不存在、多義、錯維度或相鄰材料不符時，阻塞依賴賦值和求解。ID 重排可以接受，前提是幾何語義已驗證；名稱相同不能替代驗證。

## 網格
記錄實際 mesher，不把 Workbench Meshing 與 Fluent Meshing 視為同一配方。尺寸場、邊分段、bias、方法、生成順序、薄隙解析和品質都與幾何版本關聯。網格族比較固定物理設定與 QoI 算子。逐個 QoI 依[網格加密報告指南](grid-refinement-reporting.md)區分敏感性、條件式兩網格 GCI 與多網格方法。

## 四種獨立結論
1. archive_restore：原生工程與必要外部依賴在目標位置可恢復。
2. zero_iteration_readback：重開已保存解並重取 QoI，一次 solve 都未新增；只驗保存/提取一致性。
3. fresh_parametric_replay：按 recipe 重建並求解已授權設計點，觀測來源是新 run。
4. scientific_validation：依指定參考、誤差/不確定度與適用域評估；跨 solver 接近不等於實驗驗證，校準資料不等於留出。

PASS 必須帶判據、觀測、原生工件位置及 identity。缺能力為 BLOCKED；未嘗試為 NOT_RUN；實際操作出錯為 FAIL。NOT_APPLICABLE 需理由。文件存在、JSON schema 通過、腳本 exit 0 都不能單獨證明原生成功。

## 離線檢查

從完整 skill 包的根目錄執行：

```bash
python scripts/check_portable_workflow.py examples/portable-workflow-template.json
python scripts/check_portable_workflow.py /path/to/workflow.json --bundle-root /path/to/restored-project
```

- `PLAN_TEMPLATE` 保留四項 `NOT_RUN`。填寫 `WORKFLOW_RECORD` 時，設定工作流 ID、合同版本與任務引用。引用以 ID 和 SHA-256 指向既有文件或記錄，QoI 依現有合同。
- 分別記錄各求解器配方及階段。依賴階段排在使用者之前，同一配方中的階段 ID 唯一。能力證據缺失時，在任務記錄標明所影響階段。將細節、語義選區和有效讀回存入引用的原生配方或工件。
- 將各設計點的有效輸入、幾何、網格、解和資料集 ID 寫入 `states`。證據連到自己的 state、recipe、run、operation 和 artifact。保存解讀回記錄來源 run 和 `new_solves=0`。新重放記錄實際新增求解數，保留原 run ID 供比對。
- `contract_status` 是結構與聲明一致性。傳入 `--bundle-root` 才執行 `bundle_check`，核對必要資產、讀取範圍與檔案雜湊。選用資產可標 `MISSING`；若影響本階段，應列為必要資產。檢查靜態目錄副本。四項原生狀態原樣列為 `declared_checks`，離線結果的 `native_evidence_verification` 保持 `NOT_RUN`。求解前仍依既有 journal 核對未知提交，依各任務判據審查收斂、獨立留出和科學結論。

## 交付與發布
公開 skill 交付通用 md/json/py 規格、測試及脫敏示例；私有工作流交付原生 .mph/.wbpz/case/data、CAD、UDF、物性與日誌。完整工程是否包含外部資產應實測，不從副檔名推論。相對路徑仍需安全解析，拒絕越界及符號鏈接/junction 逃逸。不要為包入求解結果而放寬現有 public release allowlist。

官方參考（2026-11-21 檢視）：[COMSOL Named Selections](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_api_geom.48.032.html)、[PyFluent meshing workflows](https://fluent.docs.pyansys.com/version/stable/api/meshing/meshing_workflow.html)。實際設定仍以安裝版本 API 與 provider schema 為準；官方原生 API 存在不等於 MCP 已暴露。
