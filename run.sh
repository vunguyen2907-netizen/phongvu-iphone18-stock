#!/bin/bash
# =============================================================================
# KHỞI CHẠY TOÀN BỘ HỆ THỐNG TRA CỨU TỒN KHO & TẠO LỆNH CKNB PHONG VŨ
# =============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================================="
echo "🚀 ĐANG KHỞI ĐỘNG HỆ THỐNG TRA CỨU IPHONE 18 PHONG VŨ (VŨ AM)"
echo "=================================================================="

# 1. Khởi động Web Server cục bộ (Port 3108)
if ! lsof -i :3108 > /dev/null; then
    echo "➜ Đang chạy Realtime ERP Server trên port 3108..."
    python3 "$DIR/server.py" > "$DIR/server.log" 2>&1 &
    sleep 2
fi

# 2. Khởi động Cloudflare Tunnel tạo link Public
if ! pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "➜ Đang tạo đường dẫn Public qua Cloudflare..."
    "$DIR/cloudflared" tunnel --url http://localhost:3108 > "$DIR/tunnel.log" 2>&1 &
    sleep 3
fi

# 3. Lấy link public từ log
PUBLIC_URL=$(grep -o "https://[a-zA-Z0-9\-]*\.trycloudflare\.com" "$DIR/tunnel.log" | tail -n 1)

echo ""
echo "🎉 HỆ THỐNG ĐÃ HOẠT ĐỘNG THÀNH CÔNG!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 LINK PUBLIC TRUY CẬP TRÊN ĐIỆN THOẠI (BẤT KỲ ĐÂU):"
echo "👉 $PUBLIC_URL/index.html"
echo ""
echo "💻 Link Local (máy tính của bạn):"
echo "👉 http://localhost:3108/index.html"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Nhấn Ctrl+C bất cứ lúc nào nếu bạn muốn dừng."

# Chạy scheduler worker
python3 "$DIR/worker/scheduler.py"
