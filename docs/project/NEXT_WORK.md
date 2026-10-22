# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

## 현재 — 그룹 활동 캐릭터 후보 구현·개발 반영 완료

[개발 안내](../ISSUE_13_GROUP_CHARACTER_CANDIDATES_DEVELOPMENT.md) 기준으로 GET `/v2/groups/{group_id}/raid-room-character-candidates`와 검색 optional `group_character_candidates_token`을 구현했다. Flutter102 수용/[Backend103 보완](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339459589) 기준이다. 새token으로 전체후보 선택검증 후 실제T 방검색/페이지를 수행하며200/items=[]도선택유효·거절은선택보류다. role_family=null/Flutter기존카탈로그표시는합의대로유지한다.

최종28PASS/222.33초+보강2PASS/21.14초(중복1제외 고유29)·두프로필 OpenAPI 전체객체일치. 실제 API8000은168경로/DB0029·새이미지66e69545…/healthy다. 전후105표449행/전체내용지문·환경/키mount·보안/포트/command보존, DDL/초기화없음. 실제정상로그인HTTP·기기/F3전체·운영인수는미완료다. 구간 `0afd87932ab9b89a5d0976cf634daa5d6ef5a408` commit/push·실제원격SHA일치·[전체104번째 Backend · 후보 구현/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6340348412) 게시완료다.

## 현재 계약 구간 — 사전 참가 표시 메타 초안1 작성 / 다음 Flutter 대조

[사전 참가 세션 표시 메타 초안1](../ISSUE_13_PREJOIN_SESSION_DISPLAY_DRAFT.md)·[검토 JSON Schema/합성 예시](../design/issue13-prejoin-session-display.draft.json)를 작성했다. 기존3GET에optional `include_session_display` query·opt-in때만data.session_display를추가하는제안이다. 생략/false의기존응답/토큰·쓰기body/원ACK는유지하고새token의내부버전표지/표시digest를결합한다.

existing는실제T/session시각·상태/revision·required/permission을ID로직접제공한다. opening_preview는prospective cycle/generation의일정의도이며session_id=null·가짜ID/자동시간확정·예약없음, none은decline/already_open noop이다. 실제미정과duration미상preview·다중one_of/each/coordinated/unscheduled/주차전체를구분한다.

다음 **Flutter**: opt-in/닫힌DTO·세종류/선택의미·prospective세대비교·원ACK보존·1MiB초과처리제안을소비대조한다. 충돌없으면Backend구현/격리검증·게시/개발실행/소비SHA인계다. 같은F1~F4/후보·F5독립시험/정책을반복요청하지않는다.

검증은schema/ref/닫힌객체·11예시/11거절fixture/opt-in존재3경계와KST/시각·상태조합의문서검사다. 실제HTTP/DB·token/동시성시험이아니다. 앱코드/실행OpenAPI·서버168경로/DB29·기본고정계약불변이며아래요청접수는이력이다.

## 최신 수신 — F4 마감·F5 독립 연결 / 사전 참가 표시 메타 보완

[전체106번째 Flutter F4](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6342159361)는0c850294 commit/push·최종단일93mock PASS/분석0 보고, [전체107번째 Flutter F5](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6343179198)는f2e09c9d commit/push·고유130mock PASS(127묶음후추가3포함일정27재실행/기존103재사용)/분석0 보고다. F4는코드/자동검증마감, F5는일정/예약독립연결완료이며사전참가시간표시는미완료다. Backend에서Flutter소스/시험/원격SHA를독립재현하지않았고실제HTTP·실회원/기기인수로확대하지않는다.

[전체108번째 Backend · 표시 메타 요청 확인](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6343260776)에현재context/DTO·privateplan권한을정적대조한결과를회신했다. SessionChoice는ID/required/join_deadline/permission만있고continuation/opening은target_session_ids만제공한다. 공개시각목록순서로ID를추정하거나참가전privateplan을무조건조회하는것으로대체하지않는다.

다음 **Backend**: 기존admission/continuation/opening context권한내선택session의실제T/ID·시작/종료(nullable)·상태/표시revision 계약을작성해Flutter대조한다. context token/일정revision·generation binding, 미정·변경/삭제/접근상실·prospective개방의미생성session표시/선택경계를정의한다. 정확한wire/경로는미확정이며개인제출표/타방busy공개·권한확대는포함하지않는다.

## 다음 Flutter — F5 독립 구현 유지·표시 메타 계약 대기

- 사전일반참가/캐릭터변경/N특례·개방확인창의실제시각/미정표시부분만Backend계약보완대기다. F1~F4/후보·이미참가한방의F5일정/제안/본인확인연결은유지한다.
- 표시계약합의→Backend구현/검증·게시/실행SHA인계후네이티브가해당부분을연결/검증·회신한다. F6완료/정정·종료/재개통합은미구현이다.
- 정상로그인HTTP·실회원·기기표시/성능인수는미확인이다. 기존mock검증/BackendDB시험/동일정책채택을반복요청하지않는다.

## 다음 Backend — 연결 차이 대응·현재 실행 유지

- Flutter 재현 가능한 계약/실행 차이가 있으면 같은브랜치에서 필요한구간만보완·검증/게시후회신한다. 이미수용한공개범위/계열·같은시험/정책채택을반복요청하지않는다. #19통계는별도후속이다.
- 재기동은 compose.yaml + compose.two-cycle.yaml/two-cycle image·factory를함께사용한다. 기본0023 앱/구worker를DB29에혼용하지않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를따른다.
- 지난주7관계의현재C/N검색제외는정상이며원본/persistent관계·한도자동해제없음. 기존비공개checkpoint는보존하며source23용도구를현재DB29에재실행/이전snapshotoverwrite하지않는다. 실제복구·운영변경/merge는별도범위확인이다.
