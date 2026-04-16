#!/bin/bash
# Kindle Highlights → Notion: Lightsail セットアップスクリプト
#
# 使い方:
#   1. Lightsail で Ubuntu 22.04 インスタンスを作成
#   2. SSH でログイン
#   3. このリポジトリを clone
#   4. このスクリプトを実行: sudo bash deploy/setup.sh
#
# 前提: Ubuntu 22.04 LTS

set -e

APP_NAME="kindle-highlights"
APP_DIR="/opt/${APP_NAME}"
APP_USER="www-data"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================="
echo " Kindle Highlights → Notion: セットアップ"
echo "========================================="

# --- 1. システム更新 & 必要パッケージ ---
echo ""
echo "📦 パッケージをインストール中..."
apt-get update -qq
apt-get install -y -qq python3 nginx certbot python3-certbot-nginx

# --- 2. アプリ配置 ---
echo ""
echo "📁 アプリを ${APP_DIR} に配置..."
mkdir -p "${APP_DIR}"
cp "${REPO_DIR}/server.py" "${APP_DIR}/"

# .env が存在しなければテンプレートからコピー
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${REPO_DIR}/.env.example" "${APP_DIR}/.env"
    echo "⚠️  ${APP_DIR}/.env を編集してください（後述）"
fi

mkdir -p "${APP_DIR}/data"
mkdir -p "${APP_DIR}/static"
chown -R ${APP_USER}:${APP_USER} "${APP_DIR}"

# --- 3. systemd サービス ---
echo ""
echo "⚙️  systemd サービスを登録..."
cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=Kindle Highlights to Notion
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 ${APP_DIR}/server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${APP_NAME}

# --- 4. nginx 設定 ---
echo ""
echo "🌐 nginx を設定中..."
cat > /etc/nginx/sites-available/${APP_NAME} << 'NGINX'
server {
    listen 80;
    server_name _;

    # Let's Encrypt 認証用
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# --- 完了 ---
echo ""
echo "========================================="
echo " ✅ セットアップ完了!"
echo "========================================="
echo ""
echo "次のステップ:"
echo ""
echo "1. .env を編集:"
echo "   sudo nano ${APP_DIR}/.env"
echo "   ---"
echo "   HOST=0.0.0.0"
echo "   PORT=8000"
echo "   BASE_URL=https://your-domain.com"
echo "   BASIC_AUTH_USER=your-username"
echo "   BASIC_AUTH_PASS=your-password"
echo "   ---"
echo ""
echo "2. サービスを起動:"
echo "   sudo systemctl start ${APP_NAME}"
echo "   sudo systemctl status ${APP_NAME}"
echo ""
echo "3. HTTPS を設定 (ドメインがある場合):"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo "4. 動作確認:"
echo "   curl http://localhost:8000"
echo ""
