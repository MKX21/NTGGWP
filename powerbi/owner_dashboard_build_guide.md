# 老闆端 Power BI 儀表板 — 建置指南

對應功能:年度/月度營業額趨勢與目標比較 / 熱賣冷門課程排行 / 分類講師營運表現比較 / 退款與折扣成本總覽 / 詳細營業額(逐筆可鑽研)

前置作業:先執行 `teacher_dashboard_views.sql`,再執行同資料夾的 `owner_dashboard_views.sql`(後者的分類/講師表現是疊在前者的 `vw_course_sales_summary` 上面算的,順序不能反)。

---

## 1. 這次要匯入的表

跟講師端共用同一份資料來源(同一個 MySQL 連線),在 Power BI 裡「取得資料」的清單勾選:

```
vw_revenue_detail          -- 逐筆訂單明細,詳細營業額的主力表
vw_platform_daily_revenue  -- 每日營收彙總,拉趨勢圖用
vw_platform_daily_refund   -- 每日退款彙總
vw_course_sales_summary    -- 課程層級(熱賣/冷門排行用,講師端已經匯過的話可以共用)
vw_category_performance    -- 分類彙總
vw_teacher_performance     -- 講師彙總
```

如果你是在同一個 .pbix 檔案裡同時做老闆端 + 講師端(用頁籤分開,建議這樣做,維護只要一份檔案),`vw_course_sales_summary` 只匯入一次,兩邊頁籤共用即可,不用重複匯入。

---

## 2. 日期表(沿用講師端那份 DimDate,同一個檔案不用重建)

如果是新檔案,一樣用:

```dax
DimDate = CALENDAR ( DATE ( 2024, 1, 1 ), TODAY () )
年月 = FORMAT('DimDate'[Date], "YYYY-MM")
年 = YEAR('DimDate'[Date])
季 = "Q" & QUARTER('DimDate'[Date])
```

`vw_revenue_detail[order_date]`、`vw_platform_daily_revenue[order_date]`、`vw_platform_daily_refund[refund_date]` 都跟 `DimDate[Date]` 建多對一關聯。

---

## 3. 年度目標(手動輸入表)

系統目前沒有存「目標營業額」這種資料(不是 bug,是本來就沒有這個功能),要做「趨勢與目標比較」需要自己在 Power BI 裡建一張手動表。

在 Power BI 裡:常用 → 輸入資料,建一張表:

| 年月 | 目標營業額 |
|---|---|
| 2026-01 | 100000 |
| 2026-02 | 120000 |
| ... | ... |

之後把這張表的「年月」跟 DimDate 的「年月」關聯起來。如果之後想讓目標可以在後台調整而不是每次改 Power BI,可以請 Django 那邊加一張簡單的 `MonthlyGoal(year_month, target_amount)` model,之後 Power BI 直接接那張表就好——這個可以寫進專題報告當「未來優化方向」。

---

## 4. DAX 量測值

### 4.1 營業額趨勢與目標比較

```dax
總營業額 = SUM ( vw_revenue_detail[paid_amount] )

去年同期營業額 =
CALCULATE (
    [總營業額],
    SAMEPERIODLASTYEAR ( 'DimDate'[Date] )
)

年增率 =
DIVIDE ( [總營業額] - [去年同期營業額], [去年同期營業額] )

目標達成率 =
DIVIDE ( [總營業額], SUM ( 年度目標[目標營業額] ) )
```

放的視覺:大卡片(本月營業額 + 年增率箭頭)+ 營業額 vs 目標 折線圖(兩條線疊在一起,目標用虛線)+ 月度營業額長條圖。

### 4.2 熱賣/冷門課程排行

```dax
課程營業額 = SUM ( vw_course_sales_summary[paid_amount] )

課程購買數 = SUM ( vw_course_sales_summary[enrollment_count] )

課程排名 =
RANKX (
    ALL ( vw_course_sales_summary[course_title] ),
    [課程營業額],
    , DESC
)
```

放的視覺:橫向長條圖,由大到小排序,前 10 名跟後 10 名各用一張(在篩選窗格用「前 N 個」設定),冷門課程那張建議加平均評分欄位輔助判斷——賣得差但評分高,可能是行銷問題不是內容問題,這個洞察對老闆決策比單純排行更有用。

### 4.3 分類/講師營運表現比較

```dax
分類營收佔比 =
DIVIDE ( SUM ( vw_category_performance[total_revenue] ), [總營業額] )

講師平均營收 = AVERAGE ( vw_teacher_performance[total_revenue] )

講師退款率 = AVERAGE ( vw_teacher_performance[refund_rate] )
```

放的視覺:分類營收佔比圓環圖 + 講師營收排行長條圖(可以疊加平均評分當第二軸,找出「高營收但評分偏低」需要關注的講師)。

### 4.4 退款與折扣成本總覽

```dax
總退款金額 = SUM ( vw_platform_daily_refund[refund_amount] )

平台退款率 =
DIVIDE (
    SUM ( vw_platform_daily_refund[refund_count] ),
    SUM ( vw_platform_daily_revenue[paid_order_count] )
)

總折扣金額 = SUM ( vw_revenue_detail[discount_amount] )

折扣佔營收比 =
DIVIDE ( [總折扣金額], SUM ( vw_revenue_detail[list_price] ) )

有優惠券訂單佔比 =
DIVIDE (
    CALCULATE ( COUNTROWS ( vw_revenue_detail ), NOT ISBLANK ( vw_revenue_detail[coupon_code] ) ),
    COUNTROWS ( vw_revenue_detail )
)
```

放的視覺:3 張卡片(總退款金額 / 折扣佔營收比 / 有券訂單佔比)+ 退款金額趨勢折線圖(跟營業額疊圖,看退款是不是跟著促銷活動一起變多)。

### 4.5 詳細營業額(逐筆鑽研)

不需要額外量測值,直接把 `vw_revenue_detail` 拉成一張明細表(矩陣視覺),欄位建議:訂單日期、課程名稱、分類、講師、學生、售價、折扣金額、實付金額、付款方式、優惠碼。

在其他頁的圖表上設定「鑽研到詳細資料」(在視覺化的格式選項打開 Drillthrough),這樣老闆在營業額趨勢圖上對某個月按右鍵,就能直接跳到那個月的逐筆明細,不用另外去資料庫查。

---

## 5. 版面建議

```
頁籤 1「經營總覽」    總營業額卡片 + 年增率 + 營業額 vs 目標趨勢圖
頁籤 2「課程排行」    熱賣 Top10 / 冷門 Bottom10 長條圖(各佔一半版面)
頁籤 3「分類與講師」  分類營收圓環圖 + 講師營收排行(疊評分)
頁籤 4「退款與折扣」  3 張卡片 + 退款金額趨勢折線圖
頁籤 5「詳細營業額」  vw_revenue_detail 矩陣明細表,作為其他頁的鑽研目標頁
```

跟講師端的 4 個頁籤放在同一份 .pbix 裡的話,建議用頁籤群組或前面加「老闆」「講師」字樣區分,同時把老闆端頁籤設成「頁面存取權限」(進階功能,選做),避免展示時混在一起。
