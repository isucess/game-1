# Sân chơi Will & Kem 🦖

Các game học cho bé, tối ưu cho iPad. Mở trang chủ để chọn game:

| Đường dẫn | Game |
|---|---|
| `/` | Menu chọn game |
| `/khung-long-danh-van/` | **Khủng long đánh vần**: nghe cô đánh vần "a – ngờ – ang", di chuyển khủng long hứng đúng quả trứng có vần đó |
| `/flying-numbers/` | **Flying Numbers**: nghe số tiếng Anh 1–20, chạm đúng số khi nó bay qua |

Chung cho cả hai game:

- Chọn 5 hoặc 10 lượt, mỗi lượt sai tối đa 3 lần
- Vật bị thẩy theo vòng cung từ dưới lên, trên xuống, hai bên
- Chạm khủng long: "Dinosaur mà"; chạm chữ **Will**: "Will í ẹ"; chạm chữ **Kem**: "Kem xinh đẹp" (kèm pháo hoa)
- Pause, chơi lại, đồng hồ, sao, bảng xếp hạng có điền tên (mỗi game một bảng)

Khủng long đánh vần thêm:

- Cách chơi: trứng có vần rơi chậm từ trên xuống; bấm ◀ ▶ (hoặc phím mũi tên / A D, hoặc vuốt) để khủng long đứng đúng cột có quả trứng cô vừa đánh vần và đớp lấy
- Chọn nhóm vần: `an · ang · anh` (vần hay nhầm), `Nờ hay ngờ?`, `an ăn ân`, `ang ong ung`, `anh ênh inh`… hoặc trộn tất cả
- Sai 2 lần thì hiện gợi ý `a + ng = ang`; hết lượt thì cô đánh vần lại vần đúng
- Vần bé hay sai được nhớ trên máy và ra nhiều hơn ở các ván sau; màn kết quả có mục "Cần ôn thêm"
- Giọng đọc tiếng Việt có sẵn của iPad (Linh)

## Chạy trên Mac mini

```bash
git clone https://github.com/isucess/game-1.git ~/projects/flying-numbers
cd ~/projects/flying-numbers
bash deploy/install-macmini.sh        # tự chọn port trống từ 8090
bash deploy/autodeploy.sh --install   # tự deploy khi main có commit mới
```

Script in ra địa chỉ cho iPad cùng WiFi, ví dụ `http://192.168.1.20:8090`.
Service chạy bằng launchd, tự bật lại khi máy khởi động. Bảng xếp hạng lưu ở `deploy/scores*.json` (không bị git ghi đè).

**Tự động deploy:** launchd chạy `deploy/autodeploy.sh` mỗi 1 phút. Có commit mới trên `main` → kéo về,
restart server nếu `deploy/server.py` đổi (chỉ sửa các trang `index.html` thì không cần restart), kiểm tra `/health`.
Server lỗi thì tự quay về bản cũ và không thử lại commit đó (push bản sửa là nó thử tiếp).
Log: `~/Library/Logs/flying-numbers/autodeploy.log`. Chỉ cần push lên `main`, không cần SSH.

**Mở từ ngoài mạng (tuỳ chọn):** Cloudflare Zero Trust → Networks → Tunnels → `mac-mcp` → Public Hostname →
thêm `flying-numbers.kntmcptools.online` → `HTTP` `localhost:<port>`.

**Gỡ:**

```bash
launchctl bootout gui/$(id -u)/com.flyingnumbers.server
rm ~/Library/LaunchAgents/com.flyingnumbers.server.plist
launchctl bootout gui/$(id -u)/com.flyingnumbers.autodeploy
rm ~/Library/LaunchAgents/com.flyingnumbers.autodeploy.plist
```

## Cấu trúc

- `index.html` — menu chọn game
- `khung-long-danh-van/index.html` — game đánh vần (HTML/CSS/JS, không cần build)
- `flying-numbers/index.html` — game số
- `deploy/server.py` — server Python thuần: phục vụ các trang + API bảng xếp hạng `/<game>/api/scores`
  (Flying Numbers giữ file `deploy/scores.json` cũ; Khủng long đánh vần lưu ở `deploy/scores-khung-long-danh-van.json`)
- `deploy/install-macmini.sh` — cài launchd service, tự chọn port trống
- `deploy/autodeploy.sh` — tự deploy `main` mỗi phút (`--install` để cài)
