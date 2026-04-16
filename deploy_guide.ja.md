# AWS Lightsail デプロイガイド

[English version](deploy_guide.md)

## 1. Lightsail インスタンスの作成

1. [AWS Lightsail コンソール](https://lightsail.aws.amazon.com/) にログイン
2. 「Create instance」をクリック
3. 設定:
   - **Region**: 東京 (ap-northeast-1)
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only → **Ubuntu 22.04 LTS**
   - **Plan**: $3.50 USD/月（512MB RAM, 1 vCPU）で十分
   - **Instance name**: `kindle-highlights`
4. 「Create instance」で作成

## 2. ネットワーク設定

Lightsail コンソール → インスタンス → Networking:
- **HTTP (80)** を開放（デフォルトで開いているはず）
- **HTTPS (443)** を追加で開放
- **Custom TCP 8000** は不要（nginx 経由でアクセスするため）

## 3. （任意）ドメイン設定

独自ドメインがある場合:
- DNS の A レコードを Lightsail の Static IP に向ける
- Lightsail コンソールで Static IP を割り当てておく

ドメインなしでも IP アドレスで利用可能（ただし HTTPS は使えません）

## 4. SSH でログイン & セットアップ

```bash
# Lightsail コンソールの「Connect using SSH」か、ダウンロードした鍵を使用
ssh ubuntu@<インスタンスのIPアドレス>

# リポジトリを clone
git clone https://github.com/<your-username>/kindle-highlights-notion.git
cd kindle-highlights-notion

# セットアップスクリプトを実行
sudo bash deploy_setup.sh
```

## 5. .env を設定

```bash
sudo nano /opt/kindle-highlights/.env
```

以下を設定:
```
HOST=0.0.0.0
PORT=8000
BASE_URL=https://your-domain.com   # ドメインなしの場合: http://<IP>
BASIC_AUTH_USER=myuser
BASIC_AUTH_PASS=mysecretpassword
```

## 6. サービスを起動

```bash
sudo systemctl start kindle-highlights
sudo systemctl status kindle-highlights
```

## 7. HTTPS を設定（ドメインがある場合）

```bash
sudo certbot --nginx -d your-domain.com
```

certbot が自動で nginx の設定を更新し、SSL 証明書も自動更新されます。

## 8. 動作確認

```bash
# ローカルでテスト
curl http://localhost:8000

# 外部からブラウザでアクセス
# http://<IPアドレス> or https://your-domain.com
```

---

## 運用コマンド

```bash
# ログ確認
sudo journalctl -u kindle-highlights -f

# 再起動
sudo systemctl restart kindle-highlights

# 停止
sudo systemctl stop kindle-highlights

# コード更新
cd ~/kindle-highlights-notion
git pull
sudo cp server.py /opt/kindle-highlights/
sudo systemctl restart kindle-highlights

# データのバックアップ
sudo cp -r /opt/kindle-highlights/data ~/backup-data
```

## トラブルシューティング

### サービスが起動しない
```bash
sudo journalctl -u kindle-highlights --no-pager -n 50
```

### 502 Bad Gateway
- Python サーバーが起動しているか確認: `sudo systemctl status kindle-highlights`
- ポートを確認: `ss -tlnp | grep 8000`

### HTTPS 証明書の更新
certbot が自動更新しますが、手動で更新する場合:
```bash
sudo certbot renew
```
