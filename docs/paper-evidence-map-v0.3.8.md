# 文獻—規則—回歸映射

本表沿用迭代建議包的文獻定位，另以原文核對 Roache 的 GCI 方法及 Jing & He 的熱阻定義。頁碼為 PDF 頁碼，Roache 列期刊頁碼，Yang 同列兩種頁碼。文章提供方法依據，執行依任務授權。

| 本地文件 / 真實文獻 | 核對位置 | 支持的項目規則 | 不支持的推論 |
|---|---|---|---|
| main.pdf；Yang, Ru & Lin (2024), A fully automated tool for constructing multiphysics model and performing simulations of kW-scale solid oxide cell stacks；[DOI](https://doi.org/10.1016/j.ijhydene.2024.04.357) | pp.3–5 / 期刊700–702，Fig.2、算法1–3 | 幾何選區、網格配方、分段耦合接口；中間轉段與最終收斂分開 | SOC UDF/耦合順序普遍適用微通道；COMSOL 映射已實測 |
| Roache (1994), Perspective: A Method for Uniform Reporting of Grid Refinement Studies；[DOI](https://doi.org/10.1115/1.2910291) | pp.407–409 Eq.(10)、p.411 Eq.(19) | 分開記錄原始差值與附有階數、加密比、安全係數和漸近依據的條件式 GCI | 用兩點差值反推階數、以名義格式階數證實漸近區，或把 GCI 當實驗不確定度 |
| 078001_1.pdf；Celik 等 (2008), Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications；[DOI](https://doi.org/10.1115/1.2960953) | p.1 preliminaries、後續 RE/GCI 程序 | 求解迭代誤差和網格研究分開；GCI 適用性判斷 | 二網格差就是不確定度；文獻殘差建議可當所有任務硬門檻 |
| Eca-Hoekstra.pdf；Eça & Hoekstra (2014), A procedure for the estimation of the numerical uncertainty of CFD calculations based on grid refinement studies；[DOI](https://doi.org/10.1016/j.jcp.2014.01.006) | pp.1–2，方法範圍與 verification/validation 區分 | 系統網格加密、擬合品質與收斂階影響不確定度估計 | 任意三網格皆在漸近區；擬合成功即物理驗證成功 |
| Brynjarsdottir-OHagan.pdf；Brynjarsdóttir & O’Hagan (2014), Learning about physical parameters: The importance of model discrepancy | p.1 摘要、p.5 物理/調整參數、pp.16–17 混淆 | 擬合參數不是作者真值；模型偏差與輸入不確定度分賬 | 為過線任加假熱源；所有任務必做貝葉斯校準 |
| Raue-identifiability.pdf；Raue 等 (2009), Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood；[DOI](https://doi.org/10.1093/bioinformatics/btp358) | p.2 摘要、p.3 問題與似然模型 | 需要推斷參數時，可選 profile likelihood；說明誤差模型和可辨識性 | 將生物 ODE 示範直接當 CFD 原生驗證；15% 容差等於統計方差 |
| Oberkampf-Trucano.pdf；實為 Aeschliman & Oberkampf (1997), Experimental Methodology for Computational Fluid Dynamics Code Validation，SAND95-1189 | 封面核對作者、題名與年份 | 來源身份須讀原件；驗證文獻分類須準確 | 將檔名作作者/題名引用。本次僅用於身份糾錯，不宣稱完成該報告方法審查 |
| CAND-1114-005.pdf；Jing & He (2018), Thermal Characteristics of Staggered Double-Layer Microchannel Heat Sink；[DOI](https://doi.org/10.3390/e20070537) | pp.3–4 Fig.1、Eq.(4)–(5)、p.7 Fig.5 | 複合域、重複單元、top plate 與 Tmax 位置的語義核對；有條件寬度推導 | 3 mm 為所有工況原文值；歷史 2 mm 模型已證實錯誤 |
| P017.pdf；Kumari 等 (2022), A Numerical Investigation on Hydrothermal Performance of Micro Channel Heat Sink with Periodic Spatial Modification on Sidewalls；[DOI](https://doi.org/10.3390/mi13111986) | p.1、p.9 §2.7 | 以 Nu 和摩擦因子對照來源；區分其基準直通道與改型通道 | 基準通道驗證自動涵蓋所有修改形狀 |
| P048.pdf；Yu 等 (2023), Numerical Investigation of Fluid Flow and Heat Transfer in High-Temperature Wavy Microchannels with Different Shaped Fins Cooled by Liquid Metal；[DOI](https://doi.org/10.3390/mi14071366) | p.1、p.5 網格研究、p.6 §2.5 | 壓降與溫度對網格的敏感性分別看；液態金屬物性另建來源 | 用水冷案例的預設值、殘差或網格數直接搬用 |
| P061.pdf；Soloveva 等 (2024), Numerical Study of the Thermal and Hydraulic Characteristics of Plate-Fin Heat Sinks；[DOI](https://doi.org/10.3390/pr12040744) | p.1、p.9 §2.6 | 參考數值研究與直接實驗對比須分開標記 | 將其引用數值對照自動算成本項目實驗驗證 |
| P064.pdf；Wang 等, Parameterization investigation on the microchannel heat sink with slant rectangular ribs by numerical simulation | p.1 摘要、p.3 Eq.(5)–(6) 與網格段落 | 固定泵功比較、Dh、受熱面積 Aq 與共軛界面 Ac 分別凍結 | 把任意 Re 或不同泵功的點直接比較為優化提升 |
| Microchannel-Pareto.pdf；Zhang 等 (2024), Multi-Objective Optimization of the Microchannel Heat Sink Used for Combustor of the Gas Turbine；[DOI](https://doi.org/10.3390/en17040818) | p.1、p.15 conclusions | DOE/代理/Pareto 可為獨立 Discovery 流程 | 一般水冷微通道採用相同目標；代理值算原生求解 |
| Wavy-Optimization.pdf；Park, Ma & Kim (2021), Optimization of a Wavy Microchannel Heat Sink with Grooves；[DOI](https://doi.org/10.3390/pr9020373) | p.1、pp.13–14 §4.4 | 采樣設計、響應面與多目標；先區分復刻和優化目的 | 其改善百分比可當本項目成功承諾 |

## 證據到工程的追蹤
- Yang → staged-solve-contract / portable-workflow-contract → R03–R07。
- Roache → [網格加密報告指南](grid-refinement-reporting.md) → R09。
- Celik、Eça → 現有 grid uncertainty admission 的增量審計 → R09。
- Brynjarsdóttir、Raue → 現有 conditional calibration，按需額外診斷 → R10、R16。
- CAND → 案例專用幾何/QoI 卡 → R04、R08、R15。
- P017/P048/P061/P064 → 後續不同工質/定義的案例族，不列為本次已實測 benchmark。
- 兩篇優化文章 → opt-in Discovery；不增加默認求解開銷。

沒有引用更新包提及但本次未核實的 CFDTwin 作核心設計依據。官方 API 參考只支持能力設計，具體安裝版本、許可及 MCP 曝露需運行時核對。
