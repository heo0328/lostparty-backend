# 현재 작업과 다음 실행

기준일2026-10-14. 현재그룹: **회원별 나이스단 자동 갱신 허용 설정 Backend 완료·게시 후 Flutter 연결/인수**.

## 현재 기준

- feat/member-settings,기준dev4eb23f5. [Issue6](https://github.com/heo0328/lostparty-backend/issues/6)·[계약정리/착수](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6168785700)·[정확한계약/후속](../ISSUE_6_MEMBER_SETTINGS.md).
- GET/PUT /v1/me/settings: flag+version,기본false/version1·read-onlyGET·명시booleanPUT·expected_version/UUIDv4 key·실제변경만version증가/로그아웃새session보존 구현. 0004는회원별최소1테이블추가,기존회원backfill없음.
- 새원본OpenAPI는기존path/DTO·auth/game정책전체보존,새GET/PUT/DTO/회원설정정책만추가. 원정대설정과별도다.
- 대상22개통과(9.61초,기존경고1개),로컬API/DB0004·OpenAPI일치/health200·기존19테이블건수보존/새table0. 실제Flutter기기변경/재설치인수는미실행. 기존등록/이름/전투력시험반복없음.
- 승인된네이티브인계용게시규칙으로현재작업구간을1회commit/push하고원격확인후같은Issue에실제구현/계약SHA를인계한다. 해당SHA는게시결과댓글이기준. dev/main통합은미수행.

## 다음 실행

1. Flutter가원격게시계약SHA로회원설정GET/명시PUT·조회실패와false구분·충돌GET/새결정·같은key복구/회원캐시격리를연결한다. UI위치·저장중/실패안내/앱실행UX는Flutter와사용자범위다.
2. Flutter적용SHA/자동검증과사용자true/false재조회·로그아웃재로그인/새환경복원을분리해보고하면확인하고새서버차이만보완한다. 구현/자동검증과실제재설치시험완료를혼동하지않는다.
3. 전체Armory/역할별자동갱신·나이스단OFF저장빌드·선호역할/표시순서의전체복원계약은실행안내의후속표에보존. 이번flag설정만으로자동갱신/전체복원완료로확대하지않는다.

#5 전투력39188d5와Flutter6beb55e/devccc6b23의게시/사용자3흐름은확인완료·dev통합. #4로컬보존/#3장비·활동/#2[인증후속](../ISSUE_2_FOLLOWUP.md)은별도. #6OPEN유지,자료삭제/초기화·운영배포·main변경없음.
