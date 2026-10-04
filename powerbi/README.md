# LearnMate Power BI — 資料管線與檔案位置

這份說明讓任何人（包含接手的同學）都能從頭產出 LearnMate AI 儀表板的資料，
**不需要 GPT、不需要設定 Power BI 連資料庫**。

## 一句話原理

Power BI 本身**不直接連資料庫**，它讀一個 Excel。那個 Excel 由 Django 從資料庫
匯出的 JSON 組成。所以只要 Django 連得到資料庫（本機或 AWS 都行），就能產出。

```
資料庫 ──(Django)──> JSON ──(build_workbook.py)──> Excel ──> .pbix 重新整理
```

## 檔案放在哪

| 東西 | 位置 |
|---|---|
| **匯出指令**（讀資料庫 → JSON）| `myproject/main/management/commands/export_powerbi_json.py` |
| **建 Excel 的腳本**（JSON → xlsx）| `powerbi/build_workbook.py` |
| **最新產出的資料**（JSON + Excel）| `outputs/learnmate/` |
| **Demo 資料種子**（可選，灌展示用學習資料）| `myproject/main/management/commands/seed_powerbi_demo.py` |
| **報表檔 .pbix** | 你的桌面 `專題報告檔案\LearnMate_AI_Dashboard.pbix` |
| GPT 最初版本（保留參考，可不理）| `outputs/01a0f85f-.../` |
| 舊的「營收/分潤」方向指南（非 LearnMate，保留參考）| `powerbi/owner_dashboard_build_guide.md`、`teacher_dashboard_build_guide.md` |

## 怎麼重新產生資料（三步）

```bash
cd myproject

# 1.（第一次或換機）套用資料表欄位
python manage.py migrate

# 2.（可選）要展示用的完整資料就灌 demo；要純真實資料就跳過
python manage.py seed_powerbi_demo

# 3. 匯出 JSON
python manage.py export_powerbi_json --output ../outputs/learnmate/learnmate_powerbi_data.json

# 4. 組成 Excel
cd ../powerbi
python build_workbook.py --input ../outputs/learnmate/learnmate_powerbi_data.json --output ../outputs/learnmate/LearnMate_PowerBI_Data.xlsx
```

## 怎麼讓 .pbix 吃到新資料

打開 `LearnMate_AI_Dashboard.pbix` →「**轉換資料 → 資料來源設定**」→
把來源路徑改成 `outputs/learnmate/LearnMate_PowerBI_Data.xlsx` → **重新整理**。
工作表名稱（StudentsTable、CourseHealthTable…）、欄位都與原本一致，圖表不會壞。

## 真實資料 vs demo 資料

- `seed_powerbi_demo` 產的是**展示用** demo（分數由實際對錯計算，但作答是程式生成）。
- 正式比賽要用真實資料：學生在平台**實際交卷後**，`submit_quiz` 會自動把弱點
  （依真實錯題按知識點分組）落地到 `QuizAttempt`，之後匯出就是真資料，不需補造。

## 17 張資料表（對應 .pbix 的表格）

students, courses, chapters, lessons, enrollments, lesson_progress, learning_records,
course_summaries, quizzes, questions, quiz_results, answers, weak_topics,
remedial_comparisons, student_course_metrics, course_health, topic_stats。
