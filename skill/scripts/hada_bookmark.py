#!/usr/bin/env python3
"""Save/list/show Hada.io (GeekNews) bookmarks from the local Hada monitor state."""
from __future__ import annotations
import argparse, datetime as dt, html, json, re, sys, urllib.request
from pathlib import Path

STATE = Path('/home/lukeoh/.openclaw/workspace/memory/hada-news-state.json')
BOOKMARKS = Path('/home/lukeoh/.openclaw/workspace/memory/hada-news-bookmarks.json')


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def norm(s: str | None) -> str:
    s = (s or '').lower().strip()
    s = re.sub(r'["“”‘’`\[\](){}<>]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def candidates(state):
    items = []
    for src in ('lastDelivered', 'seen'):
        for idx, item in enumerate(state.get(src, []) or []):
            if not item:
                continue
            merged = dict(item)
            merged.setdefault('number', idx + 1)
            if not merged.get('topicUrl') and merged.get('id'):
                merged['topicUrl'] = f"https://news.hada.io/topic?id={merged['id']}"
            merged['_sourceList'] = src
            items.append(merged)
    dedup = []
    seen_keys = set()
    for item in items:
        key = item.get('id') or item.get('topicUrl') or item.get('url') or item.get('title')
        if key in seen_keys:
            continue
        seen_keys.add(key)
        dedup.append(item)
    return dedup


def sorted_bookmarks():
    data = load_json(BOOKMARKS, {'bookmarks': []})
    bookmarks = list(data.get('bookmarks', []) or [])
    bookmarks.sort(key=lambda b: b.get('savedAt') or '', reverse=True)
    return bookmarks


def resolve_bookmark(query: str):
    q = query.strip()
    bookmarks = sorted_bookmarks()
    if not q:
        return [], bookmarks
    if q.isdigit():
        num = int(q)
        if 1 <= num <= len(bookmarks):
            return [bookmarks[num - 1]], bookmarks
        by_id = [b for b in bookmarks if str(b.get('id') or '') == q or q in str(b.get('topicUrl') or '')]
        if by_id:
            return by_id[:1], bookmarks
    nq = norm(q)
    exact = [b for b in bookmarks if norm(b.get('title')) == nq]
    if exact:
        return exact, bookmarks
    contains = [b for b in bookmarks if nq and nq in norm(b.get('title'))]
    if contains:
        return contains, bookmarks
    url_matches = [b for b in bookmarks if nq and (nq in norm(b.get('url')) or nq in norm(b.get('topicUrl')))]
    if url_matches:
        return url_matches, bookmarks
    words = [w for w in re.split(r'\s+', nq) if len(w) >= 2]
    fuzzy = [b for b in bookmarks if words and all(w in norm(b.get('title')) for w in words)]
    return fuzzy, bookmarks


def resolve(query: str, state):
    q = query.strip()
    items = candidates(state)
    if not q:
        return [], items
    # Number from lastDelivered first.
    if q.isdigit():
        num = int(q)
        numbered = [x for x in state.get('lastDelivered', []) if int(x.get('number') or -1) == num]
        if numbered:
            return numbered[:1], items
        by_id = [x for x in items if str(x.get('id') or '') == q or q in str(x.get('topicUrl') or '')]
        if by_id:
            return by_id[:1], items
    nq = norm(q)
    exact = [x for x in items if norm(x.get('title')) == nq]
    if exact:
        return exact, items
    contains = [x for x in items if nq and nq in norm(x.get('title'))]
    if contains:
        return contains, items
    url_matches = [x for x in items if nq and (nq in norm(x.get('url')) or nq in norm(x.get('topicUrl')))]
    if url_matches:
        return url_matches, items
    words = [w for w in re.split(r'\s+', nq) if len(w) >= 2]
    fuzzy = [x for x in items if words and all(w in norm(x.get('title')) for w in words)]
    return fuzzy, items


def bookmark(query: str, saved_by: str, dry_run: bool = False):
    state = load_json(STATE, {})
    matches, _ = resolve(query, state)
    if not matches:
        print(f"NOT_FOUND: {query}")
        return 1
    if len(matches) > 1:
        print('AMBIGUOUS')
        for m in matches[:10]:
            print(f"- {m.get('id') or ''} {m.get('title')} {m.get('topicUrl') or ''}")
        return 2
    item = matches[0]
    if dry_run:
        print(f"MATCH: {item.get('title')} | {item.get('topicUrl') or item.get('url')}")
        return 0
    data = load_json(BOOKMARKS, {'version': 1, 'updatedAt': None, 'bookmarks': []})
    bookmarks = data.setdefault('bookmarks', [])
    item_id = str(item.get('id') or '')
    topic = item.get('topicUrl') or (f"https://news.hada.io/topic?id={item_id}" if item_id else item.get('url'))
    for b in bookmarks:
        if (item_id and str(b.get('id') or '') == item_id) or (topic and b.get('topicUrl') == topic):
            print(f"EXISTS: {b.get('title')} | {b.get('topicUrl')}")
            return 0
    entry = {
        'id': item_id or None,
        'title': item.get('title'),
        'topicUrl': topic,
        'url': item.get('url'),
        'savedAt': now(),
        'savedBy': saved_by,
        'source': 'hada-new-summary',
        'matchedBy': query,
    }
    bookmarks.append(entry)
    data['updatedAt'] = entry['savedAt']
    save_json(BOOKMARKS, data)
    print(f"SAVED: {entry['title']} | {entry['topicUrl']}")
    return 0


def list_bookmarks(as_json: bool = False):
    bookmarks = sorted_bookmarks()
    if as_json:
        print(json.dumps(bookmarks, ensure_ascii=False, indent=2))
        return 0
    for b in bookmarks:
        saved_at = b.get('savedAt') or ''
        print(f"- {b.get('title')} | {b.get('topicUrl')} | {saved_at}")
    return 0


def html_to_text(fragment: str) -> str:
    fragment = re.sub(r'<(script|style)[^>]*>.*?</\\1>', ' ', fragment, flags=re.I | re.S)
    fragment = re.sub(r'<br\s*/?>', '\n', fragment, flags=re.I)
    fragment = re.sub(r'</(p|li|h\d|div|ul|ol)>', '\n', fragment, flags=re.I)
    fragment = re.sub(r'<[^>]+>', ' ', fragment)
    text = html.unescape(fragment)
    text = re.sub(r'\n\s*\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def fetch_topic_summary(topic_url: str, limit: int = 900) -> str:
    if not topic_url:
        return ''
    try:
        req = urllib.request.Request(topic_url, headers={'User-Agent': 'OpenClaw hada-bookmarks/1.0'})
        raw = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', 'replace')
    except Exception:
        return ''

    # GeekNews exposes a clean JSON-LD DiscussionForumPosting payload. Prefer it over
    # broad HTML scraping so details do not include nav/footer/scripts.
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw, flags=re.I | re.S):
        try:
            payload = json.loads(html.unescape(match.group(1)).strip())
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get('@type') == 'DiscussionForumPosting':
            text = str(payload.get('text') or '').strip()
            if text:
                text = re.sub(r'\s+', ' ', html.unescape(text)).strip()
                return text[:limit].rstrip() + ('…' if len(text) > limit else '')

    # Fallback: prefer the topic body before comments/footer.
    start = raw.find('댓글')
    body = raw[:start] if start > 0 else raw
    text = html_to_text(body)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line in {'GeekNews', '로그인', '최신글 예전글 댓글 Ask Show GN⁺ Weekly | 글등록'}:
            continue
        if line.startswith('처음 오셨나요'):
            break
        lines.append(line)
    text = '\n'.join(lines)
    if len(text) > limit:
        text = text[:limit].rstrip() + '…'
    return text


def show_bookmark(query: str, as_json: bool = False):
    matches, _ = resolve_bookmark(query)
    if not matches:
        print(f"NOT_FOUND: {query}")
        return 1
    if len(matches) > 1:
        print('AMBIGUOUS')
        for b in matches[:10]:
            print(f"- {b.get('id') or ''} {b.get('title')} {b.get('topicUrl') or ''}")
        return 2
    b = dict(matches[0])
    b['summary'] = b.get('summary') or fetch_topic_summary(b.get('topicUrl') or '')
    if as_json:
        print(json.dumps(b, ensure_ascii=False, indent=2))
        return 0
    print(f"TITLE: {b.get('title')}")
    print(f"TOPIC: {b.get('topicUrl')}")
    if b.get('url') and b.get('url') != b.get('topicUrl'):
        print(f"SOURCE: {b.get('url')}")
    if b.get('savedAt'):
        print(f"SAVED_AT: {b.get('savedAt')}")
    if b.get('summary'):
        print('SUMMARY:')
        print(b['summary'])
    return 0


def delete_bookmark(query: str, as_json: bool = False):
    matches, _ = resolve_bookmark(query)
    if not matches:
        print(f"NOT_FOUND: {query}")
        return 1
    if len(matches) > 1:
        print('AMBIGUOUS')
        for b in matches[:10]:
            print(f"- {b.get('id') or ''} {b.get('title')} {b.get('topicUrl') or ''}")
        return 2

    target = matches[0]
    target_id = str(target.get('id') or '')
    target_topic = target.get('topicUrl') or ''
    data = load_json(BOOKMARKS, {'version': 1, 'updatedAt': None, 'bookmarks': []})
    bookmarks = list(data.get('bookmarks', []) or [])

    def is_target(bookmark):
        bookmark_id = str(bookmark.get('id') or '')
        bookmark_topic = bookmark.get('topicUrl') or ''
        return (target_id and bookmark_id == target_id) or (target_topic and bookmark_topic == target_topic)

    kept = [b for b in bookmarks if not is_target(b)]
    removed = [b for b in bookmarks if is_target(b)]
    if not removed:
        print(f"NOT_FOUND: {query}")
        return 1

    data['bookmarks'] = kept
    data['updatedAt'] = now()
    save_json(BOOKMARKS, data)

    removed_item = removed[0]
    if as_json:
        print(json.dumps(removed_item, ensure_ascii=False, indent=2))
        return 0
    print(f"DELETED: {removed_item.get('title')} | {removed_item.get('topicUrl')}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('save')
    s.add_argument('query', help='number, id, or title/title fragment')
    s.add_argument('--saved-by', default='user')
    s.add_argument('--dry-run', action='store_true', help='resolve only; do not write bookmark file')
    l = sub.add_parser('list')
    l.add_argument('--json', action='store_true')
    sh = sub.add_parser('show')
    sh.add_argument('query', help='bookmark list number, id, title/title fragment, or URL')
    sh.add_argument('--json', action='store_true')
    d = sub.add_parser('delete')
    d.add_argument('query', help='bookmark list number, id, title/title fragment, or URL')
    d.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if args.cmd == 'save':
        return bookmark(args.query, args.saved_by, args.dry_run)
    if args.cmd == 'list':
        return list_bookmarks(args.json)
    if args.cmd == 'show':
        return show_bookmark(args.query, args.json)
    if args.cmd == 'delete':
        return delete_bookmark(args.query, args.json)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
