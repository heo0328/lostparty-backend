# 캐릭터 전투력 수집·캐시 작업 계획

기준: [Issue #5](https://github.com/heo0328/lostparty-backend/issues/5), 사용자1700이상기준·공통상수 적용/작업착수지시. 브랜치 feat/account-management, 기준 dev78a5494. 미커밋/미push.

## 확정 범위와 독립 구현

기본 사용 최소레벨은 [앱 기본값](../../reference/GAME_DEFAULTS.md)의 DEFAULT_MIN_ITEM_LEVEL=Decimal("1700"). 기본 전투력수집은 해당등록의1700이상캐릭터를선별한다. 원정대전체GET/등록·장비인증·활동권한은별도다. 공식100회/min과기존Backend공유80회/min·transport동시2를구분하고 새조회가공유제한을우회하지않는다.

공통상수/수집대상선별과신뢰경계profile파서를구현했다. 서버명+캐릭터명일치·쉼표/유한수치·음수거절·0/미제공구분은 기존numberparser를재사용한다. 아직REST/service/cache/DB연결은없다.

## 계약 검토 이력 — Flutter 동의 후 구현

- POST /v1/me/game-accounts/{registration_id}/combat-power/refresh: 로그인Bearer+UUIDv4 Idempotency-Key, body characters:[{server_name,character_name}]. 순서유지중복제거,입력상한20명제안. 6명은고정하지않는다. 20은전원수집상한이아니라하나의요청크기다.
- 현재등록의현재roster소속인지먼저전체검증. 범위밖400·타인/삭제404·소유상실표시조회는본인등록preview만허용제안. 미인증에canonicalID/소유권/활동을생성하지않는다. 기본1700미만/null은skipped로외부호출없음.
- 캐시TTL30분,회원별서버명/캐릭터명키의작은전투력캐시로미인증/인증모두GET에overlay. 원문profile저장없음. 기존canonical정상값도보존. GET은읽기만한다. 대표요약도동일cache사용.
- 결과items별combat_power/power_fetched_at/power_stale와status(updated,cached,unavailable,failed,skipped,deferred) 및 고정reason. 수치미제공/실패는이전정상값과성공시각보존·stale=true,최초값없음null,0은정상값. 최신시도/미제공확인시각은정상값시각과분리한다.
- 전체요청deadline20초·최대동시2·공유80회/min quota및기존3/5timeout재사용. 예산내미처리대상은deferred,다음묶음으로확장. 캐시hit는quota소모없음. 네트워크동안DBlock없음.
- 같은키/body는완료결과replay. request30초lease/generationfencing유지. profile조회merge는기존lease패턴재사용/최소확장검토. 기록직전회원/session/등록삭제·version/roster/소유차수를재검사해409와rollback. 전투력적용만으로등록/소유권/settings revision을올리지않는다.
- 최종request/response/status/stale/GET상태필드·공용cache구조는Issue에서소비가능여부를확인후OpenAPI/DBmigration/service/router/GET구현으로진행한다. 여기적힌정책안은API구현완료가아니다.

## 다음 작업·검증 경계

1. Issue에사용자기준/상수와독립구현결과·정확한wire검토안을회신한다. Flutter는대상선별·묶음/부분결과·표시캐시소비영향을확인한다.
2. 합의된최소cache/migration·갱신/GET를구현하고캐시hit·미인증nullID·부분실패/이전값보존·범위/상한/멱등·quota·등록/회원변경후늦은반영을대상검증한다. 전체기존테스트반복없음.
3. 키/사용자시험대상준비후실profile응답을식별정보없이대조하고 차이가있으면해당parser만보완한다. Flutter연결후신규전투력·cache/부분실패·로컬역할snapshot우선/로그아웃격리만실인수한다.

장비/소유이전·활동/대표·전투력역할분석·전체빌드서버저장·큐/polling·자료이관/삭제·DB초기화/운영배포는제외. 실증대기를권한/DB독립구현전체중단사유로두지않는다. commit/push는별도사용자승인범위다.

착수/확인댓글: https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166675659. 독립대상22개통과(2.59초,기존경고1개),OpenAPI전체일치. 실제GET전투력/실profile/DBcache는아직미구현·미실행이다.

## Flutter 동의 후 실행

[6166739099](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166739099)에서1700/20명/부분결과·cache방향동의. 0003 캐시테이블·POST/GET상태/대표overlay·quota/lease/시간예산·권한재검사 구현. 위 미구현/미합의 문구는착수당시이력이며정확한최신wire/실행한계는 [실행안내](ISSUE_5_DEVELOPMENT.md)를따른다. 미커밋/미push·새SHA없음은유지.

## 2026-10-14 게시 완료

사용자 승인으로 `feat/account-management`에 commit/push 완료. 실제 구현·원본OpenAPI SHA: `39188d5dca2d394f4e8b3fcbfe332274812285bf`. 앞선 미커밋/미push·새SHA없음 설명은 게시 전 이력이며 현재 Flutter 소비 기준은 이 SHA다. dev/main 병합·배포·Issue종료는 하지 않았다. 기존42개/후속3개·로컬0003/API 적용 근거 유지,실profile/Flutter신규인수후속. 게시기록후속은파일끝공백정리와문서상태만 바꾸며새API동작/계약변경없음.

## 2026-10-14 dev 통합·정리

사용자 승인으로 #5작업/문서·인계규칙을 dev87751537bd63f13605fb8f0eacbca749c0898285에fast-forward 통합·push했다. 완료 feat/account-management는로컬/원격삭제. 위작업브랜치/미통합 설명은당시이력이며실제구현/계약39188d5는유지된다. Flutter연결·사용자3흐름은확인됐고Git게시SHA미회신/별도미확인범위는후속이다. 이번통합에코드/계약추가변경없음·반복검증없음.

2026-10-14 [Flutter Git인계](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6168115419) 추가확인: 구현6beb55e3f6f301873d200ff8cbfd6a764d33f547·dev통합ccc6b23f24c1f438c79ce683a8c9f3af35c8af06·push완료보고,소비39188d5유지. 앞선Git미회신대기는해소됐다. 자동1204/후속70·사용자3흐름근거유지/추가Backend요청없음. 다음나이스단설정/앱실행1회자동갱신은설계후보이며현재수동API인수·새API구현과구분한다.
