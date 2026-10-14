# 현재 작업과 다음 실행

기준일2026-10-15. 현재그룹: **회원 개인 Lost Ark 키 Backend 구현·검증·로컬 적용 완료, 원격 인계 후 Flutter 연결**. #6 설정 인수/Git 게시 대기는 별도 유지.

## 현재 기준

- feat/member-settings,기준dev4eb23f5. [Issue6](https://github.com/heo0328/lostparty-backend/issues/6)·[계약정리/착수](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6168785700)·[정확한계약/후속](../ISSUE_6_MEMBER_SETTINGS.md).
- GET/PUT /v1/me/settings: flag+version,기본false/version1·read-onlyGET·명시booleanPUT·expected_version/UUIDv4 key·실제변경만version증가/로그아웃새session보존 구현. 0004는회원별최소1테이블추가,기존회원backfill없음.
- 새원본OpenAPI는기존path/DTO·auth/game정책전체보존,새GET/PUT/DTO/회원설정정책만추가. 원정대설정과별도다.
- 대상22개통과(9.61초,기존경고1개),로컬API/DB0004·OpenAPI일치/health200·기존19테이블건수보존/새table0. 실제Flutter기기변경/재설치인수는미실행. 기존등록/이름/전투력시험반복없음.
- Backend 구현·계약 SHA `79255f0f77602c26a215bf0340331eb697417ff4`, feat/member-settings push 완료. [인계](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6168992033). dev/main 미병합.
- [Flutter 최신 회신](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6170276194): 같은 계약 소비, 기존 캐릭터관리의 스위치 즉시 저장 연결 완료. 전체1219 테스트 후 보완 관련32개·최종분석0·debug APK 성공 보고. Flutter feature/member-settings는 미커밋·미push·dev 미반영이며 실제 서버 저장/사용자 복원 인수는 미실행. 새 Backend 수정 요청 없음.

## 다음 실행

1. Flutter/사용자가 새 APK에서 ON/OFF 즉시 저장→관리화면 재진입→동일 Google 회원 재로그인, 가능할 때 새환경 복원을 확인한다. 실제 서버 저장·복원 결과와 미실행 항목을 구분한 회신이 완료 조건이다. 새환경 로컬 캐릭터 부재에 따른 스위치 노출과 서버 설정 보존은 구분한다.
2. Flutter가 현재 구현을 게시하고 적용 SHA·브랜치·push/dev 반영 상태를 회신하면 기록한다. Backend는 사용자 인수 결과 또는 새 서버 차이를 기다리며, 동일 계약의 반복 테스트나 추가 자료 요청은 하지 않는다.
3. 전체Armory/역할별자동갱신·나이스단OFF저장빌드·선호역할/표시순서의전체복원계약은실행안내의후속표에보존. 이번flag설정만으로자동갱신/전체복원완료로확대하지않는다.

#5 전투력39188d5와Flutter6beb55e/devccc6b23의게시/사용자3흐름은확인완료·dev통합. #4로컬보존/#3장비·활동/#2[인증후속](../ISSUE_2_FOLLOWUP.md)은별도. #6OPEN유지,자료삭제/초기화·운영배포·main변경없음.

## 회원별 Lost Ark 키 #7 — 다음 실행

[Issue #7](https://github.com/heo0328/lostparty-backend/issues/7)·[계약 수용](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6172158382)·[실행/정확한 계약](../ISSUE_7_DEVELOPMENT.md). 현재 feat/member-settings를 유지하고 회원 키 GET/PUT/DELETE·AES-GCM/HMAC·전 외부 호출 전환·회원/키 버전 cache/lease와 늦은 결과 차단·token별 quota를 구현했다. 공용 JWT 설정/실행환경 제거·암호화파일 준비 완료, 기존 공용 키 자동 회원 등록 없음. DB0005·기존20테이블 건수 보존·새 credential0·health/계약일치PASS, 대상180개 통과.

1. 검증된 구간을 인계 규칙으로 1회 commit/push·원격 확인하고 같은 Issue에 실제 구현/OpenAPI SHA·branch/push·dev 미병합·검증과 실미확인을 전달한다. 게시 결과는 같은 Issue 최신 인계 댓글이 기준이다.
2. Flutter가 원격 계약으로 명시 키 저장/교체/삭제와 상태·업무 오류·멱등/키변경·회원 격리를 연결하고 적용SHA/검증 결과를 회신한다. 로컬키 UX 협의는 Backend 대기 사유가 아니다.
3. 사용자가 앱에서 개인 키를 직접 등록하고 실제 서버 조회를 확인한다. 키를 채팅/Issue로 요청하지 않는다. 등록 성공은 암호화 저장 완료이며 provider 유효성 증명이 아니다. actual provider/사용자 확인은 현재 미실행이다.

#6은 기존 연결/자동검증 보고 확인·Flutter 게시/사용자 인수 대기를 보존한다. 전체빌드자동갱신·역할Snapshot 저장·로컬직접조회 제거·장비proof 보류 해제·운영배포/Issue 종료는 이번 범위가 아니다. dev/main 미병합.
