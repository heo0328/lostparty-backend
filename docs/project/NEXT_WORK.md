# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

## 현재 — 그룹 활동 캐릭터 후보 구현·개발 반영 완료

[개발 안내](../ISSUE_13_GROUP_CHARACTER_CANDIDATES_DEVELOPMENT.md) 기준으로 GET `/v2/groups/{group_id}/raid-room-character-candidates`와 검색 optional `group_character_candidates_token`을 구현했다. Flutter102 수용/[Backend103 보완](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339459589) 기준이다. 새token으로 전체후보 선택검증 후 실제T 방검색/페이지를 수행하며200/items=[]도선택유효·거절은선택보류다. role_family=null/Flutter기존카탈로그표시는합의대로유지한다.

최종28PASS/222.33초+보강2PASS/21.14초(중복1제외 고유29)·두프로필 OpenAPI 전체객체일치. 실제 API8000은168경로/DB0029·새이미지66e69545…/healthy다. 전후105표449행/전체내용지문·환경/키mount·보안/포트/command보존, DDL/초기화없음. 실제정상로그인HTTP·기기/F3전체·운영인수는미완료다. 구간commit/push·실제원격확인후같은Issue에소비SHA를인계한다.

## 다음 Flutter — 후보 UI 연결

1. 게시될소비SHA의실행OpenAPI/개발안내를기준으로단일그룹context→후보GET→회원별2열카드/내부레벨순·명시더보기를연결한다. 그룹snapshot대표명/null·계열null/기존카탈로그·역할별전투력출처를구분한다.
2. 같은member_ref/alias와canonical UUID로선택하고검색token을함께보낸다. 첫페이지에선택UUID가없다고삭제하지않는다. 후보변경은새첫페이지token+동일선택검색최대1회/200빈결과유효·반복stale보류, 자동전페이지/빈배열확대/새UUID대체없음.
3. 사용SHA·확인/실패/미확인을같은#13에회신한다. 실제로그인/기기결과는mocked HTTP/Backend격리검증과분리한다. 기존독립F3구현은유지하고후보부분적용전F3전체완료로표시하지않는다.

## 다음 Backend — 연결 차이 대응·현재 실행 유지

- Flutter 재현 가능한 계약/실행 차이가 있으면 같은브랜치에서 필요한구간만보완·검증/게시후회신한다. 이미수용한공개범위/계열·같은시험/정책채택을반복요청하지않는다. #19통계는별도후속이다.
- 재기동은 compose.yaml + compose.two-cycle.yaml/two-cycle image·factory를함께사용한다. 기본0023 앱/구worker를DB29에혼용하지않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를따른다.
- 지난주7관계의현재C/N검색제외는정상이며원본/persistent관계·한도자동해제없음. 기존비공개checkpoint는보존하며source23용도구를현재DB29에재실행/이전snapshotoverwrite하지않는다. 실제복구·운영변경/merge는별도범위확인이다.
