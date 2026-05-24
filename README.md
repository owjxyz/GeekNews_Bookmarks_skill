# GeekNews/Hada Bookmarks Skill + Telegram Plugin

GeekNews 긱뉴스 기사를 모니터링하고 저장/조회/삭제할 수 있는 OpenClaw Agent 스킬과 Telegram 슬래시 커맨드 플러그인입니다.

## 📦 구성 요소

| 구성 요소 | 설명 |
|-----------|------|
| **스킬** (`hada-bookmarks`) | GeekNews 모니터링, 북마크 CRUD |
| **텔레그램 플러그인** (`hada-bookmarks-telegram`) | `/hada_bookmarks` 슬래시 커맨드 + 인라인 UI |
| **ヘルパー スクリプト** (`hada_bookmark.py`) | JSON 기반 북마크/상태 관리 |

## 🗂️ 디렉토리 구조

```
GeekNews_Bookmarks_skill/
├── README.md                                    # 본 문서
├── skill/
│   ├── SKILL.md                                 # 스킬 매니페스트
│   └── scripts/
│       └── hada_bookmark.py                     # 북마크 관리 스크립트
├── plugin/
│   ├── index.js                                 # 텔레그램 UI & 명령 처리
│   ├── openclaw.plugin.json                     # 플러그인 매니페스트
│   └── package.json                             # 패키지 정보
├── memory/
│   ├── hada-news-state.json                     # 모니터링 상태 (자동 생성)
│   └── hada-news-bookmarks.json                 # 북마크 데이터 (자동 생성)
└── cron.md                                      # 추천 cron 설정 예시
```

## 🚀 설치 & 재현 절차

> **환경 변수 안내**: 별도 표시가 없는 한 `<USER_HOME>`은 사용자 홈 디렉토리를 의미합니다.

### 1. 저장소 클론

```bash
git clone https://github.com/owjxyz/GeekNews_Bookmarks_skill.git
```

### 2. 스킬 설치

OpenClaw 에이전트의 스킬 폴더에 복사합니다.

```bash
mkdir -p <USER_HOME>/.agents/skills/hada-bookmarks/scripts
cp GeekNews_Bookmarks_skill/skill/SKILL.md <USER_HOME>/.agents/skills/hada-bookmarks/
cp GeekNews_Bookmarks_skill/skill/scripts/hada_bookmark.py <USER_HOME>/.agents/skills/hada-bookmarks/scripts/
chmod +x <USER_HOME>/.agents/skills/hada-bookmarks/scripts/hada_bookmark.py
```

**핵심:** Python 스크립트의 경로는 플러그인 `index.js`에서 하드 코딩되어 있으므로 **정확하게 위 경로에 배치**해야 합니다.

### 3. 텔레그램 플러그인 설치

```bash
mkdir -p <USER_HOME>/.openclaw/extensions/hada-bookmarks-telegram
cp GeekNews_Bookmarks_skill/plugin/index.js <USER_HOME>/.openclaw/extensions/hada-bookmarks-telegram/
cp GeekNews_Bookmarks_skill/plugin/openclaw.plugin.json <USER_HOME>/.openclaw/extensions/hada-bookmarks-telegram/
cp GeekNews_Bookmarks_skill/plugin/package.json <USER_HOME>/.openclaw/extensions/hada-bookmarks-telegram/
```

### 4. 메모리 디렉토리 생성

```bash
mkdir -p <USER_HOME>/.openclaw/workspace/memory
touch <USER_HOME>/.openclaw/workspace/memory/hada-news-bookmarks.json
touch <USER_HOME>/.openclaw/workspace/memory/hada-news-state.json
```

초기 상태 (선택):

```json
// hada-news-bookmarks.json
[]
```

```json
// hada-news-state.json
{
  "lastChecked": null,
  "seen": [],
  "lastDelivered": []
}
```

### 5. OpenClaw 설정 등록

`<USER_HOME>/.openclaw/openclaw.json`에 플러그인을 enabled로 등록:

```json
{
  "plugins": {
    "entries": {
      "hada-bookmarks-telegram": {
        "enabled": true
      }
    }
  }
}
```

텔레그램 skill fallback과 충돌을 피하려면 (선택):

```json
{
  "channels": {
    "telegram": {
      "commands": {
        "nativeSkills": false
      }
    }
  }
}
```

### 6. 게이트웨이 재시작

```bash
openclaw gateway restart
openclaw gateway status
```

### 7. 검증

```bash
# 플러그인 상태 확인
openclaw plugins inspect hada-bookmarks-telegram --json
```

정상 예시:

```json
{
  "id": "hada-bookmarks-telegram",
  "status": "loaded",
  "enabled": true,
  "activated": true,
  "commands": ["hada_bookmarks"],
  "pluginCommands": ["hada_bookmarks"]
}
```

텔레그램 Bot API로 직접 확인:

```bash
python3 - <<'PY'
import json, urllib.request
from pathlib import Path
cfg = json.loads(Path('<USER_HOME>/.openclaw/openclaw.json').read_text())
token = cfg['channels']['telegram']['botToken']
with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getMyCommands') as r:
    resp = json.loads(r.read().decode())
for c in resp.get('result', []):
    if c.get('command') == 'hada_bookmarks':
        print(c)
PY
```

> ⚠️ **주의**: `openclaw.plugin.json`에 `commandAliases`와 `activation.onCommands`가 누락되면 재시작 후 `/hada_bookmarks`가 skill fallback으로 빠집니다.

## ⚙️ Cron 설정

`cron.md`를 참조하여, GeekNews 모니터링을 위한 주기적 크론 작업 설정을 권장합니다.

## 🔧 종속성

- **Python 3** — 스크립트 실행
- **Node.js** — 플러그인 실행 (OpenClaw 내장)
- **OpenClaw** — 에이전트 런타임

## 📝 라이선스

MIT
