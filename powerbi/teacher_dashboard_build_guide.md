# 講師端 Power BI 儀表板 — 建置指南

對應功能:真實淨收入與提領總覽 / 課程銷售與退款分析 / 學生互動與評價分析 / 單元完成率與棄看熱點

前置作業:先在你們的 MySQL 資料庫執行同資料夾的 `teacher_dashboard_views.sql`,建立好 8 個 view。之後這份指南裡的 Power BI 步驟都是直接接這些 view,不用再處理原始表的 join。

---

## 1. 連接資料來源

Power BI Desktop → 常用 → 取得資料 → 更多 → 資料庫 → **MySQL 資料庫**。

需要:主機位址、Port(預設 3306)、資料庫名稱、帳號密碼(跟你們 Django `.env` 裡 `DATABASES` 用的是同一組)。第一次連線會要求安裝 **MySQL Connector/NET**,沒裝的話 Power BI 會跳出下載連結。

匯入模式選 **Import**(不要 DirectQuery)— 專題資料量小,Import 之後所有視覺化都不用等資料庫回應,DAX 也比較好寫。

只勾選這 8 張 view,不要整庫匯入:

```
vw_teacher_revenue_ledger
vw_teacher_withdrawals
vw_teacher_balance
vw_course_sales_summary
vw_refund_detail
vw_order_item_discount
vw_lesson_completion
vw_course_engagement
vw_review_detail
```

---

## 2. 建立日期表(用來做趨勢圖的月份軸)

新增資料表(Power Query 或 DAX 都可以),用 DAX 建一張獨立日期表:

```dax
DimDate =
CALENDAR (
    DATE ( 2024, 1, 1 ),
    TODAY ()
)
```

再加幾欄方便分組:

```dax
年月 = FORMAT('DimDate'[Date], "YYYY-MM")
年 = YEAR('DimDate'[Date])
月 = MONTH('DimDate'[Date])
```

---

## 3. 建立關聯(模型檢視)

| 表 A | 欄位 | 表 B | 欄位 | 方向 |
|---|---|---|---|---|
| vw_teacher_revenue_ledger | created_at (日期部分) | DimDate | Date | 多對一 |
| vw_review_detail | created_at (日期部分) | DimDate | Date | 多對一 |
| vw_order_item_discount | order_created_at (日期部分) | DimDate | Date | 多對一 |
| vw_course_sales_summary | course_id | vw_lesson_completion | course_id | 一對多(可選,或用課程名稱切片器分開篩選就好) |

> Power BI 的關聯要求鍵值型態一致,日期時間欄位建議在 Power Query 裡先切出「純日期」欄位(Date.From),再拿去跟 DimDate 關聯,不要直接拿 datetime 關聯。

如果只做單一講師的展示(不需要多講師切換),可以先不用設 RLS,直接在每一頁最上面放一個「課程」或「講師」交叉分析篩選器(Slicer)手動切換 — 這對專題展示來說最簡單也最不會出錯。若之後真的要嵌回平台給每個講師登入後只看自己的資料,才需要做第 6 節的 RLS。

---

## 4. DAX 量測值(依 4 個功能分組)

### 4.1 真實淨收入與提領總覽

```dax
淨收入 =
CALCULATE (
    SUM ( vw_teacher_revenue_ledger[teacher_amount] ),
    vw_teacher_revenue_ledger[status] = "confirmed"
)

已提領金額 =
CALCULATE (
    SUM ( vw_teacher_withdrawals[amount] ),
    vw_teacher_withdrawals[status] = "completed"
)

待處理提領 =
CALCULATE (
    SUM ( vw_teacher_withdrawals[amount] ),
    vw_teacher_withdrawals[status] = "pending"
)

可提領餘額 = SUM ( vw_teacher_balance[available_balance] )

行銷成本佔比 =
DIVIDE (
    SUM ( vw_teacher_revenue_ledger[marketing_cost] ),
    SUM ( vw_teacher_revenue_ledger[gross_amount] )
)
```

放的視覺:3 張卡片(淨收入 / 可提領餘額 / 待處理提領)+ 一張「淨收入」按月折線圖(用 DimDate[年月] 當 X 軸)+ 提領紀錄表格(狀態用色塊區分)。

### 4.2 課程銷售與退款分析

```dax
總銷售額 = SUM ( vw_course_sales_summary[paid_amount] )

總購買數 = SUM ( vw_course_sales_summary[enrollment_count] )

退款率 =
DIVIDE (
    SUM ( vw_course_sales_summary[refund_count] ),
    SUM ( vw_course_sales_summary[enrollment_count] )
)

平均折扣率 =
DIVIDE (
    SUM ( vw_course_sales_summary[discount_amount] ),
    SUM ( vw_course_sales_summary[gross_amount] )
)

有券訂單佔比 =
DIVIDE (
    CALCULATE ( COUNTROWS ( vw_order_item_discount ), NOT ISBLANK ( vw_order_item_discount[coupon_code] ) ),
    COUNTROWS ( vw_order_item_discount )
)
```

放的視覺:各課程銷售額橫向長條圖(由高到低排序)+ 退款率 vs 銷售額散佈圖(找出「賣得多但退很兇」的課)+ 退款原因文字雲或表格(來源 `vw_refund_detail[reason]`)。

### 4.3 學生互動與評價分析

```dax
平均評分 = AVERAGE ( vw_review_detail[rating] )

評論數 = COUNTROWS ( vw_review_detail )

未回覆問題數 = SUM ( vw_course_engagement[unanswered_count] )

平均回覆時間(分鐘) = AVERAGE ( vw_course_engagement[avg_response_minutes] )
```

放的視覺:評分按月趨勢折線圖 + 各課程平均評分長條圖 + 未回覆問題數卡片(建議設條件格式,>0 就標紅提醒講師要去回)。

### 4.4 單元完成率與棄看熱點

```dax
平均完成率 = AVERAGE ( vw_lesson_completion[completion_rate] )

平均觀看百分比 = AVERAGE ( vw_lesson_completion[avg_watch_percent] )

低完成率單元數 =
CALCULATE (
    COUNTROWS ( vw_lesson_completion ),
    vw_lesson_completion[completion_rate] < 0.5
)
```

放的視覺:單元完成率排行榜(表格,由低到高排序,一眼看出棄看熱點在哪個單元)+ 章節層級的完成率長條圖(X 軸用 chapter_title,方便講師抓到「第幾章」開始流失)。

---

## 5. 版面建議(4 個報表頁)

```
頁籤 1「淨收入總覽」   卡片 x3 + 淨收入趨勢折線圖 + 提領紀錄表
頁籤 2「銷售與退款」   課程銷售長條圖 + 退款率散佈圖 + 退款原因表
頁籤 3「學生互動評價」 評分趨勢折線圖 + 課程評分長條圖 + 未回覆問題卡片
頁籤 4「完成率與棄看」 單元完成率排行表 + 章節完成率長條圖
```

每頁左上角放課程切片器(Slicer),同步篩選(在「篩選」→「同步交叉分析篩選器」裡打開,4 頁都勾),這樣切換課程時 4 頁資料一起連動。

---

## 6.(進階,選做)未來要嵌回平台的話怎麼做 RLS

如果之後要把報表嵌進 Django 平台,讓每個講師登入後台只看得到自己的資料,不能靠 Power BI 原生 RLS 的 `USERNAME()`(那個綁的是 Azure AD 帳號,跟你們 Django 的帳號系統是兩套)。正確做法是 **Power BI Embedded「App owns data」模式**:

1. Django 後端呼叫 Power BI REST API 產生 Embed Token 時,帶入 `identities` 參數,把目前登入講師的 `teacher_id` 當作 effective identity 傳進去。
2. Power BI 報表裡設一個 RLS 角色,規則寫 `[teacher_id] = USERNAME()`(這裡的 USERNAME() 讀到的其實是你傳進去的 identity,不是真的 AD 帳號)。
3. 前端用 `powerbi-client` JS SDK,拿後端回傳的 embed token + embed URL 塞進 iframe。

這一步需要 Azure Power BI Embedded 容量(要付費),對專題來說可以先在報告裡寫成「未來規劃」,demo 時用第 3 節提到的手動切片器就夠了。
