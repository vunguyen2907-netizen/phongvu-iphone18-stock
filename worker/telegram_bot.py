#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
TELEGRAM BOT INTEGRATION: ADMIN APPROVAL FOR STOCK TRANSFER (CKNB)
=============================================================================
Bot Telegram nhận yêu cầu xin hàng từ Mobile Web, hiển thị nút Inline Keyboard:
[ ✅ Duyệt & Tạo Lệnh ERP ] | [ ❌ Từ Chối ]
Khi Admin bấm duyệt -> Kích hoạt ERP Bot tạo phiếu ST-xxxxxx và báo kết quả ngược lại.
"""

import os
import json
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime
from erp_bot import PhongVuErpBot

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "YOUR_CHAT_ID_HERE")


class TelegramApprovalBot:
    def __init__(self, token=TELEGRAM_BOT_TOKEN):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_transfer_request_to_admin(self, chat_id, request_data):
        """
        Gửi tin nhắn yêu cầu xin hàng đến Admin kèm nút bấm Duyệt / Từ chối
        """
        items_text = "\n".join([
            f"  • [{i['sku']}] {i['name']} (SL: <b>{i['qty']}</b>)"
            for i in request_data["items"]
        ])

        message_text = (
            f"🔔 <b>YÊU CẦU DUYỆT CHUYỂN KHO NỘI BỘ (CKNB)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 <b>Lộ trình:</b> CP01 (Kho 11001.01) ➔ <b>{request_data['target_showroom']}</b>\n"
            f"📦 <b>Loại hàng:</b> {request_data.get('transfer_type', 'Hàng bảo hành')}\n"
            f"📱 <b>Sản phẩm xin hàng:</b>\n{items_text}\n"
            f"📝 <b>Ghi chú:</b> <i>{request_data.get('notes', 'Hệ thống auto xin hàng Iphone 18 của VŨ AM')}</i>\n"
            f"⏰ <b>Thời gian:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Vui lòng bấm nút bên dưới để hệ thống tự động đăng nhập ERP tạo phiếu:</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Duyệt & Tạo Lệnh ERP", "callback_data": f"approve_{request_data['request_id']}"},
                    {"text": "❌ Từ Chối", "callback_data": f"reject_{request_data['request_id']}"}
                ]
            ]
        }

        return self._send_request("sendMessage", {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        })

    def notify_approval_success(self, chat_id, message_id, transfer_result):
        """
        Cập nhật lại tin nhắn khi đã tạo phiếu ST- thành công trên ERP
        """
        items_text = "\n".join([
            f"  • [{i['sku']}] {i['name']} (SL: <b>{i['qty']}</b>)"
            for i in transfer_result["items"]
        ])

        success_text = (
            f"🎉 <b>TẠO PHIẾU CHUYỂN KHO ERP THÀNH CÔNG!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 <b>Mã phiếu ST:</b> <code>{transfer_result['st_code']}</code>\n"
            f"🏢 <b>Lộ trình:</b> CP01 ➔ <b>{transfer_result['target_showroom']}</b>\n"
            f"📦 <b>Loại hàng:</b> Hàng bảo hành\n"
            f"📱 <b>Sản phẩm đã chuyển:</b>\n{items_text}\n"
            f"📝 <b>Ghi chú:</b> Hệ thống auto xin hàng Iphone 18 của VŨ AM\n"
            f"⏱️ <b>Hoàn tất lúc:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <i>Trạng thái: Đã gửi lệnh lên hệ thống ERP Phong Vũ.</i>"
        )

        return self._send_request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": success_text,
            "parse_mode": "HTML"
        })

    def _send_request(self, method, data):
        """Gửi HTTP POST request đến Telegram API"""
        url = f"{self.base_url}/{method}"
        try:
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=encoded_data, headers={"User-Agent": "PhongVuErpBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except Exception as e:
            print(f"! Telegram API Error: {e}")
            return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    print("=== TELEGRAM ADMIN APPROVAL BOT MODULE LOADED ===")
    print("Module sẵn sàng kết nối webhook hoặc polling khi có Bot Token.")
