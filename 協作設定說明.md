# 協作開發設定說明

> ✅ **新做法（推薦）：改用「共用雲端資料庫」**
> 只要大家的 `.env` 都指向同一個雲端 MySQL，資料就是即時共用的——
> 誰新增課程／使用者，其他人重新整理網頁就看得到，**再也不用 `dumpdata`／`loaddata`**。
> 設定方式見下方〈零、改用共用雲端資料庫〉。
>
> ⚠️ 舊做法（本機各自 MySQL + fixtures 匯入）仍保留在下面當備援，
> 但只要設好 `.env`，就不需要再走匯出／匯入那一套了。

---

## 零、改用共用雲端資料庫（設定一次，之後免同步資料）

1. **負責人**去申請一個免費雲端 MySQL（Railway / Aiven / Zeabur 擇一），
   拿到 `host / port / database / user / password`。
2. 每位組員在專案根目錄把範本複製成 `.env`：
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   # Mac / Linux
   cp .env.example .env
   ```
3. 打開 `.env`，填入負責人給的那組**同一份**連線資訊（大家填一樣的）。
4. 安裝套件（多了一個 `python-dotenv`）並建表：
   ```bash
   pip install -r requirements.txt
   cd myproject
   python manage.py migrate      # 只有第一次、或有人新增 migration 時要跑
   python manage.py runserver
   ```

設好之後，日常協作就只剩：**改程式 → `git pull` / `git push`**。
資料在雲端共用，不必再匯出匯入。`.env` 已被 git 忽略，密碼不會外流。

---

## 一、同伴第一次設定專案（clone 後）

```bash
# 1. 取得專案
git clone https://github.com/justingywen/NTGGWP.git
cd NTGGWP

# 2. 安裝套件
pip install -r requirements.txt

# 3. 在自己電腦的 MySQL 建立資料庫
#    先進 MySQL：mysql -u root -p
#    再執行：
CREATE DATABASE course_platform_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
# 4. 修改 myproject/myproject/settings.py 的 DATABASES 密碼
#    把 'PASSWORD': '0000' 改成「你自己 MySQL 的 root 密碼」

# 5. 建立資料表
cd myproject
python manage.py migrate

# 6. 匯入課程/使用者資料（關鍵！這步才會看到課程）
python manage.py loaddata fixtures/initial_data.json

# 7. 啟動
python manage.py runserver
```

開 http://127.0.0.1:8000/ 就會看到一樣的課程資料。

**測試帳號**（密碼見專案負責人）：管理員 `admin` / 老師 `teacher_python` / 學生 `student_amy`。

---

## 二、當你（負責人）更新了資料，要重新分享給同伴

每次你在自己電腦新增/修改了課程資料，重新匯出一次再 commit：

```bash
cd myproject
python -X utf8 manage.py dumpdata auth.user main --indent 2 --output fixtures/initial_data.json
git add fixtures/initial_data.json
git commit -m "更新課程資料"
git push
```

同伴那邊：

```bash
git pull
cd myproject
python manage.py loaddata fixtures/initial_data.json   # 會覆蓋更新成最新資料
```

---

## 三、上傳的影片與圖片

- 課程封面（`media/course_images/`）與示範影片（`media/course_videos/`）目前**有隨 git 一起同步**，所以同伴 clone 後就有。
- 若之後影片檔太大讓 repo 變肥，再改用雲端硬碟另外分享，並在 `.gitignore` 加入 `myproject/media/`。

---

## 四、注意事項

- `settings.py` 裡的 MySQL 密碼是明碼，正式上線前建議改用環境變數。
- 每個人用自己電腦的 MySQL，密碼各自不同，所以 `settings.py` 的 `PASSWORD` 不要互相覆蓋（可各自保留本機設定，不要 push 蓋掉對方）。
- 影片時長會在老師上傳影片時**自動偵測**，不需手動輸入。
