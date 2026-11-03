# 📢 Kanal post boti

Botga postlarni yuborasiz — bot ularni **navbatga** qo'yadi va siz belgilagan
vaqtlarda kanalga **o'zi joylaydi**.

## Imkoniyatlar
- Matn, rasm, video, GIF, fayl, audio, ovozli xabar, **albom**, stiker, so'rovnoma — hammasi qabul qilinadi
- Formatlash (qalin, kursiv, havola, spoiler) saqlanadi; forward qilingan postlar ham ishlaydi
- Har kuni belgilangan vaqtlarda (`/vaqt 09:00 13:00 18:00`) va har vaqtda N ta (`/son 2`) post chiqaradi
- Istalgan postni aniq sanaga qo'yish: `/reja 12 05.11 14:00`
- Har post ostiga **imzo** (`/imzo 👉 @kanal`) va **tugma** (`/tugma Obuna | https://t.me/kanal`)
- Navbatni ko'rish, postni oldindan ko'rish, o'chirish, darhol joylash, pauza
- Navbat tugay deganda adminni ogohlantiradi

## O'rnatish
1. Botni kanalga **admin** qilib qo'shing ("Post joylash" huquqi bilan).
2. Serverda:
   ```bash
   cd channel_bot
   pip install -r requirements.txt
   cp .env.example .env     # BOT_TOKEN va ADMIN_IDS ni yozing
   python bot.py
   ```
3. Botga `/start` yozing, keyin `/kanal @kanal_nomi`.

`ADMIN_IDS` bo'sh qoldirilsa, botga birinchi `/start` bosgan odam admin bo'ladi.
O'z ID'ingizni bilish uchun botga `/id` yozing.

## Doimiy ishlashi uchun (Linux, systemd)
```ini
# /etc/systemd/system/channel-bot.service
[Unit]
Description=Kanal post boti
After=network.target

[Service]
WorkingDirectory=/opt/ads/channel_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now channel-bot
```

Postlar `posts.db` (SQLite) faylida saqlanadi — bot qayta ishga tushsa ham navbat yo'qolmaydi.
