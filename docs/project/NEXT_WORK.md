# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

## 현재 — 그룹 활동 캐릭터 후보 구현·개발 반영 완료

[개발 안내](../ISSUE_13_GROUP_CHARACTER_CANDIDATES_DEVELOPMENT.md) 기준으로 GET `/v2/groups/{group_id}/raid-room-character-candidates`와 검색 optional `group_character_candidates_token`을 구현했다. Flutter102 수용/[Backend103 보완](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339459589) 기준이다. 새token으로 전체후보 선택검증 후 실제T 방검색/페이지를 수행하며200/items=[]도선택유효·거절은선택보류다. role_family=null/Flutter기존카탈로그표시는합의대로유지한다.

최종28PASS/222.33초+보강2PASS/21.14초(중복1제외 고유29)·두프로필 OpenAPI 전체객체일치. 실제 API8000은168경로/DB0029·새이미지66e69545…/healthy다. 전후105표449행/전체내용지문·환경/키mount·보안/포트/command보존, DDL/초기화없음. 실제정상로그인HTTP·기기/F3전체·운영인수는미완료다. 구간 `0afd87932ab9b89a5d0976cf634daa5d6ef5a408` commit/push·실제원격SHA일치·[전체104번째 Backend · 후보 구현/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6340348412) 게시완료다.

## 최신 수신 — Flutter F3 코드/자동 검증 마감

[전체105번째 Flutter · F3 후보 연결/자동 검증 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6340688138)에서 `feature/raid-recruitment-scheduling` / `f6287404afd6273218255037c6cb4e419fb0313e` commit/push·원격일치 보고를 수신했다. Backend0afd879/실행168경로를 소비해 후보2열UI·정렬/명시더보기·검색token·페이지밖선택/stale재검증·회원/세션격리를 연결했다. 신규후보21+기존F3관련27 고유48PASS/변경Dart7파일분석0 보고이며 모두mock 검증이다. Backend에서 Flutter 소스/시험을 독립 재현하지 않았고 기존114/Backend29와 합산하지 않는다.

후보 출처/계약 보완 대기는 해소됐고 **F3 코드·자동 검증 구간 마감**, 실제 정상인증HTTP·실회원/기기 인수·운영 완료는 아니다. 새 Backend 수정/추가시험/동일정책 재채택 요청은 없다. 변화 없는 수신확인 댓글은 반복하지 않는다.

## 다음 Flutter — F4 주차별 관리

- 다음 단위는 F4 N특례·주차별 탈퇴/승계·위임/편성·관리다. F5일정/예약·F6완료/통합은 이후 미구현이다. 생성만C/N원자·이후T별독립과 기존과거7관계보존을 유지한다.
- 정상로그인 후보조회·실제2열/긴이름/글자크기·더보기/stale/회원전환·성능 확인은 미실행이며, 사용자 전체기능섹션 기기 인수와 별도 추적한다. 이미 보고한 같은 mock 시험/정책 수용을 다시 요청하지 않는다.

## 다음 Backend — 연결 차이 대응·현재 실행 유지

- Flutter 재현 가능한 계약/실행 차이가 있으면 같은브랜치에서 필요한구간만보완·검증/게시후회신한다. 이미수용한공개범위/계열·같은시험/정책채택을반복요청하지않는다. #19통계는별도후속이다.
- 재기동은 compose.yaml + compose.two-cycle.yaml/two-cycle image·factory를함께사용한다. 기본0023 앱/구worker를DB29에혼용하지않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를따른다.
- 지난주7관계의현재C/N검색제외는정상이며원본/persistent관계·한도자동해제없음. 기존비공개checkpoint는보존하며source23용도구를현재DB29에재실행/이전snapshotoverwrite하지않는다. 실제복구·운영변경/merge는별도범위확인이다.
