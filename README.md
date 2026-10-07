# Flying Numbers 🦖

Game luyện nghe số tiếng Anh cho bé (tối ưu cho iPad). Máy đọc một số từ 1 đến 20, bé chạm đúng số khi nó bay qua.

- Chọn 5 hoặc 10 lượt, mỗi lượt sai tối đa 3 lần
- Số bị thẩy theo vòng cung từ dưới lên, trên xuống, hai bên
- Chạm khủng long: "Dinosaur mà"; chạm chữ **Will**: "Will í ẹ"; chạm chữ **Kem**: "Kem xinh đẹp" (kèm pháo hoa)
- Pause, chơi lại, đồng hồ, sao, bảng xếp hạng có điền tên

## Chạy trên Mac mini

```bash
git clone https://github.com/isucess/game-1.git ~/projects/flying-numbers
cd ~/projects/flying-numbers
bash deploy/install-macmini.sh        # tự chọn port trống từ 8090
bash deploy/autodeploy.sh --install   # tự deploy khi main có commit mới
```

Script in ra địa chỉ cho iPad cùng WiFi, ví dụ `http://192.168.1.20:8090`.
Service chạy bằng launchd, tự bật lại khi máy khởi động. Bảng xếp hạng chung lưu ở `deploy/scores.json`.

**Tự động deploy:** launchd chạy `deploy/autodeploy.sh` mỗi 1 phút. Có commit mới trên `main` → kéo về,
restart server nếu `deploy/server.py` đổi (chỉ sửa `index.html` thì không cần restart), kiểm tra `/health`.
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

- `index.html` — toàn bộ game (HTML/CSS/JS, không cần build)
- `deploy/server.py` — server Python thuần: phục vụ game + API `/api/scores`
- `deploy/install-macmini.sh` — cài launchd service, tự chọn port trống
- `deploy/autodeploy.sh` — tự deploy `main` mỗi phút (`--install` để cài)
