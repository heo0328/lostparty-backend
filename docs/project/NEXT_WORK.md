# 현재 작업과 다음 실행

기준일2026-10-14. 현재그룹: **전투력 갱신 API/cache 구현·자동검증·로컬적용 완료, 계약 게시/Flutter 연결·실provider 인수 후속**.

## 기준 상태

- [Issue5](https://github.com/heo0328/lostparty-backend/issues/5), [Flutter동의](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166739099), [실행/정확한wire](../ISSUE_5_DEVELOPMENT.md), [계획](../ISSUE_5_COMBAT_POWER_PLAN.md), [공통기준](../GAME_DEFAULTS.md).
- [구현결과회신](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166983632)에서정확한wire·예산한계·후속을인계했다.
- feat/account-management(dev78a5494기준). 코드/계약/0003/문서 미커밋·미push,새구현/계약SHA없음. Backend 구현완료와 원격 인계를 구분한다.
- DEFAULT_MIN_ITEM_LEVEL=Decimal1700,20명input·TTL30분·회원별cache·POST/GET관찰상태·대표수치overlay·부분실패보존·quota80/동시2·lease/멱등·회원/등록/소유차수재검사 구현.
- 대상42개통과(9.29초,경고1개),마지막null레벨reason/retention/상수계약변경후3개통과(3.37초,경고1개). 처음22/중간33은이전검증으로구분,전체기존테스트재실행없음.
- 로컬API적용·OpenAPI전체일치PASS·health200·DB0003_power_cache·runtime키존재true,기존18테이블집계건수보존/새cache0 확인. 개발fixture/자료삭제/DB초기화없음.
- 실profile조회·Flutter전투력표시/역할snapshot우선·세션격리는미인수. 기존siblings4개성공을profiles실증으로확대하지않음.

## 다음 실행

1. 사용자commit/push승인범위로새구현/계약SHA를게시·Issue인계한다. 아직미게시인계약을Flutter가원격에서가져올수있다고안내하지않는다. 기존d3cb697은전투력새계약SHA가아니다.
2. Flutter는게시된계약으로POST/새 GET3필드·요청전용30초receiveTimeout·20명순차묶음/부분결과·1700선별을연결한다. profile없는값/실패/oldstale·deferred·로컬역할snapshot우선와로그아웃격리검증.
3. 사용자시험대상준비후실profile응답을safe형태로확인하고차이가있으면대상만보완한다. Flutter연결뒤신규전투력/캐시·관련실패인수를진행하며성공등록/이름시험반복없음.

## 한계·완료조건

20초는진입시처리예산/19초network결과대기+commit여유다. quota리셋sleep없음·초과대상deferred,blockingtransport의뒤늦은결과는DB쓰기없이폐기한다. OS/DB연결·응답전송까지정확히20초강제하는proxyharddeadline은아니며이한계를Issue에명시한다.

완료는계약게시/Flutter소비·미인증/인증전투력GET/캐시·부분실패의시각·상태와로컬역할자료보존인수다. #5OPEN. #4빈이름/등록실제결과·Flutterdev266a7e2는확인 완료·삭제후로컬보존잔여. #3장비/활동·#2[인증후속](../ISSUE_2_FOLLOWUP.md)은별도다. 운영배포/merge/Issue종료없음.

최신 [게시 대기 회신](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6167001322) 확인: 새 코드/계약 수정요청없음. 기존 Flutter Strict DTO는 새GET필드 거절하므로 새SHA 소비/DTO연결 전까지 기존 앱 호환완료로표시하지않는다. 사용자commit/push승인으로현재검증된작업을게시한다.
