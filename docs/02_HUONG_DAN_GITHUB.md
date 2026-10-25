# 02 – HƯỚNG DẪN GITHUB CHO NGƯỜI MỚI

> Cả nhóm dùng **GitHub Desktop** (giao diện bấm chuột, không cần gõ lệnh). Tải tại desktop.github.com.
> Phần A chỉ nhóm trưởng làm. Phần B mọi thành viên làm. Phần C là quy trình hằng ngày.

## Từ khóa cần biết

| Từ | Nghĩa |
|---|---|
| **Repository (repo)** | Thư mục dự án trên GitHub, lưu lại mọi lịch sử thay đổi |
| **Clone** | Tải repo về máy mình lần đầu |
| **Branch (nhánh)** | Bản sao để mỗi người làm riêng, không đụng vào bản chính `main` |
| **Commit** | "Lưu một mốc" thay đổi trên máy, kèm mô tả ngắn |
| **Push** | Đẩy các commit từ máy lên GitHub |
| **Pull / Fetch** | Lấy thay đổi mới của người khác về máy |
| **Pull Request (PR)** | Đề nghị gộp nhánh của mình vào `main`; TV1 xem rồi bấm Merge |
| **Issue** | Một "phiếu việc" có người phụ trách, hạn, checklist |
| **Milestone** | Mốc hạn, gom nhiều issue |

---

## A. NHÓM TRƯỞNG – thiết lập một lần (tối nay, ~30 phút)

### A1. Tạo tài khoản và cài đặt
1. Đăng ký tài khoản ở github.com (nếu chưa có).
2. Cài **GitHub Desktop**, đăng nhập bằng tài khoản GitHub.
3. Cài **Python 3.11** (python.org, khi cài nhớ tick *Add Python to PATH*) và **VS Code**.

### A2. Đưa bộ khởi đầu lên GitHub
1. Giải nén file `261HHTQD-NhomXX-portfolio.zip` ra một thư mục, ví dụ `Documents\261HHTQD-NhomXX-portfolio`. Đổi `XX` thành số nhóm.
2. Mở GitHub Desktop → **File → Add local repository** → chọn thư mục vừa giải nén.
3. Desktop báo "This directory does not appear to be a Git repository" → bấm **create a repository** → để nguyên → **Create repository**.
4. Bấm **Publish repository** (nút xanh phía trên) → **giữ tick "Keep this code private"** → Publish.
5. Vào github.com → mở repo vừa tạo → kiểm tra đã thấy `README.md`, `docs/`, `src/`.

### A3. Mời thành viên
1. Trong repo trên web: **Settings → Collaborators** (mục *Access*) → **Add people**.
2. Nhập username hoặc email từng người → chọn đúng người → gửi lời mời.
3. Nhắc mọi người **vào email bấm Accept** (lời mời hết hạn sau 7 ngày).

### A4. Tạo Milestones (mốc hạn)
Repo → tab **Issues** → **Milestones** → **New milestone**. Tạo 5 cái:

| Tên | Hạn |
|---|---|
| M0 – Dữ liệu sạch | 28/10/2026 |
| M1 – Bước S + giả thuyết | 29/10/2026 |
| M2 – Đóng băng số liệu | 03/11/2026 |
| M3 – Report + dashboard | 05/11/2026 |
| M4 – Nộp bài | 08/11/2026 |

### A5. Tạo Issues (phiếu việc)
Tab **Issues → New issue**. Tạo **mỗi thành viên 1 issue**, nội dung copy từ bảng của người đó trong `docs/01_PHAN_CONG_VA_DEADLINE.md`, viết dạng checklist:

```
Tiêu đề: [TV2] Dữ liệu – bước O

- [ ] 27/10 Danh sách VN30 kỳ 1/2020 + nguồn
- [ ] 28/10 Tải giá + VN-Index + TPCP, ETL, prices.csv
- [ ] 28/10 Từ điển dữ liệu + Nhật ký ETL (Drive)
- [ ] 29/10 Nguồn phí, thuế, Damodaran → TV1
- [ ] 04/11 Viết phần 4 report
- [ ] 07/11 Kiểm tra tái lập run_all.py
```
Bên phải: **Assignees** = người đó; **Milestone** = mốc gần nhất. Mỗi khi xong một dòng, người đó tự tick.

Tạo thêm 3 issue chung: **"Sổ giả định"** (mọi người comment nguồn vào đây), **"Chốt thiết kế 02/11"**, **"Hỏi thầy"**.

### A6. Quy tắc bảo vệ nhánh `main`
Repo private trên tài khoản miễn phí **không bật được khóa nhánh**, nên nhóm áp dụng bằng quy ước: **không ai commit thẳng vào `main`**, mọi thay đổi qua Pull Request, TV1 duyệt.
(Nếu bạn có GitHub Pro qua *GitHub Student Developer Pack* thì vào Settings → Rules → Rulesets để khóa `main`.)

### A7. Thiết lập Drive
Tạo thư mục `261HHTQD_NhomXX` theo cấu trúc ở mục 6 file 01. Upload 3 file trong `templates/` lên `05_Phu_luc/`, mở bằng **Google Sheets** (chuột phải → Mở bằng → Google Trang tính) để cả nhóm cùng sửa. Share quyền *Người chỉnh sửa* cho cả nhóm.

---

## B. THÀNH VIÊN – cài đặt một lần

1. Chấp nhận lời mời trong email.
2. Cài **GitHub Desktop**, **Python 3.11**, **VS Code**.
3. GitHub Desktop → **File → Clone repository** → tab GitHub.com → chọn repo nhóm → chọn chỗ lưu → **Clone**.
4. Tạo nhánh của mình: thanh trên cùng **Current branch → New branch** → đặt tên theo vai:

| TV | Tên nhánh |
|---|---|
| TV1 | `tv1-buoc-s` |
| TV2 | `tv2-du-lieu` |
| TV3 | `tv3-mo-ta` |
| TV4 | `tv4-uoc-luong` |
| TV5 | `tv5-backtest` |
| TV6 | `tv6-report` |

5. Bấm **Publish branch**.
6. Cài thư viện: mở thư mục repo bằng VS Code → **Terminal → New Terminal** → gõ:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   (Mac: `source .venv/bin/activate`.) Thư mục `.venv` đã được `.gitignore` bỏ qua, không bị đẩy lên GitHub.

---

## C. QUY TRÌNH HẰNG NGÀY (mọi người)

```
Đầu buổi:   cập nhật từ main  →  làm việc  →  commit  →  push  →  tạo Pull Request
```

1. **Đầu buổi – lấy thay đổi mới:** GitHub Desktop, đang ở nhánh của mình → menu **Branch → Update from main**. (Nếu thấy nút **Fetch origin / Pull origin** thì bấm luôn.)
2. **Làm việc** trong VS Code, chỉ sửa file thuộc phần mình.
3. **Commit:** GitHub Desktop hiện danh sách file thay đổi bên trái → ô *Summary* ghi ngắn, ví dụ `tv2: thêm prices.csv 2017-2026` → **Commit to tv2-du-lieu**. Commit nhiều lần nhỏ, đừng để dồn.
4. **Push:** bấm **Push origin**.
5. **Khi xong một việc trong checklist → Pull Request:** bấm **Create Pull Request** (mở trình duyệt) → tiêu đề rõ → mô tả ghi `Liên quan #số-issue` → **Create pull request** → báo TV1 trong nhóm chat.
6. **TV1 duyệt:** mở PR → tab **Files changed** xem qua → nếu ổn bấm **Merge pull request → Confirm merge**. Nếu cần sửa, viết comment, người kia sửa tiếp trên cùng nhánh rồi push (PR tự cập nhật).

### Quy tắc tránh xung đột
- **Mỗi file có một chủ:** `config.yaml` chỉ TV1 sửa; `src/metrics.py` chỉ TV3; `src/estimators.py`, `src/optimizers.py` chỉ TV4; `src/backtest.py`, `run_all.py` chỉ TV5; `src/data_loader.py`, `src/clean.py` chỉ TV2. Muốn đổi file người khác → nhắn người đó.
- Gặp **conflict** (GitHub Desktop báo đỏ) → đừng tự xóa, nhắn TV1 hoặc chủ file, cùng xử lý.
- Không đẩy: `.venv/`, file > 50MB, `.pbix`, video, mật khẩu/token.

### Lỗi hay gặp
| Hiện tượng | Cách xử lý |
|---|---|
| Push bị từ chối | Bấm **Fetch origin**, rồi **Pull**, rồi Push lại |
| Lỡ commit vào `main` | Đừng push. **Branch → New branch** (mang theo thay đổi) rồi push nhánh mới. Đã push thì báo TV1 |
| `pip` báo không tìm thấy | Chưa kích hoạt `.venv`, chạy lại lệnh `activate` |
| Không thấy repo khi Clone | Chưa Accept lời mời trong email |

---

## D. TRƯỚC KHI NỘP (TV1, ngày 08/11)

1. Merge hết PR, `main` chạy được `python run_all.py`.
2. Repo → **Settings → General → Danger Zone → Change visibility → Public** (hoặc mời tài khoản thầy vào Collaborators, theo yêu cầu của thầy).
3. Copy link repo vào `GitHub_link.txt` trong thư mục nộp.
