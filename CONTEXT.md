# NTGGWP 領域詞彙

這份文件定義程式碼與討論共用的名詞。**改動定價、結帳、課程進度相關的程式時，先讀這裡。**
新概念進入程式時，同時把詞加進來（見 `docs/agents/domain.md`）。

## 金額與定價

| 詞 | 定義 | 在程式裡 |
|---|---|---|
| **定價** | 講師設定的原始價格，不含任何折扣。 | `Course.price` |
| **售價** | 這堂課目前單獨賣多少。募資期間內優先取早鳥價，其次取折扣價，兩者只取其一，不疊加。 | `Course.get_effective_price()` |
| **折扣價** | 講師自訂的長期折扣，任何課程都可設定，須低於定價。 | `Course.discount_price` |
| **早鳥價** | 募資課程在募資期間內的優惠價，須低於定價。募資期間外不生效。 | `Course.early_bird_price` |
| **促銷** | 平台層的行銷活動，由管理員逐課勾選適用範圍，作用於**售價**。促銷與早鳥價／折扣價**會疊加**。 | `Promotion` |
| **優惠券** | 使用者持有並在結帳時輸入的折抵，作用於**促銷後的小計**。 | `Coupon`、`UserCoupon` |
| **報價** | 一次結帳意圖的計算結果：逐項售價、各層折扣、實付總額。**尚未寫入資料庫**，重新整理頁面會重算。 | `checkout.Quote` |
| **實付** | 報價的總額，也是使用者實際要付的錢。 | `Quote.total` → `Order.final_price` |

### 折扣的疊加順序

**唯一的順序，由 `main/checkout.py` 定義：**

```
售價  = get_effective_price()      早鳥價或折扣價，二者取一
小計  = 售價 − 促銷折扣             促銷作用於售價
實付  = 小計 − 優惠券折扣           優惠券作用於小計
```

每一層都作用於前一層的結果（依序遞減），因此折扣總額**結構上不可能超過售價**，不需要事後夾 0。

優惠券的 `min_spend`（最低消費）語意是「**促銷後**仍需消費滿 N 元」。

## 結帳與訂單

| 詞 | 定義 | 在程式裡 |
|---|---|---|
| **購物籃** | 一次結帳要買的課程集合。單課直購是「只有一項的購物籃」，走同一條定價路徑。 | `quote_basket(user, courses, coupon_code)` |
| **成立訂單** | 把報價寫成待付款的訂單（訂單 + 明細 + 付款紀錄三者原子性建立）。**成立訂單不代表付款完成，也不會開通課程。** | `place_order(user, quote)` |
| **開通** | 付款成功後才發生：建立購課紀錄、標記優惠券已使用、發送通知。具冪等性。 | `transitions.fulfill_order` |
| **退款** | 開通的反向操作：**撤銷購課紀錄**、回沖付款、發送通知。撤銷的是存取權，不是歷史 —— 學習紀錄與評價一律保留。 | `transitions.approve_refund` |

### 三個階段

```
結帳 checkout.py  →  付款 payments.py  →  開通 transitions.fulfill_order
（算錢、成立待付款訂單）  （金流閘道）      （開課、標券、通知）
```

### 狀態轉換只有一個入口

`main/transitions.py` 是「訂單付款後會發生什麼」與「課程什麼時候能上架」的**唯一**
答案。前台 view 與後台 admin 都呼叫同一份，因此不存在兩套行為：

```
fulfill_order        付款成功 → 開通、建立分潤紀錄
approve_refund       核准退款 → 撤銷存取、回沖付款、沖銷分潤紀錄
reject_refund        拒絕退款
approve_course       審核通過 → 上架（上架的唯一路徑，必留審核紀錄）
reject_course        審核退回 → 下架
complete_withdrawal  提領完成
reject_withdrawal    提領拒絕
```

七個入口皆具冪等性。**新增任何會改變訂單或課程狀態的動作時，加進這裡，
不要在 view 或 admin 裡就地寫一套。**

### `OrderItem` 的三個金額

| 欄位 | 語意 |
|---|---|
| `price` | 購買當下的**售價**（促銷前、券前）。歷史紀錄，不因後續活動改變。 |
| `discount_amount` | 分攤到這一項的促銷 + 優惠券折扣。 |
| `paid_amount` | 這一項的**實付**。同一張訂單所有明細的 `paid_amount` 加總，精確等於 `Order.final_price`。 |

優惠券折扣按各項「促銷後金額」比例分攤，採**最大餘額法**取整，確保加總精確相等。

## 分潤、收支與提領

| 詞 | 定義 | 在程式裡 |
|---|---|---|
| **課程分潤設定** | 每堂課的講師／公司分潤比例，以及行銷成本（如 Facebook 廣告費）由誰負擔多少。兩組比例各自須加總 100，互相獨立。未自訂過的課程套用預設值（分潤 7:3、成本各半）。 | `CourseSplitSetting`、`CourseSplitSetting.for_course(course)` |
| **收支分潤紀錄** | 一筆 `OrderItem` 付款成功後，依當下的課程分潤設定拆算出的講師應付金額與公司實收金額。比例是**建立當下拍照存檔**，之後設定異動不會追溯改到已建立的紀錄。 | `RevenueRecord` |
| **提領** | 講師申請把累積的分潤兌現。可提領餘額 = 所有 `confirmed` 分潤紀錄的講師應付金額加總，扣掉已佔用（`pending`/`completed`）的提領金額；超額申請在 model 層直接擋下。 | `WithdrawalRequest`、`WithdrawalRequest.available_balance(teacher)` |

### 分潤金額怎麼算

```
講師應收(毛額) = 實付金額 × 講師分潤比例（四捨五入）
公司應收(毛額) = 實付金額 − 講師應收(毛額)        ← 用相減取整，兩者加總精確等於實付金額
講師負擔成本   = 行銷成本 × 講師成本負擔比例（四捨五入）
公司負擔成本   = 行銷成本 − 講師負擔成本
講師應付金額   = 講師應收(毛額) − 講師負擔成本
公司實收金額   = 公司應收(毛額) − 公司負擔成本
```

兩組比例分開套用（分潤比例作用於毛額，成本負擔比例作用於行銷成本），
因此改行銷成本負擔比例不會影響分潤比例，反之亦然。

### 跟著訂單狀態轉換走

分潤紀錄的建立與沖銷是 `transitions.py` 既有五個入口的延伸，不是另一套流程：

```
fulfill_order      付款成功 → 開通課程的同時，逐 OrderItem 建立分潤紀錄（confirmed）
approve_refund     核准退款 → 把該訂單的分潤紀錄標記為 reversed（保留歷史，不刪除）
```

行銷成本目前沒有自動來源（無串接 Facebook 廣告 API），建立時預設 0，
由後台人工事後在 `RevenueRecord.marketing_cost` 填入實際花費；
儲存時會自動重算講師應付金額與公司實收金額。

### 提領審核會通知講師

`complete_withdrawal` / `reject_withdrawal` 一律透過 `transitions._notify_withdrawal`
發站內通知，並在講師的 `User.email` 有填寫時額外寄一封 Email（走 Django
的 `EMAIL_BACKEND`，沒設 SMTP 時退回終端機印出，見 `settings.py` 的
Email 區塊）。**寄信失敗不會讓審核動作跟著失敗**（`fail_silently=True`）——
站內通知已經送達，管理員的核准/拒絕本身要算數，不該被寄信基礎設施擋住。
Django admin 的批次動作與 `manage_withdrawals` 頁面的核准/拒絕按鈕呼叫的是
同一份 `transitions` 函式，因此兩個入口的通知行為完全一致。

## 角色

| 詞 | 定義 | 在程式裡 |
|---|---|---|
| **學生** | 購課、觀看、評價、提問。 | `Profile.role == 'student'` |
| **講師** | 開課、管理章節單元、回答提問、審核自己課程的退款。 | `Profile.role == 'teacher'` |
| **管理員** | 課程審核、退款審核、資料匯出、平台分析。 | `User.is_superuser` |

## 課程的可見性

未上架（`is_published=False`）的課程只有三種人看得到：**課程講師本人**、
**管理員**（要能審核就得看得到內容）、**已購課的學生**（課程可能在購買後才下架，
不該讓付過錢的人吃 404）。其餘一律 404。

預覽權不等於購買權 —— 未上架的課程**任何人都不能購買**，包含講師與管理員。
邏輯在 `views._visible_course_or_404` 與 `views._purchasable_course_or_404`。

付費影片同理：`/media/course_videos/` 不再直出，一律走
`views.stream_lesson_video`，權限與 `watch_lesson` 相同。

## 已知的語意債

這些是目前程式碼與上面定義不符之處，**尚未修正**，不要當成規格：

- `Order.course` 對多課程訂單為 `None`，導致講師營收、退款入口、退款權限都漏掉購物車訂單。每課營收應改由 `OrderItem` 推算。（2026-07-28 實測：共用資料庫中已付款且 `course` 為 `None` 的訂單為 0 筆，因此目前尚未造成實際漏算。）
- 「課程進度」有四種算法（觀看分鐘制、單元數制、秒數制、證書門檻），畫面之間互相矛盾。
- `Order.status` 與 `Payment.status` 的 model default 都是 `'paid'`。正式流程走 `place_order`（明確設 `pending`）不受影響，但從 admin 手動建立的訂單會直接被算進營收。
- 授權檢查有 29 處手抄的 `profile.role` 判斷，沒有共用 decorator。
- CSV 匯出是 11 個近乎相同的 view。
