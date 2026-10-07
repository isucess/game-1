# Flying Numbers 🦖

Game luyện nghe số tiếng Anh cho bé (tối ưu cho iPad). Máy đọc một số từ 1 đến 20, bé chạm đúng số khi nó bay qua.

- Chọn 5 hoặc 10 lượt, mỗi lượt sai tối đa 3 lần
- Số bị thẩy theo vòng cung từ dưới lên, trên xuống, hai bên
- Khủng long kêu "rawr" khi chạm, chữ **Will** bay qua thì có pháo hoa
- Pause, chơi lại, đồng hồ, sao, bảng xếp hạng có điền tên

## Chạy trên Mac mini

```bash
git clone https://github.com/isucess/game-1.git ~/projects/flying-numbers
cd ~/projects/flying-numbers
bash deploy/install-macmini.sh        # tự chọn port trống từ 8090
```

Script in ra địa chỉ cho iPad cùng WiFi, ví dụ `http://192.168.1.20:8090`.
Service chạy bằng launchd, tự bật lại khi máy khởi động. Bảng xếp hạng chung lưu ở `deploy/scores.json`.

**Cập nhật:** `cd ~/projects/flying-numbers && git pull` (không cần restart).

**Mở từ ngoài mạng (tuỳ chọn):** Cloudflare Zero Trust → Networks → Tunnels → `mac-mcp` → Public Hostname →
thêm `flying-numbers.kntmcptools.online` → `HTTP` `localhost:<port>`.

**Gỡ:**

```bash
launchctl bootout gui/$(id -u)/com.flyingnumbers.server
rm ~/Library/LaunchAgents/com.flyingnumbers.server.plist
```

## Cấu trúc

- `index.html` — toàn bộ game (HTML/CSS/JS, không cần build)
- `deploy/server.py` — server Python thuần: phục vụ game + API `/api/scores`
- `deploy/install-macmini.sh` — cài launchd service, tự chọn port trống
