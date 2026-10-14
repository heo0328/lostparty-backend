# 현재 작업과 다음 실행 계획

기준일: 2026-10-14. 현재 그룹은 **Issue #4 빈 이름 자동 표시 Backend 구현·대상16개 통과·새 계약 인계 후속**입니다.

## 목표·근거·범위

[Issue #4](https://github.com/heo0328/lostparty-backend/issues/4), [작업 계획](../ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md), [기존 실행 안내](../ISSUE_3_DEVELOPMENT.md), [원본 OpenAPI](../../openapi/openapi.yaml)가 기준입니다. #3의 기존 구현/보완을 다시 개발하지 않고 등록 구간의 준비·실provider 관찰·모바일인수·발견차이만 #4에서 추적합니다.

현재 브랜치 `feat/4-registration-integration`, 기준 `dev`의 `e807a6f002222cdff7beb07bfbe5cae65b97df43`. 사용자 승인으로 #3 구현/문서/헤더보완 및 이슈종료기록을 dev에 fast-forward 통합·push했습니다. 완료 feat/3-account-restoration은 local/remote 삭제, main은 e6c72e4 유지. #4 준비문서는 미커밋·미push입니다.

## 기준 상태

| 영역 | 상태 |
|---|---|
| Backend | 기존12업무API/0002 구현·로컬적용·dev통합 완료. 기반contract254cb5d/db0f3ae. 새 로컬 label 계약 구현(미커밋·미push) |
| 검증 | 이전전체114개+후속대상10개통과/106개미실행. 이번dev통합전OpenAPI전체비교·diff확인,기능테스트반복없음 |
| 실행/DB | 기존로컬source/health200·DB0002·인증데이터보존근거 있음. 이번Git작업에서서버/DB변경없음 |
| server key/실provider | local/runtime key설정 확인·접두사없음·health200. 수동진단CLI·대상13개검증완료. 사용자 live siblings 4개/parser passed,등록인수미실행 |
| Flutter | #4보고dev69d3aaa,두GET/로그인빈목록·로그아웃/로컬보존 및디자인기준확인. 등록쓰기UI 보고 미확인. 빈이름 최종요청6163006876 적용 |
| 이슈 | #1/#2 Completed, #3 OPEN(전체계정/장비·활동후속), #4 OPEN(등록관리실연동) |
| 운영 | 배포/외부공개·DB초기화·Firebase변경미실행 |

## 다음 실행 순서

1. [#4 준비 인계](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6162462300)에 dev통합·계약/보완SHA·기존근거·시험조건·key준비절차를게시했다. 새요구/환경변경이없으면완료검증을반복하지않는다.
2. 새 최종요청의 빈 label wire 계약을 적용한다(POST 생략/빈값 자동, PATCH 생략 유지/빈값 clear/null 거절). 지정이름 포함 전체 부계정 안정순서로 Flutter가 자동이름을 계산한다. 상세는 작업계획의 「최종 요청: 빈 이름 자동 표시 계약」. 새 commit SHA는 미발급이다. Flutter는디자인을유지해preview/등록/PATCH/DELETE/refresh의UI·Repository와동일key/payload복구·세션격리·예상503/409를연결한다. 장비증거인수를선행조건으로두지않는다.
3. 키 local/runtime 반영과 사용자 실 siblings 조회가 완료됐다. 관찰된 4개 행의 필드 타입/수치/중복/입력존재 검증을 통과했고 parser 수정은 필요 없다. 동일 자료를 다시 요청하거나 진단을 반복하지 않는다. [실검증 기록](../ISSUE_4_LIVE_VALIDATION.md)을 기준으로 Flutter 테스트를 진행한다.
4. 사용자명시동작으로검색→등록→두조회→표시명/main전환→refresh→제거→재조회를공동인수한다. Flutter로컬캐릭터/빌드보존은별도보고한다.
5. 재현된code/request_id·기대/실제결과로서버/계약차이를최소보완한다. 변경시계약유지/변경·구현SHA·실제대상검증을인계하고신규게시/통합은승인범위를따른다.

## 남은 입력·완료 기준

server key는 로컬/runtime 반영 완료. 실 siblings 관찰도 완료. 남은 입력은 명시등록관리테스트·Flutter쓰기연결결과입니다. 미준비는실증만보류하며 독립구현/연결을중단시키지않습니다. 완료는준비/실행버전·실provider근거/제한·등록변경갱신제거의GET반영과로컬보존인수기록입니다. Issue를임의종료하지않습니다.

장비challenge/소유권이전·활동/대표Flutter쓰기는후속그룹입니다. PROVIDER_EVIDENCE_PENDING/ROSTER_EVIDENCE_PENDING·suspect보류와기존인증6API/두조회API를보존합니다. 실기기/release·운영HTTPS/배포·탈퇴/약관·전체세션실인수는 #2 종료와별도잔여로유지합니다.

이번새코드는진단CLI/대상테스트이며미커밋·미push다. 13개대상테스트와키미준비CLI종료2·최신image schema일치를확인했다. 이전전체114/후속10은기존기록이다. 진단 구현 당시 외부호출은 없었고, 이후 사용자 실조회 1회 통과가 추가됐다. Backend agent의 개발DB쓰기·서버재생성·기존API변경은없다.

2026-10-14 키 설정 후 확인: local/runtime 존재 true·Bearer 접두사 false, local JWT 형태 3부분, health200. 이미 runtime 반영돼 API 재생성은 하지 않았다. 키 값/본문 출력·외부 호출·DB 쓰기 없음. 이후 사용자 수동진단 passed 결과를 확인했다. 다음은 Flutter 등록관리 연결/인수다.

Flutter 연결/인수 세부 요청 형식과 성공/재조회 기준은 작업 계획의 「Flutter 연결·사용자 인수 순서」를 따른다. 최신 이슈에 빈 이름 자동 표시 최종 요청이 추가돼 Backend 계약/구현을 보완했다. 새 wire 계약/구현 게시와 Flutter 연결/실인수를 다음 단계로 진행한다.

빈label 로컬API 적용 완료: OpenAPI 전체일치 PASS·health200·runtime키존재true·DB0002. 대상16개/27개미실행. 다음은 변경 commit/push 승인 범위의 게시 및 새계약SHA 전달→Flutter 새wire 연결/실제 인수→발견차이 보완. 개발자료 삭제/초기화 없음.
