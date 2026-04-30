"""Kindle Highlights → Notion: Python HTTP サーバー

起動方法: python server.py
設定: .env ファイルに記述（.env.example を参照）

初回起動時に static/ ディレクトリと HTML/CSS/JS ファイルを自動生成します。
"""

import http.server
import json
import os
import hashlib
import base64
import urllib.request
import urllib.error
from urllib.parse import urlparse


# ============================================================
# 設定（.env ファイルから読み込み）
# ============================================================
def load_env(filepath):
    """シンプルな .env パーサー（標準ライブラリのみ）"""
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # 環境変数が未設定の場合のみ .env の値を使う
            if key not in os.environ:
                os.environ[key] = value


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_env(os.path.join(BASE_DIR, '.env'))

HOST = os.environ.get('HOST', 'localhost')
PORT = int(os.environ.get('PORT', '8000'))
BASE_URL = os.environ.get('BASE_URL', '')  # 例: https://example.com（末尾スラッシュなし）
BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER', '')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS', '')

STATIC_DIR = os.path.join(BASE_DIR, 'static')
DATA_DIR = os.path.join(BASE_DIR, 'data')
HIGHLIGHTS_FILE = os.path.join(DATA_DIR, 'highlights.json')
SENT_FILE = os.path.join(DATA_DIR, 'sent.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


def get_base_url():
    """ブックマークレット等で使うベース URL を返す"""
    if BASE_URL:
        return BASE_URL
    if HOST == '0.0.0.0' or HOST == '':
        return f'http://localhost:{PORT}'
    return f'http://{HOST}:{PORT}'


# ============================================================
# ブックマークレット（Kindle Notebook ページ用）
# ============================================================
BOOKMARKLET_JS = r"""
(function(){
  try {
    var highlights = [];

    /* --- 書名・著者を取得 --- */
    var titleEl =
      document.querySelector('h3.kp-notebook-searchable') ||
      document.querySelector('.kp-notebook-cover-title-text') ||
      document.querySelector('#annotation-scroller h3') ||
      document.querySelector('h1');
    var authorEl =
      document.querySelector('p.kp-notebook-searchable') ||
      document.querySelector('.kp-notebook-cover-author-text') ||
      document.querySelector('#annotation-scroller p.a-color-secondary');

    var bookTitle = titleEl ? titleEl.textContent.trim() : '';
    var author = authorEl ? authorEl.textContent.trim() : '';

    /* --- 各ハイライトを抽出 --- */
    var rows = document.querySelectorAll('#kp-notebook-annotations .a-spacing-base');
    if (!rows.length) {
      rows = document.querySelectorAll('#kp-notebook-annotations > div > div');
    }

    rows.forEach(function(row) {
      var hlEl = row.querySelector('[id^="highlight-"]') ||
                 row.querySelector('.kp-notebook-highlight span');
      if (!hlEl) return;

      var text = hlEl.textContent.trim();
      if (!text) return;

      /* 位置情報 */
      var locEl = row.querySelector('[id^="annotationNoteHeader"]') ||
                  row.querySelector('.kp-notebook-metadata');
      var location = locEl ? locEl.textContent.trim().replace(/^\s+|\s+$/g,'') : '';

      /* メモ */
      var noteEl = row.querySelector('[id^="note-"]');
      var note = noteEl ? noteEl.textContent.trim() : '';

      /* ハイライト色 */
      var color = 'yellow';
      var colorEl = row.querySelector('[id^="annotationHighlightHeader"]') ||
                    row.querySelector('[class*="kp-notebook-highlight-"]');
      if (colorEl) {
        var cls = colorEl.className || '';
        var txt = colorEl.textContent || '';
        if (cls.indexOf('blue') !== -1 || txt.indexOf('blue') !== -1 || txt.indexOf('青') !== -1) color = 'blue';
        else if (cls.indexOf('pink') !== -1 || txt.indexOf('pink') !== -1 || txt.indexOf('ピンク') !== -1) color = 'pink';
        else if (cls.indexOf('orange') !== -1 || txt.indexOf('orange') !== -1 || txt.indexOf('オレンジ') !== -1) color = 'orange';
      }

      highlights.push({
        bookTitle: bookTitle,
        author: author,
        text: text,
        location: location,
        note: note,
        color: color
      });
    });

    if (highlights.length === 0) {
      alert('ハイライトが見つかりませんでした。\n本を選択してからもう一度お試しください。');
      return;
    }

    /* --- サーバーに送信 --- */
    var headers = { 'Content-Type': 'application/json' };
    AUTH_HEADER_PLACEHOLDER

    fetch('BASE_URL_PLACEHOLDER/api/highlights', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ highlights: highlights })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      alert('取得完了!\n新規: ' + d.new + ' 件 / 合計: ' + d.total + ' 件\n\nBASE_URL_PLACEHOLDER を開いて確認してください');
    })
    .catch(function(e) {
      alert('送信エラー: ' + e.message + '\n\nサーバー (python server.py) が起動しているか確認してください');
    });

  } catch(e) {
    alert('エラー: ' + e.message);
  }
})();
""".strip()


def get_bookmarklet_code():
    """ブックマークレット用の minified コードを返す"""
    import re
    code = BOOKMARKLET_JS.replace('BASE_URL_PLACEHOLDER', get_base_url())

    # Basic 認証ヘッダーを埋め込む
    if BASIC_AUTH_USER:
        cred = base64.b64encode(
            f'{BASIC_AUTH_USER}:{BASIC_AUTH_PASS}'.encode()
        ).decode()
        auth_line = f"headers['Authorization'] = 'Basic {cred}';"
    else:
        auth_line = ''
    code = code.replace('AUTH_HEADER_PLACEHOLDER', auth_line)

    # 簡易 minify: コメント除去、余分な空白を詰める
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'\s+', ' ', code)
    code = code.strip()
    return 'javascript:' + urllib.request.quote(code, safe="(){}[];:,.'\"=+!&|?/<>-*%$@#~ ")


# ============================================================
# 静的ファイル内容（初回起動時に static/ に書き出し）
# ============================================================

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kindle Highlights → Notion</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <div class="lang-switcher">
      <button id="lang-btn" class="btn btn-small" onclick="toggleLang()">English</button>
    </div>
    <h1>📚 Kindle Highlights → Notion</h1>
    <p class="subtitle" data-i18n="subtitle"></p>
  </header>

  <main>
    <section class="card" id="config-section">
      <h2 data-i18n="config_title"></h2>
      <div class="form-group">
        <label for="notion-token" data-i18n="config_token_label"></label>
        <input type="password" id="notion-token" placeholder="secret_xxxxxxxxxxxx">
        <small data-i18n-html="config_token_help"></small>
      </div>
      <div class="form-group">
        <label for="database-id" data-i18n="config_db_label"></label>
        <input type="text" id="database-id" placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx">
        <small data-i18n-html="config_db_help"></small>
      </div>
      <button id="save-config-btn" class="btn btn-primary" data-i18n="config_save"></button>
      <button id="test-notion-btn" class="btn btn-secondary" data-i18n="config_test"></button>
      <span id="config-status" class="status"></span>
      <div id="test-result" class="test-result" style="display:none;"></div>
    </section>

    <section class="card" id="bookmarklet-section">
      <h2 data-i18n="bm_title"></h2>
      <p data-i18n="bm_desc"></p>
      <div class="bookmarklet-container">
        <a id="bookmarklet-link" class="bookmarklet-btn" href="#" data-i18n="bm_button"></a>
      </div>
      <details>
        <summary data-i18n="bm_manual_summary"></summary>
        <p data-i18n="bm_manual_desc"></p>
        <textarea id="bookmarklet-code" readonly rows="4"></textarea>
        <button id="copy-bookmarklet-btn" class="btn btn-small" data-i18n="bm_copy"></button>
      </details>
    </section>

    <section class="card" id="usage-section">
      <h2 data-i18n="usage_title"></h2>
      <ol id="usage-steps"></ol>
      <button id="refresh-btn" class="btn btn-secondary" data-i18n="usage_refresh"></button>
    </section>

    <section class="card" id="highlights-section" style="display:none;">
      <h2><span data-i18n="hl_title"></span> <span id="highlight-count" class="badge">0</span></h2>
      <div class="highlight-controls">
        <label><input type="checkbox" id="select-all" checked> <span data-i18n="hl_select_all"></span></label>
        <label><input type="checkbox" id="hide-sent"> <span data-i18n="hl_hide_sent"></span></label>
        <button id="send-btn" class="btn btn-primary" data-i18n="hl_send"></button>
      </div>
      <div id="highlights-list"></div>
      <div id="send-status" class="status"></div>
      <div id="error-details" class="error-details" style="display:none;">
        <h3 data-i18n="error_title"></h3>
        <div id="error-list"></div>
      </div>
    </section>

    <section class="card" id="manual-section">
      <h2 data-i18n="manual_title"></h2>
      <details>
        <summary data-i18n="manual_summary"></summary>
        <div class="form-group">
          <label for="manual-book" data-i18n="manual_book"></label>
          <input type="text" id="manual-book">
        </div>
        <div class="form-group">
          <label for="manual-author" data-i18n="manual_author"></label>
          <input type="text" id="manual-author">
        </div>
        <div class="form-group">
          <label for="manual-text" data-i18n="manual_text_label"></label>
          <textarea id="manual-text" rows="6"></textarea>
        </div>
        <button id="manual-add-btn" class="btn btn-secondary" data-i18n="manual_add"></button>
      </details>
    </section>

    <section class="card" id="backup-section">
      <h2 data-i18n="backup_title"></h2>
      <p data-i18n="backup_desc"></p>
      <div class="backup-controls">
        <button id="backup-btn" class="btn btn-primary" data-i18n="backup_download"></button>
        <button id="restore-btn" class="btn btn-secondary" data-i18n="backup_restore" onclick="document.getElementById('restore-input').click()"></button>
        <input type="file" id="restore-input" accept=".json" style="display:none;">
      </div>
      <div id="backup-status" class="status"></div>
    </section>
  </main>

  <footer>
    <p data-i18n-html="footer_text"></p>
  </footer>

  <script src="app.js"></script>
</body>
</html>
"""

STYLE_CSS = r"""/* === 基本レイアウト === */
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f7;
  color: #333;
  line-height: 1.6;
  padding: 1rem;
  max-width: 900px;
  margin: 0 auto;
}

header {
  text-align: center;
  padding: 2rem 0 1rem;
  position: relative;
}
header h1 { font-size: 1.8rem; }
.subtitle { color: #666; margin-top: 0.3rem; }
.lang-switcher { position: absolute; top: 1rem; right: 0; }

/* === カード === */
.card {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.card h2 { font-size: 1.2rem; margin-bottom: 1rem; }

/* === フォーム === */
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-weight: 600; margin-bottom: 0.3rem; }
.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
}
.form-group small { display: block; color: #888; margin-top: 0.3rem; font-size: 0.8rem; }
.form-group small a { color: #0066cc; }
.form-group code { background: #f0f0f0; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.85em; }

/* === ボタン === */
.btn {
  display: inline-block;
  padding: 0.5rem 1.2rem;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn:hover { opacity: 0.85; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #0066cc; color: #fff; }
.btn-secondary { background: #e8e8ed; color: #333; }
.btn-small { font-size: 0.8rem; padding: 0.3rem 0.8rem; }

/* === ブックマークレット === */
.bookmarklet-container { text-align: center; margin: 1rem 0; }
.bookmarklet-btn {
  display: inline-block;
  padding: 0.7rem 2rem;
  background: linear-gradient(135deg, #ff9500, #ff6b00);
  color: #fff;
  font-size: 1.1rem;
  font-weight: 700;
  text-decoration: none;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(255,149,0,0.3);
  cursor: grab;
}
.bookmarklet-btn:hover { box-shadow: 0 4px 12px rgba(255,149,0,0.5); }

details { margin-top: 1rem; }
details summary { cursor: pointer; color: #0066cc; font-size: 0.9rem; }
details textarea { margin-top: 0.5rem; font-family: monospace; font-size: 0.75rem; }

/* === ステータス === */
.status { display: inline-block; margin-left: 0.5rem; font-size: 0.9rem; }
.status.ok { color: #34c759; }
.status.error { color: #ff3b30; }
.status.info { color: #007aff; }

/* === バッジ === */
.badge {
  display: inline-block;
  background: #007aff;
  color: #fff;
  font-size: 0.8rem;
  padding: 0.1rem 0.6rem;
  border-radius: 10px;
  vertical-align: middle;
}

/* === ハイライト一覧 === */
.highlight-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.highlight-controls label { font-size: 0.9rem; cursor: pointer; }

.highlight-item {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 0.8rem;
  margin-bottom: 0.5rem;
  display: flex;
  gap: 0.8rem;
  align-items: flex-start;
  transition: opacity 0.2s;
}
.highlight-item.sent { opacity: 0.5; }
.highlight-item.hidden { display: none; }
.highlight-item input[type="checkbox"] { margin-top: 0.3rem; flex-shrink: 0; }

.hl-content { flex: 1; min-width: 0; }
.hl-text { font-size: 0.95rem; margin-bottom: 0.3rem; }
.hl-meta { font-size: 0.8rem; color: #888; }
.hl-meta span { margin-right: 0.8rem; }
.hl-note { font-size: 0.85rem; color: #555; font-style: italic; margin-top: 0.2rem; }

.color-dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
  margin-right: 0.3rem;
  vertical-align: middle;
}
.color-dot.yellow { background: #ffcc02; }
.color-dot.blue { background: #007aff; }
.color-dot.pink { background: #ff2d55; }
.color-dot.orange { background: #ff9500; }

/* === フッター === */
footer {
  text-align: center;
  padding: 2rem 0;
  color: #999;
  font-size: 0.8rem;
}
footer code { background: #eee; padding: 0.1rem 0.3rem; border-radius: 3px; }

/* === エラー詳細 === */
.error-details {
  margin-top: 1rem;
  padding: 1rem;
  background: #fff5f5;
  border: 1px solid #ffcccc;
  border-radius: 8px;
}
.error-details h3 { font-size: 1rem; margin-bottom: 0.5rem; color: #cc0000; }
.error-item {
  padding: 0.5rem;
  margin-bottom: 0.4rem;
  background: #fff;
  border: 1px solid #ffe0e0;
  border-radius: 4px;
  font-size: 0.85rem;
  font-family: monospace;
  word-break: break-all;
  white-space: pre-wrap;
}

/* === 接続テスト結果 === */
.test-result {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  line-height: 1.8;
}
.test-result.success { background: #f0fff4; border: 1px solid #c6f6d5; }
.test-result.warning { background: #fffff0; border: 1px solid #fefcbf; }
.test-result.fail { background: #fff5f5; border: 1px solid #ffcccc; }

/* === ol === */
ol { padding-left: 1.5rem; }
ol li { margin-bottom: 0.5rem; }

/* === バックアップ === */
.backup-controls {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}
"""

APP_JS = r"""/* Kindle Highlights → Notion */

const API = '';

// ============================================================
// i18n
// ============================================================
const I18N = {
  ja: {
    subtitle: 'Kindle のハイライトを Notion データベースに送信',
    config_title: '⚙️ Step 1: Notion 設定',
    config_token_label: 'Notion API キー (Internal Integration Token)',
    config_token_help: '<a href="https://www.notion.so/my-integrations" target="_blank">Notion Integrations</a> で Internal Integration を作成しトークンを貼り付けてください',
    config_db_label: 'Notion データベース ID',
    config_db_help: '<strong>取得方法:</strong> Notion で<strong>データベース</strong>（テーブルビュー）を開き「Share」→「Copy link」で URL 中の ID（32文字）をコピー。<br>例: <code>https://www.notion.so/<strong>DB ID</strong>?v=...</code><br>⚠️ ページ ID ではなく<strong>データベース ID</strong> を入力。<br>推奨プロパティ: <code>Name</code>(title), <code>Book</code>(text), <code>Author</code>(text), <code>Location</code>(text), <code>Color</code>(select)',
    config_save: '設定を保存',
    config_test: '🔍 接続テスト',
    config_saved: '✅ 保存しました',
    config_testing: '🔍 テスト中...',
    bm_title: '🔖 Step 2: ブックマークレットを登録',
    bm_desc: '下のボタンをブックマークバーにドラッグ＆ドロップしてください：',
    bm_button: '📖 Kindle→取得',
    bm_manual_summary: '手動で登録する場合',
    bm_manual_desc: '新しいブックマークを作成し、URL 欄に以下を貼り付け：',
    bm_copy: '📋 コピー',
    bm_copied: '✅ コピー済み',
    usage_title: '📋 Step 3: 使い方',
    usage_steps: [
      'このサーバーを起動（<code>python server.py</code>）',
      '<a href="https://read.amazon.co.jp/notebook" target="_blank">Kindle ノートブック</a> を開き対象の本を選択',
      'ブックマークレット「📖 Kindle→取得」をクリック',
      'この画面に戻り確認 → Notion に送信'
    ],
    usage_refresh: '🔄 ハイライトを更新',
    hl_title: '📝 取得済みハイライト',
    hl_select_all: 'すべて選択',
    hl_hide_sent: '送信済みを非表示',
    hl_send: '🚀 Notion に送信',
    hl_sending: '送信中...',
    hl_sent_label: '✅ 送信済み',
    hl_no_selection: '⚠️ ハイライトを選択してください',
    hl_sending_status: '⏳ 送信中...',
    hl_sent_count: (n) => `✅ 送信: ${n} 件`,
    hl_skipped_count: (n) => ` / スキップ: ${n} 件`,
    hl_error_count: (n) => ` / エラー: ${n} 件`,
    error_title: '⚠️ エラー詳細',
    manual_title: '✏️ 手動入力（オプション）',
    manual_summary: 'ブックマークレットが動かない場合はこちら',
    manual_book: '書名',
    manual_author: '著者',
    manual_text_label: 'ハイライト（1行1件）',
    manual_add: '追加',
    manual_need_input: '書名とハイライトを入力してください',
    manual_done: (n, t) => `追加完了: 新規 ${n} 件 / 合計 ${t} 件`,
    footer_text: 'ローカル専用ツール — データは <code>data/</code> に保存されます',
    test_fail: '❌ 接続失敗',
    test_ok: '✅ 接続成功',
    test_db: 'DB',
    test_untitled: '(無題)',
    test_props: 'DB プロパティ一覧',
    test_comm_error: '❌ 通信エラー',
    comm_error: '❌ 通信エラー',
    lang_toggle: 'English',
    api_key_missing: 'Notion API キーまたは DB ID が未設定です',
    backup_title: '💾 バックアップ / リストア',
    backup_desc: 'ハイライト・送信履歴・設定・.env をまとめてバックアップ・リストアできます。',
    backup_download: '📥 バックアップをダウンロード',
    backup_restore: '📤 バックアップからリストア',
    backup_confirm: 'バックアップからリストアすると、現在のデータが上書きされます。続行しますか？',
    backup_restored: (items) => `✅ リストア完了: ${items}`,
    backup_invalid: '❌ 無効なバックアップファイルです',
    backup_error: '❌ リストアエラー'
  },
  en: {
    subtitle: 'Send Kindle highlights to your Notion database',
    config_title: '⚙️ Step 1: Notion Settings',
    config_token_label: 'Notion API Key (Internal Integration Token)',
    config_token_help: 'Create an Internal Integration at <a href="https://www.notion.so/my-integrations" target="_blank">Notion Integrations</a> and paste the token here',
    config_db_label: 'Notion Database ID',
    config_db_help: '<strong>How to get it:</strong> Open a <strong>database</strong> (table view) in Notion, click "Share" → "Copy link", and copy the 32-char ID from the URL.<br>Example: <code>https://www.notion.so/<strong>DB ID here</strong>?v=...</code><br>⚠️ Use the <strong>database ID</strong>, not a page ID.<br>Recommended properties: <code>Name</code>(title), <code>Book</code>(text), <code>Author</code>(text), <code>Location</code>(text), <code>Color</code>(select)',
    config_save: 'Save Settings',
    config_test: '🔍 Test Connection',
    config_saved: '✅ Saved',
    config_testing: '🔍 Testing...',
    bm_title: '🔖 Step 2: Register Bookmarklet',
    bm_desc: 'Drag & drop the button below to your bookmarks bar:',
    bm_button: '📖 Kindle→Fetch',
    bm_manual_summary: 'Register manually',
    bm_manual_desc: 'Create a new bookmark and paste the following into the URL field:',
    bm_copy: '📋 Copy',
    bm_copied: '✅ Copied',
    usage_title: '📋 Step 3: How to Use',
    usage_steps: [
      'Start this server (<code>python server.py</code>)',
      'Open <a href="https://read.amazon.co.jp/notebook" target="_blank">Kindle Notebook</a> and select a book',
      'Click the bookmarklet "📖 Kindle→Fetch"',
      'Return to this page to review → Send to Notion'
    ],
    usage_refresh: '🔄 Refresh Highlights',
    hl_title: '📝 Saved Highlights',
    hl_select_all: 'Select All',
    hl_hide_sent: 'Hide Sent',
    hl_send: '🚀 Send to Notion',
    hl_sending: 'Sending...',
    hl_sent_label: '✅ Sent',
    hl_no_selection: '⚠️ Please select highlights',
    hl_sending_status: '⏳ Sending...',
    hl_sent_count: (n) => `✅ Sent: ${n}`,
    hl_skipped_count: (n) => ` / Skipped: ${n}`,
    hl_error_count: (n) => ` / Errors: ${n}`,
    error_title: '⚠️ Error Details',
    manual_title: '✏️ Manual Input (Optional)',
    manual_summary: 'Use this if the bookmarklet does not work',
    manual_book: 'Book Title',
    manual_author: 'Author',
    manual_text_label: 'Highlights (one per line)',
    manual_add: 'Add',
    manual_need_input: 'Please enter the book title and highlights',
    manual_done: (n, t) => `Added: ${n} new / ${t} total`,
    footer_text: 'Local tool — data is stored in <code>data/</code>',
    test_fail: '❌ Connection Failed',
    test_ok: '✅ Connection Successful',
    test_db: 'DB',
    test_untitled: '(Untitled)',
    test_props: 'DB Properties',
    test_comm_error: '❌ Communication Error',
    comm_error: '❌ Communication Error',
    lang_toggle: '日本語',
    api_key_missing: 'Notion API key or Database ID is not set',
    backup_title: '💾 Backup / Restore',
    backup_desc: 'Backup and restore your highlights, send history, config, and .env all at once.',
    backup_download: '📥 Download Backup',
    backup_restore: '📤 Restore from Backup',
    backup_confirm: 'Restoring from backup will overwrite current data. Continue?',
    backup_restored: (items) => `✅ Restore complete: ${items}`,
    backup_invalid: '❌ Invalid backup file',
    backup_error: '❌ Restore error'
  }
};

let currentLang = localStorage.getItem('lang') || 'ja';

function t(key) {
  return I18N[currentLang][key] || I18N['ja'][key] || key;
}

function toggleLang() {
  currentLang = currentLang === 'ja' ? 'en' : 'ja';
  localStorage.setItem('lang', currentLang);
  applyI18n();
}

function applyI18n() {
  document.documentElement.lang = currentLang;
  document.getElementById('lang-btn').textContent = t('lang_toggle');

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (typeof val === 'string') el.textContent = val;
  });

  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    const val = t(key);
    if (typeof val === 'string') el.innerHTML = val;
  });

  // Usage steps
  const stepsEl = document.getElementById('usage-steps');
  if (stepsEl) {
    const steps = t('usage_steps');
    if (Array.isArray(steps)) {
      stepsEl.innerHTML = steps.map(s => `<li>${s}</li>`).join('');
    }
  }

  renderHighlights();
}

// --- DOM Elements ---
const $notionToken = document.getElementById('notion-token');
const $databaseId = document.getElementById('database-id');
const $saveConfigBtn = document.getElementById('save-config-btn');
const $testNotionBtn = document.getElementById('test-notion-btn');
const $configStatus = document.getElementById('config-status');
const $testResult = document.getElementById('test-result');
const $bookmarkletLink = document.getElementById('bookmarklet-link');
const $bookmarkletCode = document.getElementById('bookmarklet-code');
const $copyBookmarkletBtn = document.getElementById('copy-bookmarklet-btn');
const $refreshBtn = document.getElementById('refresh-btn');
const $highlightsSection = document.getElementById('highlights-section');
const $highlightCount = document.getElementById('highlight-count');
const $highlightsList = document.getElementById('highlights-list');
const $selectAll = document.getElementById('select-all');
const $hideSent = document.getElementById('hide-sent');
const $sendBtn = document.getElementById('send-btn');
const $sendStatus = document.getElementById('send-status');
const $errorDetails = document.getElementById('error-details');
const $errorList = document.getElementById('error-list');
const $manualBook = document.getElementById('manual-book');
const $manualAuthor = document.getElementById('manual-author');
const $manualText = document.getElementById('manual-text');
const $manualAddBtn = document.getElementById('manual-add-btn');
const $backupBtn = document.getElementById('backup-btn');
const $restoreInput = document.getElementById('restore-input');
const $backupStatus = document.getElementById('backup-status');

let highlights = [];

// --- Init ---
async function init() {
  applyI18n();
  await loadConfig();
  await loadBookmarklet();
  await loadHighlights();
}

// --- Config ---
async function loadConfig() {
  try {
    const res = await fetch(API + '/api/config');
    const config = await res.json();
    if (config.notion_token) $notionToken.value = config.notion_token;
    if (config.database_id) $databaseId.value = config.database_id;
  } catch (e) {
    console.error('Config load failed:', e);
  }
}

async function saveConfig() {
  const config = {
    notion_token: $notionToken.value.trim(),
    database_id: $databaseId.value.trim().replace(/-/g, '')
  };
  try {
    await fetch(API + '/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    showStatus($configStatus, t('config_saved'), 'ok');
  } catch (e) {
    showStatus($configStatus, '❌ ' + e.message, 'error');
  }
}

// --- Test Connection ---
async function testNotion() {
  $testNotionBtn.disabled = true;
  $testNotionBtn.textContent = t('config_testing');
  $testResult.style.display = 'none';
  await saveConfig();

  try {
    const res = await fetch(API + '/api/test-notion', { method: 'POST' });
    const data = await res.json();

    if (data.error) {
      $testResult.className = 'test-result fail';
      let msg = `<strong>${t('test_fail')}</strong><br>`;
      const jsonMatch = data.error.match(/Notion API error (\d+): (.+)/s);
      if (jsonMatch) {
        try {
          const parsed = JSON.parse(jsonMatch[2]);
          msg += `Notion API ${jsonMatch[1]}: ${escapeHtml(parsed.message || parsed.code || '')}`;
        } catch (_) { msg += escapeHtml(data.error); }
      } else {
        msg += escapeHtml(data.error);
      }
      $testResult.innerHTML = msg;
    } else {
      const hasMissing = data.missing && data.missing.length > 0;
      $testResult.className = 'test-result ' + (hasMissing ? 'warning' : 'success');
      let msg = `<strong>${t('test_ok')}</strong>`;
      msg += ` — ${t('test_db')}: ${escapeHtml(data.database_title || t('test_untitled'))}<br><br>`;
      if (data.found && data.found.length > 0) {
        msg += data.found.map(f => escapeHtml(f)).join('<br>');
      }
      if (hasMissing) {
        msg += '<br><br>';
        msg += data.missing.map(m => escapeHtml(m)).join('<br>');
      }
      msg += `<br><br><strong>${t('test_props')}:</strong><br>`;
      for (const [name, type] of Object.entries(data.properties || {})) {
        msg += `• ${escapeHtml(name)} (${escapeHtml(type)})<br>`;
      }
      $testResult.innerHTML = msg;
    }
    $testResult.style.display = '';
  } catch (e) {
    $testResult.className = 'test-result fail';
    $testResult.innerHTML = `<strong>${t('test_comm_error')}</strong><br>${escapeHtml(e.message)}`;
    $testResult.style.display = '';
  } finally {
    $testNotionBtn.disabled = false;
    $testNotionBtn.textContent = t('config_test');
  }
}

// --- Bookmarklet ---
async function loadBookmarklet() {
  try {
    const res = await fetch(API + '/api/bookmarklet');
    const data = await res.json();
    $bookmarkletLink.href = data.code;
    $bookmarkletCode.value = data.code;
  } catch (e) {
    console.error('Bookmarklet load failed:', e);
  }
}

// --- Highlights ---
async function loadHighlights() {
  try {
    const res = await fetch(API + '/api/highlights');
    highlights = await res.json();
    renderHighlights();
  } catch (e) {
    console.error('Highlights load failed:', e);
  }
}

function renderHighlights() {
  if (highlights.length === 0) {
    $highlightsSection.style.display = 'none';
    return;
  }
  $highlightsSection.style.display = '';
  $highlightCount.textContent = highlights.length;
  const hideSent = $hideSent.checked;

  $highlightsList.innerHTML = highlights.map((h, i) => {
    const sentClass = h._sent ? 'sent' : '';
    const hiddenClass = (h._sent && hideSent) ? 'hidden' : '';
    return `
      <div class="highlight-item ${sentClass} ${hiddenClass}" data-index="${i}">
        <input type="checkbox" class="hl-check" data-index="${i}" ${h._sent ? '' : 'checked'}>
        <div class="hl-content">
          <div class="hl-text">${escapeHtml(h.text)}</div>
          ${h.note ? '<div class="hl-note">📝 ' + escapeHtml(h.note) + '</div>' : ''}
          <div class="hl-meta">
            <span><span class="color-dot ${h.color || 'yellow'}"></span>${escapeHtml(h.color || 'yellow')}</span>
            <span>📖 ${escapeHtml(h.bookTitle || '')}</span>
            <span>✍️ ${escapeHtml(h.author || '')}</span>
            ${h.location ? '<span>📍 ' + escapeHtml(h.location) + '</span>' : ''}
            ${h._sent ? '<span>' + t('hl_sent_label') + '</span>' : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// --- Send to Notion ---
async function sendToNotion() {
  const checkboxes = document.querySelectorAll('.hl-check:checked');
  const selected = Array.from(checkboxes).map(cb => highlights[parseInt(cb.dataset.index)]);

  if (selected.length === 0) {
    showStatus($sendStatus, t('hl_no_selection'), 'error');
    return;
  }

  $sendBtn.disabled = true;
  $sendBtn.textContent = t('hl_sending');
  showStatus($sendStatus, t('hl_sending_status'), 'info');
  hideErrors();

  try {
    const res = await fetch(API + '/api/send-to-notion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ highlights: selected })
    });
    const data = await res.json();

    if (data.error) {
      showStatus($sendStatus, '❌ ' + data.error, 'error');
      showErrors([data.error]);
    } else {
      let msg = t('hl_sent_count')(data.sent);
      if (data.skipped > 0) msg += t('hl_skipped_count')(data.skipped);
      if (data.errors && data.errors.length > 0) {
        msg += t('hl_error_count')(data.errors.length);
        showErrors(data.errors);
      }
      showStatus($sendStatus, msg, data.errors && data.errors.length > 0 ? 'error' : 'ok');
      await loadHighlights();
    }
  } catch (e) {
    showStatus($sendStatus, t('comm_error') + ': ' + e.message, 'error');
    showErrors([e.message]);
  } finally {
    $sendBtn.disabled = false;
    $sendBtn.textContent = t('hl_send');
  }
}

// --- Manual Input ---
async function addManual() {
  const bookTitle = $manualBook.value.trim();
  const author = $manualAuthor.value.trim();
  const text = $manualText.value.trim();

  if (!bookTitle || !text) {
    alert(t('manual_need_input'));
    return;
  }

  const lines = text.split('\n').filter(l => l.trim());
  const newHighlights = lines.map(line => ({
    bookTitle, author, text: line.trim(), location: '', note: '', color: 'yellow'
  }));

  try {
    const res = await fetch(API + '/api/highlights', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ highlights: newHighlights })
    });
    const data = await res.json();
    alert(t('manual_done')(data.new, data.total));
    $manualText.value = '';
    await loadHighlights();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

// --- Backup / Restore ---
async function downloadBackup() {
  showStatus($backupStatus, '⏳...', '');
  try {
    const res = await fetch(API + '/api/backup');
    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    const match = cd.match(/filename="?(.+?)"?$/);
    const filename = match ? match[1] : 'backup.json';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
    showStatus($backupStatus, '✅', 'ok');
  } catch (e) {
    showStatus($backupStatus, '❌ ' + e.message, 'error');
  }
}

async function restoreBackup(file) {
  if (!confirm(t('backup_confirm'))) return;
  showStatus($backupStatus, '⏳...', '');
  try {
    const text = await file.text();
    const data = JSON.parse(text);
    if (!data.version) { showStatus($backupStatus, t('backup_invalid'), 'error'); return; }
    const res = await fetch(API + '/api/restore', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: text
    });
    const result = await res.json();
    if (result.error) {
      showStatus($backupStatus, t('backup_error') + ': ' + result.error, 'error');
    } else {
      showStatus($backupStatus, t('backup_restored')(result.restored.join(', ')), 'ok');
      await loadConfig();
      await loadHighlights();
    }
  } catch (e) {
    showStatus($backupStatus, t('backup_error') + ': ' + e.message, 'error');
  }
  $restoreInput.value = '';
}

// --- Events ---
$saveConfigBtn.addEventListener('click', saveConfig);
$testNotionBtn.addEventListener('click', testNotion);
$refreshBtn.addEventListener('click', loadHighlights);
$sendBtn.addEventListener('click', sendToNotion);
$manualAddBtn.addEventListener('click', addManual);
$backupBtn.addEventListener('click', downloadBackup);
$restoreInput.addEventListener('change', (e) => {
  if (e.target.files[0]) restoreBackup(e.target.files[0]);
});

$selectAll.addEventListener('change', () => {
  document.querySelectorAll('.hl-check').forEach(cb => { cb.checked = $selectAll.checked; });
});

$hideSent.addEventListener('change', renderHighlights);

$copyBookmarkletBtn.addEventListener('click', () => {
  $bookmarkletCode.select();
  document.execCommand('copy');
  $copyBookmarkletBtn.textContent = t('bm_copied');
  setTimeout(() => { $copyBookmarkletBtn.textContent = t('bm_copy'); }, 2000);
});

// --- Error display ---
function showErrors(errors) {
  if (!errors || errors.length === 0) { hideErrors(); return; }
  $errorList.innerHTML = errors.map(e => {
    let display = escapeHtml(e);
    const jsonMatch = e.match(/Notion API error (\d+): (.+)/s);
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[2]);
        display = `<strong>Notion API ${jsonMatch[1]}</strong>: ${escapeHtml(parsed.message || parsed.code || jsonMatch[2])}`;
      } catch (_) {}
    }
    return `<div class="error-item">${display}</div>`;
  }).join('');
  $errorDetails.style.display = '';
}

function hideErrors() {
  $errorDetails.style.display = 'none';
  $errorList.innerHTML = '';
}

// --- Utilities ---
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function showStatus(el, msg, cls) {
  el.textContent = msg;
  el.className = 'status ' + (cls || '');
  if (cls === 'ok') setTimeout(() => { el.textContent = ''; }, 3000);
}

// --- Start ---
init();
"""


def highlight_hash(h):
    """ハイライトの一意キーを生成"""
    key = f"{h.get('bookTitle', '')}\n{h.get('text', '')}\n{h.get('location', '')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]


def load_json(filepath, default=None):
    if default is None:
        default = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def notion_api_request(token, url, data=None, method='GET'):
    """Notion API への汎用リクエスト"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f'Notion API error {e.code}: {error_body}')


def query_notion_database(config):
    """Notion DB のスキーマ（プロパティ一覧）を取得"""
    token = config['notion_token']
    db_id = config['database_id']
    url = f'https://api.notion.com/v1/databases/{db_id}'
    return notion_api_request(token, url)


def create_notion_page(config, h, db_schema=None):
    """Notion API でページを作成（DB スキーマに合わせてプロパティを動的に構築）"""
    token = config['notion_token']
    db_id = config['database_id']

    # DB スキーマからプロパティ名と型を取得
    if db_schema:
        db_props = db_schema.get('properties', {})
    else:
        db_props = None

    def prop_exists(name, expected_type=None):
        if db_props is None:
            return True  # スキーマ未取得時はすべて送信を試みる
        prop = db_props.get(name)
        if not prop:
            return False
        if expected_type and prop.get('type') != expected_type:
            return False
        return True

    def find_title_prop():
        """title 型のプロパティ名を探す"""
        if db_props:
            for name, prop in db_props.items():
                if prop.get('type') == 'title':
                    return name
        return 'Name'

    properties = {}

    # title プロパティ（必須 — DB に必ず1つある）
    title_prop = find_title_prop()
    properties[title_prop] = {
        "title": [{"text": {"content": h.get('text', '')[:2000]}}]
    }

    # オプションプロパティ — DB に存在する場合のみ追加
    if prop_exists('Book', 'rich_text'):
        properties['Book'] = {
            "rich_text": [{"text": {"content": h.get('bookTitle', '')}}]
        }
    if prop_exists('Author', 'rich_text'):
        properties['Author'] = {
            "rich_text": [{"text": {"content": h.get('author', '')}}]
        }
    if prop_exists('Location', 'rich_text'):
        properties['Location'] = {
            "rich_text": [{"text": {"content": h.get('location', '')}}]
        }
    if prop_exists('Color', 'select'):
        properties['Color'] = {
            "select": {"name": h.get('color', 'yellow')}
        }

    page_data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return notion_api_request(
        token,
        'https://api.notion.com/v1/pages',
        data=page_data,
        method='POST'
    )


class Handler(http.server.BaseHTTPRequestHandler):

    def _check_auth(self):
        """Basic 認証チェック（設定されている場合のみ）"""
        if not BASIC_AUTH_USER:
            return True
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            self._send_auth_required()
            return False
        try:
            decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
            user, _, passwd = decoded.partition(':')
            if user == BASIC_AUTH_USER and passwd == BASIC_AUTH_PASS:
                return True
        except Exception:
            pass
        self._send_auth_required()
        return False

    def _send_auth_required(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Kindle Highlights"')
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('認証が必要です'.encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if not self._check_auth():
            return
        path = urlparse(self.path).path

        if path == '/api/highlights':
            self._get_highlights()
        elif path == '/api/config':
            self._get_config()
        elif path == '/api/bookmarklet':
            self._get_bookmarklet()
        elif path == '/api/backup':
            self._backup()
        else:
            self._serve_static(path)

    def do_POST(self):
        if not self._check_auth():
            return
        path = urlparse(self.path).path

        if path == '/api/highlights':
            self._receive_highlights()
        elif path == '/api/send-to-notion':
            self._send_to_notion()
        elif path == '/api/config':
            self._save_config()
        elif path == '/api/test-notion':
            self._test_notion()
        elif path == '/api/restore':
            self._restore()
        else:
            self._error(404, 'Not Found')

    # --- Static file serving ---

    def _serve_static(self, path):
        if path == '/' or path == '':
            path = '/index.html'

        filepath = os.path.join(STATIC_DIR, path.lstrip('/').replace('/', os.sep))
        filepath = os.path.normpath(filepath)

        if not filepath.startswith(STATIC_DIR):
            self._error(403, 'Forbidden')
            return

        if not os.path.isfile(filepath):
            self._error(404, 'Not Found')
            return

        ext = os.path.splitext(filepath)[1].lower()
        content_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.png': 'image/png',
            '.ico': 'image/x-icon',
        }
        content_type = content_types.get(ext, 'application/octet-stream')

        with open(filepath, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    # --- API handlers ---

    def _receive_highlights(self):
        body = self._read_body()
        existing = load_json(HIGHLIGHTS_FILE, [])
        existing_hashes = {highlight_hash(h) for h in existing}

        new_count = 0
        for h in body.get('highlights', []):
            hh = highlight_hash(h)
            if hh not in existing_hashes:
                existing.append(h)
                existing_hashes.add(hh)
                new_count += 1

        save_json(HIGHLIGHTS_FILE, existing)
        self._json_response({'status': 'ok', 'new': new_count, 'total': len(existing)})

    def _get_highlights(self):
        data = load_json(HIGHLIGHTS_FILE, [])
        sent_hashes = set(load_json(SENT_FILE, []))
        for h in data:
            h['_sent'] = highlight_hash(h) in sent_hashes
        self._json_response(data)

    def _get_bookmarklet(self):
        self._json_response({'code': get_bookmarklet_code()})

    def _send_to_notion(self):
        body = self._read_body()
        config = load_json(CONFIG_FILE, {})

        if not config.get('notion_token') or not config.get('database_id'):
            self._json_response(
                {'error': 'Notion API キーまたはデータベース ID が未設定です'}, 400
            )
            return

        # DB スキーマを取得してプロパティを動的に構築
        db_schema = None
        try:
            db_schema = query_notion_database(config)
        except Exception as e:
            self._json_response({
                'error': f'DB 情報の取得に失敗: {e}'
            }, 400)
            return

        highlights_to_send = body.get('highlights', [])
        sent_hashes = set(load_json(SENT_FILE, []))

        sent_count = 0
        skipped_count = 0
        errors = []

        for h in highlights_to_send:
            hh = highlight_hash(h)
            if hh in sent_hashes:
                skipped_count += 1
                continue
            try:
                create_notion_page(config, h, db_schema)
                sent_hashes.add(hh)
                sent_count += 1
            except Exception as e:
                errors.append(str(e))

        save_json(SENT_FILE, list(sent_hashes))
        self._json_response({
            'sent': sent_count,
            'skipped': skipped_count,
            'errors': errors
        })

    def _test_notion(self):
        """Notion 接続テスト: DB スキーマを取得し、プロパティの過不足を報告"""
        config = load_json(CONFIG_FILE, {})

        if not config.get('notion_token') or not config.get('database_id'):
            self._json_response(
                {'error': 'Notion API キーまたはデータベース ID が未設定です'}, 400
            )
            return

        try:
            db_info = query_notion_database(config)
        except Exception as e:
            self._json_response({'error': str(e)}, 400)
            return

        db_title = ''
        title_list = db_info.get('title', [])
        if title_list:
            db_title = title_list[0].get('plain_text', '')

        props = db_info.get('properties', {})
        prop_summary = {
            name: prop.get('type', '?') for name, prop in props.items()
        }

        # 期待するプロパティとの比較
        expected = {
            'title型プロパティ': ('title', True),
            'Book': ('rich_text', False),
            'Author': ('rich_text', False),
            'Location': ('rich_text', False),
            'Color': ('select', False),
        }

        found = []
        missing = []
        has_title = False

        for name, prop in props.items():
            if prop.get('type') == 'title':
                has_title = True
                found.append(f'✅ {name} (title) — ハイライト本文を格納')

        if not has_title:
            missing.append('❌ title 型プロパティが見つかりません')

        for exp_name, (exp_type, _required) in expected.items():
            if exp_name == 'title型プロパティ':
                continue
            if exp_name in props and props[exp_name].get('type') == exp_type:
                found.append(f'✅ {exp_name} ({exp_type})')
            elif exp_name in props:
                actual_type = props[exp_name].get('type', '?')
                missing.append(
                    f'⚠️ {exp_name} の型が違います（期待: {exp_type}, 実際: {actual_type}）'
                )
            else:
                missing.append(
                    f'ℹ️ {exp_name} ({exp_type}) が未作成 — なくても動作しますが情報が欠けます'
                )

        self._json_response({
            'status': 'ok',
            'database_title': db_title,
            'properties': prop_summary,
            'found': found,
            'missing': missing,
        })

    def _backup(self):
        """全データを1つの JSON としてダウンロード"""
        import datetime
        backup = {
            'version': 1,
            'created_at': datetime.datetime.now().isoformat(),
            'highlights': load_json(HIGHLIGHTS_FILE, []),
            'sent': load_json(SENT_FILE, []),
            'config': load_json(CONFIG_FILE, {}),
            'env': {}
        }

        # .env ファイルの内容を含める
        env_path = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                backup['env_raw'] = f.read()
            # パース済みも含める
            for key in ('HOST', 'PORT', 'BASE_URL', 'BASIC_AUTH_USER', 'BASIC_AUTH_PASS'):
                val = os.environ.get(key, '')
                if val:
                    backup['env'][key] = val

        body = json.dumps(backup, ensure_ascii=False, indent=2).encode('utf-8')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'kindle-highlights-backup-{timestamp}.json'

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self._cors_headers()
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _restore(self):
        """バックアップ JSON からデータを復元"""
        body = self._read_body()

        if 'version' not in body:
            self._json_response({'error': 'Invalid backup file'}, 400)
            return

        restored = []

        # highlights
        if 'highlights' in body:
            save_json(HIGHLIGHTS_FILE, body['highlights'])
            restored.append(f"highlights ({len(body['highlights'])})")

        # sent
        if 'sent' in body:
            save_json(SENT_FILE, body['sent'])
            restored.append(f"sent ({len(body['sent'])})")

        # config (Notion API key, DB ID)
        if 'config' in body:
            save_json(CONFIG_FILE, body['config'])
            restored.append('config')

        # .env
        if 'env_raw' in body and body['env_raw'].strip():
            env_path = os.path.join(BASE_DIR, '.env')
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(body['env_raw'])
            restored.append('.env')

        self._json_response({
            'status': 'ok',
            'restored': restored
        })

    def _save_config(self):
        body = self._read_body()
        save_json(CONFIG_FILE, body)
        self._json_response({'status': 'ok'})

    def _get_config(self):
        config = load_json(CONFIG_FILE, {})
        self._json_response(config)

    # --- Helpers ---

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length)
        return json.loads(raw) if raw else {}

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._cors_headers()
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _error(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def setup_static_files():
    """初回起動時に static/ フォルダと HTML/CSS/JS を生成"""
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    files = {
        'index.html': INDEX_HTML,
        'style.css': STYLE_CSS,
        'app.js': APP_JS,
    }

    for filename, content in files.items():
        filepath = os.path.join(STATIC_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content.lstrip('\n'))
            print(f'  ✏️  {filename} を生成しました')
        else:
            print(f'  ✔️  {filename} は既に存在します')


if __name__ == '__main__':
    print('📁 静的ファイルをセットアップ中...')
    setup_static_files()
    print()

    base_url = get_base_url()
    server = http.server.HTTPServer((HOST, PORT), Handler)

    print(f'🚀 サーバー起動: {base_url}')
    print(f'   HOST={HOST}, PORT={PORT}')
    if BASIC_AUTH_USER:
        print(f'   🔒 Basic 認証: 有効 (user={BASIC_AUTH_USER})')
    else:
        print('   🔓 Basic 認証: 無効')
    if BASE_URL:
        print(f'   🌐 外部URL: {BASE_URL}')
    print('   Ctrl+C で停止')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nサーバーを停止しました')
        server.server_close()
