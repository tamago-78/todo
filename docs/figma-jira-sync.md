# Figma → Jira デザインチケット自動ステータス更新

Figmaのページ一覧で、ページが**下から2番目の区切り線より上**に移動されたら、
対応するJiraのデザインチケットを **「進行中」→「レビュー中」** に自動で変更する仕組みです。

スクリプト本体: [`scripts/figma_jira_sync.py`](../scripts/figma_jira_sync.py)（Python3標準ライブラリのみ・追加インストール不要）

## 仕組み

1. Figmaファイル（既定: **26/2Q・3Q** `qJViiSMtt8kDDYlszTPhFt`）のページ一覧を取得
2. 名前がダッシュだけのページ（`---`）を「区切り線」とみなす
3. **下から2番目**の区切り線より上にあるページを「レビュー位置」と判定
4. Jiraの `project = TW AND issuetype = デザイン AND status = 進行中` のチケットと、
   ページ名を照合（`[iOS]` `[Android]` `[小タスク]` などの角括弧タグと空白を無視して比較。
   例: ページ `[Android][iOS]明日のお楽しみ予告` は `[iOS]明日のお楽しみ予告` と
   `[Android]明日のお楽しみ予告` の両チケットにマッチ）
5. マッチしたチケットを「レビュー中」に遷移し、変更理由をコメントで残す

### 前提となるFigmaのページ構成

```
 cover など
 ---            ← 区切り線①
 （レビュー位置）ここより上に移動されたページのチケットが「レビュー中」になる
 ---            ← 区切り線②（下から2番目）★ここが判定ライン
 作業中のページ …
 ---            ← 区切り線③（一番下）
 その他 …
```

### 安全側の挙動

- 区切り線が**2本未満**のファイルでは**何もしない**（2026-07-22時点の26/2Q・3Qファイルは区切り線1本なので、区切り線を追加するまで発動しません）
- 変更は「進行中 → レビュー中」の**一方向のみ**。ページを下に戻してもステータスは戻しません
- 対象は「デザイン」チケットで現在「進行中」のものだけ

## 実行方法

### Claude Code（クラウド環境）で実行

認証はプロキシが自動付与するため、そのまま動きます。

```bash
DRY_RUN=1 python3 scripts/figma_jira_sync.py   # 変更せず対象だけ表示（お試し）
python3 scripts/figma_jira_sync.py             # 実際にステータスを変更
```

### 定期実行（自動化）

Claude Codeのスケジュール実行（Routine）で、平日9〜19時に1時間ごとに実行する想定です。
このセッションでClaudeに「定期実行を有効化して」と伝えれば設定されます。
停止したいときは「Figma-Jira同期の定期実行を止めて」でOKです。

### ローカルPCで実行する場合

環境変数でトークンを渡します。

```bash
export FIGMA_TOKEN=＜Figmaのパーソナルアクセストークン＞
export JIRA_EMAIL=＜Jiraのメールアドレス＞
export JIRA_API_TOKEN=＜JiraのAPIトークン＞  # https://id.atlassian.com/manage-profile/security/api-tokens
python3 scripts/figma_jira_sync.py
```

※トークンはコードやリポジトリに書き込まないこと。

## 設定の変更（環境変数）

| 環境変数 | 既定値 | 説明 |
|---|---|---|
| `FIGMA_FILE_KEY` | `qJViiSMtt8kDDYlszTPhFt`（26/2Q・3Q） | 監視するFigmaファイル。**四半期が変わったら新ファイルのキーに差し替える**（URLの `figma.com/design/～/` の部分） |
| `JIRA_BASE_URL` | `https://team-1592382176350.atlassian.net` | Jiraのサイト |
| `JIRA_JQL` | `project = TW AND issuetype = デザイン AND status = "進行中"` | 対象チケットの検索条件 |
| `TO_STATUS` | `レビュー中` | 変更先ステータス |
| `DRY_RUN` | （なし） | `1` で変更せず表示のみ |
| `ADD_COMMENT` | `1` | `0` でチケットへの自動コメントを無効化 |

## テスト

Figmaを触らずにページ構成をシミュレートして確認できます。

```bash
echo '["cover","---","ページA","---","作業中ページ","---"]' > /tmp/pages.json
DRY_RUN=1 python3 scripts/figma_jira_sync.py --pages-json /tmp/pages.json
```

## 運用上の注意

- この自動化はチーム共有のJiraチケットを書き換えます。**本格運用の前にチーム内で周知**し、必要に応じてセキュリティ担当に一声かけてください
- 誤って遷移した場合は、Jira上で手動でステータスを戻せば済みます（コメントに自動変更の記録が残ります）
