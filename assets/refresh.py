#!/usr/bin/env python3
"""
Refresh Feishu media URLs from a Bitable table.

This template is designed for static portfolio sites deployed to GitHub Pages:
- authenticate with Feishu OpenAPI
- fetch live Bitable records
- resolve attachment tokens into tmp_download_url values
- write static JSON files for the frontend
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_DIR = Path(__file__).resolve().parent
API_DIR = REPO_DIR / "api"
VIDEOS_FILE = API_DIR / "videos.json"
COVERS_FILE = API_DIR / "covers.json"
PORTFOLIO_FILE = API_DIR / "portfolio.json"

APP_ID = os.environ.get("LARK_APP_ID", "").strip()
APP_SECRET = os.environ.get("LARK_APP_SECRET", "").strip()
BASE_TOKEN = os.environ.get("LARK_BASE_TOKEN", "").strip()
TABLE_ID = os.environ.get("LARK_TABLE_ID", "").strip()

VIDEO_FIELD_CANDIDATES = ("样片", "视频", "作品", "附件", "视频作品")
COVER_FIELD_CANDIDATES = ("封面", "封面图", "海报", "图片", "缩略图")
TITLE_FIELD_CANDIDATES = ("内容", "标题", "作品名称", "名称")
CATEGORY_FIELD_CANDIDATES = ("类型", "分类", "标签")
DURATION_FIELD_CANDIDATES = ("时长", "片长")
TOOLS_FIELD_CANDIDATES = ("AI工具", "工具", "使用工具")
ORDER_FIELD_CANDIDATES = ("序号", "排序", "order", "Order")

BATCH_SIZE = 5


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def require_env() -> None:
    missing = [
        name
        for name, value in (
            ("LARK_APP_ID", APP_ID),
            ("LARK_APP_SECRET", APP_SECRET),
            ("LARK_BASE_TOKEN", BASE_TOKEN),
            ("LARK_TABLE_ID", TABLE_ID),
        )
        if not value
    ]
    if missing:
        fail(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Configure them as repository secrets before running refresh.py."
        )


def request_json(
    url: str,
    *,
    data: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        fail(f"HTTP {exc.code} calling {url}: {body}")
    except urllib.error.URLError as exc:
        fail(f"Request failed for {url}: {exc}")


def get_tenant_access_token() -> str:
    res = request_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data={"app_id": APP_ID, "app_secret": APP_SECRET},
    )
    if res.get("code") != 0 or not res.get("tenant_access_token"):
        fail(f"Failed to get tenant access token: {json.dumps(res, ensure_ascii=False)}")
    return str(res["tenant_access_token"])


def get_records(tenant_token: str) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    page_token = ""

    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records?"
            + urllib.parse.urlencode(params)
        )
        res = request_json(url, token=tenant_token)
        if res.get("code") != 0:
            fail(f"Failed to fetch Bitable records: {json.dumps(res, ensure_ascii=False)}")

        data = res.get("data", {})
        all_records.extend(data.get("items", []))

        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break

    return all_records


def batch_resolve_urls(tenant_token: str, file_tokens: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    unique_tokens = [token for token in dict.fromkeys(file_tokens) if token]

    extra = urllib.parse.quote(json.dumps({"bitablePerm": {"tableId": TABLE_ID}}, ensure_ascii=False))
    base_url = "https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url"

    for start in range(0, len(unique_tokens), BATCH_SIZE):
        batch = unique_tokens[start : start + BATCH_SIZE]
        query = [("extra", extra)]
        query.extend(("file_tokens", token) for token in batch)
        url = base_url + "?" + "&".join(f"{k}={v}" for k, v in query)
        res = request_json(url, token=tenant_token)
        if res.get("code") != 0:
            fail(f"Failed to resolve media URLs: {json.dumps(res, ensure_ascii=False)}")

        for item in res.get("data", {}).get("tmp_download_urls", []):
            token = item.get("file_token")
            tmp_url = item.get("tmp_download_url")
            if token and tmp_url:
                resolved[str(token)] = str(tmp_url)

    return resolved


def pick_first_present(fields: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for key in candidates:
        if key in fields and fields[key] not in (None, "", []):
            return fields[key]
    return None


def first_attachment_token(value: Any) -> str | None:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            token = first.get("file_token")
            return str(token) if token else None
    return None


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("text", "name", "value"):
            if isinstance(value.get(key), str):
                return value[key].strip()
        return ""
    if isinstance(value, list):
        parts = [normalize_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    return str(value).strip()


def normalize_categories(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        text = normalize_text(value)
        return [text] if text else []
    if isinstance(value, list):
        categories: list[str] = []
        for item in value:
            text = normalize_text(item)
            if text:
                categories.append(text)
        return categories
    return []


def normalize_order(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_output(
    records: list[dict[str, Any]],
    resolved_urls: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    portfolio: list[dict[str, Any]] = []
    video_map: dict[str, str] = {}
    cover_map: dict[str, str] = {}

    for index, record in enumerate(records):
        fields = record.get("fields", {})
        video_field = pick_first_present(fields, VIDEO_FIELD_CANDIDATES)
        cover_field = pick_first_present(fields, COVER_FIELD_CANDIDATES)
        video_token = first_attachment_token(video_field)
        cover_token = first_attachment_token(cover_field)

        if not video_token:
            continue

        video_url = resolved_urls.get(video_token)
        if not video_url:
            continue

        if cover_token and resolved_urls.get(cover_token):
            cover_map[cover_token] = resolved_urls[cover_token]

        video_map[video_token] = video_url

        title = normalize_text(pick_first_present(fields, TITLE_FIELD_CANDIDATES)) or f"作品 {index + 1}"
        categories = normalize_categories(pick_first_present(fields, CATEGORY_FIELD_CANDIDATES))
        duration = normalize_text(pick_first_present(fields, DURATION_FIELD_CANDIDATES))
        tools = normalize_text(pick_first_present(fields, TOOLS_FIELD_CANDIDATES))
        order = normalize_order(pick_first_present(fields, ORDER_FIELD_CANDIDATES))

        portfolio.append(
            {
                "record_id": record.get("record_id", ""),
                "title": title,
                "order": order,
                "categories": categories,
                "duration": duration,
                "tools": tools,
                "video_token": video_token,
                "video_url": video_url,
                "cover_token": cover_token or "",
                "cover_url": resolved_urls.get(cover_token, "") if cover_token else "",
            }
        )

    portfolio.sort(key=lambda item: (item["order"], item["title"]))
    return portfolio, video_map, cover_map


def write_outputs(
    portfolio: list[dict[str, Any]],
    video_map: dict[str, str],
    cover_map: dict[str, str],
) -> None:
    API_DIR.mkdir(parents=True, exist_ok=True)
    refreshed_at = datetime.now(timezone.utc).isoformat()

    videos_payload = dict(video_map)
    videos_payload["_refreshed_at"] = refreshed_at
    videos_payload["_count"] = len(video_map)

    covers_payload = dict(cover_map)
    covers_payload["_refreshed_at"] = refreshed_at
    covers_payload["_count"] = len(cover_map)

    stats = Counter()
    for item in portfolio:
        for category in item["categories"] or ["未分类"]:
            stats[category] += 1

    portfolio_payload = {
        "_refreshed_at": refreshed_at,
        "_count": len(portfolio),
        "_stats": dict(sorted(stats.items())),
        "items": portfolio,
    }

    VIDEOS_FILE.write_text(json.dumps(videos_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    COVERS_FILE.write_text(json.dumps(covers_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PORTFOLIO_FILE.write_text(json.dumps(portfolio_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    require_env()
    tenant_token = get_tenant_access_token()
    records = get_records(tenant_token)
    print(f"Fetched {len(records)} Bitable records.")

    attachment_tokens: list[str] = []
    for record in records:
        fields = record.get("fields", {})
        for candidates in (VIDEO_FIELD_CANDIDATES, COVER_FIELD_CANDIDATES):
            token = first_attachment_token(pick_first_present(fields, candidates))
            if token:
                attachment_tokens.append(token)

    resolved_urls = batch_resolve_urls(tenant_token, attachment_tokens)
    print(f"Resolved {len(resolved_urls)} attachment URLs.")

    portfolio, video_map, cover_map = build_output(records, resolved_urls)
    write_outputs(portfolio, video_map, cover_map)

    print(f"Wrote {len(portfolio)} items to {PORTFOLIO_FILE}.")
    print(f"Wrote {len(video_map)} video URLs to {VIDEOS_FILE}.")
    print(f"Wrote {len(cover_map)} cover URLs to {COVERS_FILE}.")


if __name__ == "__main__":
    main()
