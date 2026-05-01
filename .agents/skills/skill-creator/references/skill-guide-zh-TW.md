# Skill Creator 繁體中文導覽

本文件為 `skill-creator` 的繁體中文摘要，供熟悉中文的使用者快速上手。
技術名詞與工具名稱保留英文，說明文字以繁體中文撰寫。

---

## 核心概念

**Skill** 是一套寫給 Claude 的指引，包含：
- **SKILL.md frontmatter** (`name` + `description`)：模型在決定是否呼叫此 skill 時看到的內容
- **SKILL.md body**：觸發後載入的詳細指引（目標 < 500 行 / ~5000 tokens）
- **Bundled resources**：腳本、參考文件、範本等（按需載入，無大小限制）

---

## 主要工作流程

1. **釐清意圖** — 確認 skill 要做什麼、何時觸發、預期輸出格式
2. **撰寫 SKILL.md** — 包含 frontmatter (`name`, `description`, `compatibility`) 與主體指引
3. **建立測試案例** — 儲存至 `evals/evals.json`，先只寫 prompt，assertions 後補
4. **執行 eval 跑測** — 同一輪次同時啟動 with_skill 和 baseline 兩組 subagent
5. **撰寫 assertions** — 趁 eval 跑測期間草擬可驗證的斷言，更新 `eval_metadata.json`
6. **評分 (grading)** — 使用 `agents/grader.md`，輸出含 `assertion_results` 的 `grading.json`
7. **彙整 (benchmark)** — 執行 `python -m scripts.aggregate_benchmark <workspace>/iteration-N`
8. **檢視結果** — 啟動 `eval-viewer/generate_review.py`，請使用者在 Outputs tab 留下回饋
9. **改進 skill** — 根據回饋泛化（勿過度 overfit），重複直到滿意
10. **描述最佳化 (optional)** — 執行 `python -m scripts.run_loop` 提升觸發準確度
11. **打包** — 執行 `python -m scripts.package_skill` 輸出 `.skill` 檔

---

## 關鍵 JSON 結構速查

### `evals/evals.json`
```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "用戶的任務描述",
      "expected_output": "預期輸出的文字說明",
      "files": [],
      "assertions": ["輸出包含欄位 X", "使用了腳本 Y"]
    }
  ]
}
```

### `eval_metadata.json` (每個測試案例目錄下)
```json
{
  "eval_id": 0,
  "eval_name": "具描述性的名稱",
  "prompt": "任務描述",
  "assertions": ["斷言 1", "斷言 2"]
}
```

### `grading.json` (grader agent 輸出)
```json
{
  "assertion_results": [
    { "text": "斷言文字", "passed": true, "evidence": "證據引用" }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```
> 注意：舊版使用 `expectations` 欄位名稱；現已統一為 `assertion_results`。
> 若需升級舊 workspace，執行 `scripts/migrate_schema.py`。

### `benchmark.json` delta 格式
```json
"delta": { "pass_rate": 0.5, "time_seconds": 13.0, "tokens": 1700 }
```
> `delta` 為**數值**（不是字串），顯示時由 viewer 自動加上 `+/-` 符號。

---

## Windows 指令對照

| 用途 | POSIX (bash) | Windows (PowerShell) |
|------|-------------|---------------------|
| 背景啟動 viewer | `nohup python generate_review.py … &` | `$j = Start-Job { python generate_review.py … }` |
| 停止 viewer | `kill $VIEWER_PID` | `Stop-Job $j; Remove-Job $j` |
| 暫存目錄 | `/tmp/` | `$env:TEMP\` |
| 開啟 HTML 檔 | `open file.html` | `Start-Process file.html` |

---

## 腳本執行方式

所有 CLI 腳本均支援兩種執行方式：

```bash
# 標準 Python（需自行安裝 pyyaml 等依賴）
python scripts/quick_validate.py .agents/skills/my-skill

# 使用 uv（自動安裝依賴，PEP 723 inline metadata）
uv run scripts/quick_validate.py .agents/skills/my-skill --strict
```

若以模組方式執行（用於存取 `scripts.*` 內部 import）：
```bash
python -m scripts.aggregate_benchmark benchmarks/latest/
python -m scripts.run_loop --eval-set evals/eval_set.json --skill-path ./my-skill --model <model>
```

---

## Trigger Adapter

`run_eval.py` 和 `run_loop.py` 使用 `--adapter` 參數選擇觸發偵測方式：

| Adapter | 說明 |
|---------|------|
| `claude-code` (預設) | 使用 `claude -p` CLI，需安裝 Claude Code |
| `kilo` | 待實作（目前為骨架） |
| `manual` | 互動式降級（待實作） |

---

## 常見問題 (Gotchas)

1. **Viewer 顯示空白斷言** — 確認 `grading.json` 使用 `assertion_results`（不是 `expectations`），且每個項目含 `text`、`passed`、`evidence` 三個欄位。

2. **Benchmark delta 顯示異常** — 確認 `benchmark.json` 的 `delta` 是數值型態（如 `0.5`），不是字串（如 `"+0.50"`）。

3. **Windows 上 run_eval.py 崩潰** — 舊版使用 `select.select`（POSIX only）。新版改用 `threading` + `readline`，應可在 Windows 執行。

4. **Description > 1024 字元** — `quick_validate.py` 會報錯；`improve_description.py` 在超長時會自動重試縮短。

5. **SKILL.md 超過 500 行** — `quick_validate.py --strict` 會發出警告；將非核心章節移至 `references/` 目錄。

---

## 參考文件索引

| 文件 | 說明 |
|------|------|
| `references/schemas.md` | 所有 JSON 結構定義 |
| `references/environments.md` | 各環境（Claude.ai、Cowork、Windows）差異說明 |
| `references/blind-comparison.md` | 盲測比較完整流程 |
| `references/writing-guide.md` | SKILL.md 撰寫指南（anatomy、progressive disclosure、寫作風格） |
| `agents/grader.md` | Grader subagent 指引 |
| `agents/comparator.md` | Comparator subagent 指引 |
| `agents/analyzer.md` | Analyzer subagent 指引 |
