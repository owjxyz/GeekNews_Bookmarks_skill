# Cron 설정 예시

## Hada.io 새 글 모니터링

> ⚠️ **주의**: 아래 예시의 `<...>` 로 감싼 부분들은 **실제 설정 시 자신의 환경에 맞게 교체**해야 합니다.
> 
> - `<OPENCLAW_WORKSPACE>` — OpenClaw workspace 절대 경로
> - `<GROUP_ID>` — 텔레그램 그룹/채널 ID  
> - `<TOPIC_ID>` — 텔레그램 토픽 ID (해당하는 경우)
> - `<MODEL>` — 사용할 LLM 모델 식별자

```jsonc
{
  "name": "Hada.io new posts monitor",
  "schedule": {
    "kind": "cron",
    "expr": "0 */3 * * *",
    "tz": "Asia/Seoul"
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "매 3시간마다 https://news.hada.io/new 를 확인하세요. 이전 실행 때 저장한 상태 파일 <OPENCLAW_WORKSPACE>/memory/hada-news-state.json 를 읽어서 새 글만 찾아주세요. 새 글이 없으면 정확히 NO_REPLY 만 출력하세요. 새 글이 있으면 한국어로 정리해 Telegram에 전달하세요.\n\n상태/북마크 파일:\n- 상태 파일: <OPENCLAW_WORKSPACE>/memory/hada-news-state.json\n- 북마크 파일: <OPENCLAW_WORKSPACE>/memory/hada-news-bookmarks.json\n\n새 글 요약 출력 포맷:\n- 첫 줄은 '📰 긱뉴스 새 글 요약'.\n- 각 글은 구분선 '━━━━━━━━━━━━━━'로 단락을 나누세요.\n- 제목 줄에만 이모티콘을 1개 사용하세요. 예: '🧠 1. 제목'.\n- 링크 줄은 반드시 GeekNews 아티클 주소(topicUrl)를 먼저 보여주세요.\n- 메시지 마지막에 한 줄로 선택/저장 안내를 넣으세요.\n\n상태 업데이트 규칙:\n- 마지막에 상태 파일을 최신 seen URL/제목 목록으로 업데이트하세요.\n- 이번에 실제로 전달한 글 목록을 상태 파일의 lastDelivered 배열에도 저장하세요.\n- lastDelivered 항목에는 number, id, title, url, topicUrl, deliveredAt 를 포함하세요.\n- topicUrl은 반드시 https://news.hada.io/topic?id=... 형태여야 합니다.",
    "model": "<MODEL>"
  },
  "delivery": {
    "mode": "announce",
    "channel": "telegram",
    "to": "<GROUP_ID>:topic:<TOPIC_ID>"
  }
}
```
