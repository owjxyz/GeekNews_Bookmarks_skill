---
name: hada-bookmarks
description: Use when the user invokes hada-bookmarks or /hada_bookmarks with no arguments or asks to save, retrieve, list, show, or inspect GeekNews/Hada.io bookmarks, including Korean requests like 긱뉴스 북마크 목록, 저장된 북마크, 북마크 보여줘, 북마크 1, 북마크 제목. With no arguments, show a title list sorted by most recently saved first; with a number/id/title argument, show that bookmark's link, source, saved time, and summary.
license: MIT
metadata:
  category: news
  locale: ko-KR
  source: hada-bookmarks-local
---

# Hada / GeekNews Bookmarks

Manage local bookmarks for Hada.io / GeekNews summaries.

## Files

- State: `/home/lukeoh/.openclaw/workspace/memory/hada-news-state.json`
- Bookmarks: `/home/lukeoh/.openclaw/workspace/memory/hada-news-bookmarks.json`
- Helper: `scripts/hada_bookmark.py` in this skill directory

## Slash command behavior

OpenClaw sanitizes the skill name `hada-bookmarks` to the slash command `/hada_bookmarks`.

### No arguments

When the user invokes `hada-bookmarks` or `/hada_bookmarks` with no arguments, treat it as “bookmark picker/list” and run:

```bash
python3 /home/lukeoh/.agents/skills/hada-bookmarks/scripts/hada_bookmark.py list
```

Return a compact Korean title list, newest saved first. Format like:

```text
저장된 GeekNews/Hada 북마크입니다, 우진님.

1. 제목
2. 제목
3. 제목

궁금한 글은 /hada_bookmarks 1 처럼 번호로 열어보실 수 있습니다.
```

If the current channel/runtime offers real interactive buttons, use one button per bookmark title and make the button action equivalent to `/hada_bookmarks <번호>`. If native buttons are not available in the current assistant response path, do not fake them; use the numbered fallback above.

If there are no bookmarks, say no saved bookmarks yet.

### Argument provided: show one bookmark

When the user invokes `/hada_bookmarks <번호|id|제목|URL>` or asks to open/show a specific bookmark, run:

```bash
python3 /home/lukeoh/.agents/skills/hada-bookmarks/scripts/hada_bookmark.py show '<번호|id|제목|URL>'
```

Return:

- title
- GeekNews article URL (`topicUrl`, usually `https://news.hada.io/topic?id=...`)
- source/original URL if different
- saved date/time if useful
- concise summary from the helper output

Use the same visual separator style as other Hada replies.

## List saved bookmarks

For explicit saved bookmark list / 북마크 목록 / 북마크 보여줘 requests, use the no-argument list behavior above.

## Delete a saved bookmark

When the user asks to delete/remove a saved bookmark by number, id, title/title fragment, or URL/domain fragment:

```bash
python3 /home/lukeoh/.agents/skills/hada-bookmarks/scripts/hada_bookmark.py delete '<번호|id|제목|URL>'
```

Use this only for already-saved bookmarks. The Telegram plugin also exposes a detail-view delete button with a confirmation step.

## Save a bookmark

When the user asks to save/bookmark an item by number, id, title/title fragment, or URL/domain fragment:

```bash
python3 /home/lukeoh/.agents/skills/hada-bookmarks/scripts/hada_bookmark.py save '<번호|id|제목|URL>' --saved-by '<사용자>'
```

Resolution order:

1. Number from `lastDelivered.number`
2. GeekNews topic id
3. Case-insensitive exact title
4. Title substring
5. External URL or GeekNews topic URL substring
6. All query words contained in title

If the helper returns `AMBIGUOUS`, do not guess. Show candidate titles and `topicUrl`s, then ask the user to choose a more specific title/id.

When save succeeds, display the saved item using the same visual format as the Hada cron summary, not a plain one-line confirmation:

```text
북마크 저장 완료했습니다, 우진님.

━━━━━━━━━━━━━━
🧠 1. 제목
🔗 https://news.hada.io/topic?id=...
원문: https://external.example/...   # only if different from topicUrl
```

Notes:
- Use the same section separator: `━━━━━━━━━━━━━━`.
- Use one emoji on the title line only.
- Link line must be `🔗 {topicUrl}` and must prefer the GeekNews article address.
- If showing several saved items, number them in display order.
- Do not invent summary lines if the bookmark entry does not store summary text.

## Output rules

- Always prefer the GeekNews article address (`topicUrl`) over the external source URL.
- Bookmark lists must be sorted by `savedAt` descending, not file order.
- Avoid markdown tables in Telegram; use bullets or cron-style blocks.
