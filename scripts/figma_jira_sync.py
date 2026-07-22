#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figmaのページ位置に応じて、Jiraのデザインチケットのステータスを自動更新するスクリプト。

ルール:
    Figmaファイルのページ一覧で「下から2番目の区切り線」より上に置かれているページに
    対応するJiraのデザインチケットが「進行中」だったら、「レビュー中」に変更する。

    - 区切り線 = 名前がダッシュ類だけのページ（例: "---"）
    - ページとチケットの対応 = ページ名とチケット要約を正規化して照合
      （[iOS] [Android] [小タスク] などの角括弧タグと空白を除去して比較）
    - 区切り線が2本未満のときは何もしない（安全側）
    - 変更は「進行中 → レビュー中」の一方向のみ。逆方向には動かさない。

実行方法:
    python3 scripts/figma_jira_sync.py            # 実際にステータスを変更する
    DRY_RUN=1 python3 scripts/figma_jira_sync.py  # 変更せず、何が起きるかだけ表示

認証:
    - Claude Codeのクラウド環境ではプロキシが認証を自動付与するため設定不要。
    - ローカルPCで動かす場合は環境変数を設定する:
        FIGMA_TOKEN      … Figmaのパーソナルアクセストークン
        JIRA_EMAIL       … Jiraのログインメールアドレス
        JIRA_API_TOKEN   … JiraのAPIトークン (https://id.atlassian.com/manage-profile/security/api-tokens)

主な設定（環境変数で上書き可能）:
    FIGMA_FILE_KEY … 監視するFigmaファイルのキー。既定は「26/2Q・3Q」。
                     四半期が変わったら新しいファイルのキーに差し替えること。
                     （FigmaのURL https://www.figma.com/design/<ここ>/... の部分）
"""

import base64
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------- 設定

FIGMA_FILE_KEY = os.environ.get("FIGMA_FILE_KEY", "qJViiSMtt8kDDYlszTPhFt")  # 26/2Q・3Q
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://team-1592382176350.atlassian.net")
JIRA_JQL = os.environ.get(
    "JIRA_JQL",
    'project = TW AND issuetype = デザイン AND status = "進行中"',
)
TO_STATUS = os.environ.get("TO_STATUS", "レビュー中")
DRY_RUN = os.environ.get("DRY_RUN", "") == "1"
ADD_COMMENT = os.environ.get("ADD_COMMENT", "1") == "1"

# 名前がダッシュ・罫線・イコール類と空白だけのページを「区切り線」とみなす
DIVIDER_RE = re.compile(r"^[\s\-‐–—―ー─━=＝_＿]+$")

# ---------------------------------------------------------------- HTTP

def _request(url, method="GET", headers=None, body=None):
    req = urllib.request.Request(url, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as res:
            raw = res.read()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {detail}") from e


def figma_headers():
    token = os.environ.get("FIGMA_TOKEN")
    return {"X-Figma-Token": token} if token else {}


def jira_headers():
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    if email and token:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return {"Authorization": f"Basic {cred}"}
    return {}

# ---------------------------------------------------------------- 照合ロジック

def normalize(name):
    """ページ名／チケット要約を照合用に正規化する。

    例: '[Android][iOS] 明日のお楽しみ予告' -> '明日のお楽しみ予告'
    """
    s = unicodedata.normalize("NFKC", name)
    s = re.sub(r"[\[【][^\]】]*[\]】]", "", s)  # [iOS] や 【小タスク】 などのタグを除去
    s = re.sub(r"\s+", "", s)
    return s.casefold()


def pages_above_second_divider_from_bottom(page_names):
    """下から2番目の区切り線より上にあるページ名を返す。区切り線が2本未満なら None。"""
    divider_indexes = [i for i, n in enumerate(page_names) if DIVIDER_RE.match(n)]
    if len(divider_indexes) < 2:
        return None
    threshold = divider_indexes[-2]
    return [n for n in page_names[:threshold] if not DIVIDER_RE.match(n)]

# ---------------------------------------------------------------- 本体

def fetch_figma_page_names():
    url = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}?depth=1"
    data = _request(url, headers=figma_headers())
    names = [p["name"] for p in data["document"]["children"]]
    print(f"Figmaファイル「{data.get('name')}」: {len(names)}ページ")
    return names


def fetch_jira_issues():
    params = urllib.parse.urlencode(
        {"jql": JIRA_JQL, "fields": "summary,status", "maxResults": 100}
    )
    data = _request(f"{JIRA_BASE_URL}/rest/api/3/search/jql?{params}", headers=jira_headers())
    return data.get("issues", [])


def transition_issue(key, to_status):
    data = _request(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/transitions", headers=jira_headers()
    )
    target = next(
        (t for t in data.get("transitions", []) if t.get("to", {}).get("name") == to_status),
        None,
    )
    if target is None:
        print(f"  !! {key}: 「{to_status}」への遷移が見つからないためスキップ")
        return False
    _request(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/transitions",
        method="POST",
        headers=jira_headers(),
        body={"transition": {"id": target["id"]}},
    )
    return True


def add_comment(key, page_name):
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Figmaでページ「{page_name}」がレビュー位置"
                                f"（下から2番目の区切り線より上）に移動されたため、"
                                f"ステータスを自動で「{TO_STATUS}」に変更しました。"
                            ),
                        }
                    ],
                }
            ],
        }
    }
    _request(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/comment",
        method="POST",
        headers=jira_headers(),
        body=body,
    )


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--pages-json":
        # テスト用: Figmaの代わりにJSONファイル（ページ名の配列）を読む
        with open(sys.argv[2], encoding="utf-8") as f:
            page_names = json.load(f)
        print(f"テストモード: {len(page_names)}ページ（{sys.argv[2]}）")
    else:
        page_names = fetch_figma_page_names()

    review_pages = pages_above_second_divider_from_bottom(page_names)
    if review_pages is None:
        print("区切り線（'---' ページ）が2本未満のため、何もせず終了します。")
        return 0

    review_map = {normalize(n): n for n in review_pages}
    print(f"レビュー位置（下から2番目の区切り線より上）のページ: {len(review_pages)}件")

    issues = fetch_jira_issues()
    print(f"Jira対象チケット（{JIRA_JQL}）: {len(issues)}件")

    changed = 0
    for issue in issues:
        key = issue["key"]
        summary = issue["fields"]["summary"].strip()
        page_name = review_map.get(normalize(summary))
        if page_name is None:
            continue
        if DRY_RUN:
            print(f"  [DRY RUN] {key} 「{summary}」 -> {TO_STATUS}（ページ: {page_name}）")
            changed += 1
            continue
        if transition_issue(key, TO_STATUS):
            if ADD_COMMENT:
                add_comment(key, page_name)
            print(f"  ✔ {key} 「{summary}」 -> {TO_STATUS}（ページ: {page_name}）")
            changed += 1

    if changed == 0:
        print("ステータス変更の対象はありませんでした。")
    else:
        print(f"{'変更対象' if DRY_RUN else '変更した'}チケット: {changed}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
