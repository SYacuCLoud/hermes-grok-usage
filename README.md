# hermes-grok-usage

[Hermes Agent](https://github.com/NousResearch/hermes-agent) 데스크톱 상태 표시줄에 SuperGrok 주간(또는 월간) 사용량을 붙이는 SkyMin 플러그인입니다.

GitHub 저장소 이름: `hermes-grok-usage`. 플러그인 id는 `grok-usage`입니다.

## 동작

- 칩 글자: `Grok 42%` (값을 모르면 `Grok —`)
- 툴팁: 기간, 퍼센트, 리셋 시각
- 사용량 80% 이상이면 강조
- 백엔드: Hermes xAI OAuth 토큰으로 Grok CLI 빌링(`cli-chat-proxy.grok.com`)을 읽습니다. 공개 xAI API가 아닙니다.
- 데스크톱 칩은 120초마다 폴링합니다. Python 백엔드는 90초 캐시합니다.

## 구성

```
plugin.yaml              # Hermes 플러그인 매니페스트
dashboard/
  plugin_api.py          # 칩이 쓰는 GET /usage
  manifest.json
desktop/
  plugin.js              # 상태 표시줄 칩 (Hermes desktop plugin SDK)
```

## 설치

두 반쪽이 모두 필요합니다.

**Python 백엔드** (`plugins.enabled`):

1. 이 폴더를 `$HERMES_HOME/plugins/grok-usage/`로 복사합니다.
2. 켭니다.

```bash
hermes plugins enable grok-usage
```

3. Hermes를 재시작합니다.

**데스크톱 칩**:

- `desktop/plugin.js`를 `plugins/grok-usage/desktop/`에 그대로 둡니다. Settings → Plugins에서 켭니다. 이 반쪽은 기본이 꺼짐입니다.
- 또는 `desktop/plugin.js`를 `$HERMES_HOME/desktop-plugins/grok-usage/plugin.js`로 복사합니다. 단독 데스크톱 플러그인은 기본으로 로드됩니다.

Hermes에서 먼저 xAI에 로그인하세요. 토큰이 없으면 칩이 “xAI login missing”을 보여 줍니다.

## 요구 사항

- Hermes 데스크톱 앱. CLI/게이트웨이만으로는 칩이 그려지지 않습니다.
- Hermes에 xAI OAuth가 이미 설정되어 있어야 합니다.
- 토큰이 읽을 수 있는 SuperGrok / Grok CLI 빌링 계정.

## 라이선스

[MIT](LICENSE). 저작자 SkyMin (`syacucloud`).
