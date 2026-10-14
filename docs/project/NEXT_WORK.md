# 현재 작업과 다음 실행 계획

기준일: 2026-10-14. 현재 그룹은 **Issue #4 Backend 게시 완료·Flutter 새 계약 연결/실제 등록관리 인수 후속**이다.

## 현재 기준

- [Issue #4](https://github.com/heo0328/lostparty-backend/issues/4), [작업 계획](../ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md), [실검증 안내](../ISSUE_4_LIVE_VALIDATION.md), [원본 OpenAPI](../../openapi/openapi.yaml).
- 브랜치: `feat/4-registration-integration`(origin 동일 추적). 새 구현·계약 SHA: `d3cb697bb6ebb988b63bd99c588bc1b64a93650d`. 사용자가 commit/push를 승인해 게시했다.
- dev는 #3 통합 `e807a6f`, main은 `e6c72e4`. #4를 dev/main에 병합하지 않았다. 이전 완료 #3 브랜치는 로컬/원격 정리됐다.
- 기존12개 업무 API/DB0002 유지. 새 label 계약: POST 생략/빈값은 `""`, PATCH 생략은 유지/빈값은 clear/null 거절. Flutter가 전체목록의 안정 부계정 순서(지정이름 포함)로 표시이름 계산. 새 필드/endpoint/migration 없음.
- 로컬 API에 새 label 구현 적용, OpenAPI 전체일치 PASS·health200·runtime키존재·DB0002 확인. 키 값 출력 없음.
- 대상 검증은 빈이름/관련회귀16개 통과·27개 미실행, 진단도구13개 통과. 기존 전체114개/lease후속10개는 이전 실행이며 전체 재실행으로 표시하지 않는다.
- 사용자 실제 siblings 4개/parser 통과 확인. 소유권·roster전체성 증명과 실제 업무 API 등록관리 성공은 별도다.
- Flutter 마지막 확인 기준 dev69d3aaa의 두GET/로그인빈목록·로그아웃·로컬보존 보고. 새 등록쓰기/빈이름 wire 연결·실인수는 아직 보고 미확인.

## 다음 실행

1. Flutter가 새 계약 SHA `d3cb697bb6ebb988b63bd99c588bc1b64a93650d`를 소비해 확정 디자인의 preview/등록/PATCH/DELETE/refresh UI·Repository를 연결한다. 기존254cb5d를 빈이름 계약 SHA로 사용하지 않는다. [최종요청](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6163006876)·작업계획의 요청형식/재시도/전체목록표시 규칙을 따른다.
2. 적용 commit/소비SHA·자동검증·실제 사용자 시험/미실행을 이슈 댓글에서 확인한다. 키나 동일 siblings 샘플을 다시 요청하지 않으며 장비 인증을 선행조건으로 두지 않는다.
3. 사용자 명시동작으로 검색→이름미입력등록→두GET→지정이름변경/빈이름전환→본부전환/번호→refresh→명시제거→재조회를 인수한다. Flutter 로컬 캐릭터/빌드 보존 보고는 별도로 확인한다.
4. 재현된 동작·기대/실제·status/code/request_id로 서버차이가 확인되면 해당 부분만 보완하고 대상검증/계약영향을 인계한다. 미관찰 오류는 기존 격리 검증과 구분한다.

## 완료·후속 경계

이슈 #2의 나중에 구현할 정책 기능과 미확인 인수는 [인증 후속 목록](../ISSUE_2_FOLLOWUP.md) AUTH-F01~F06으로 보존한다. 현재 #4 진행을 유지하며 인증 후속 착수 시 항목별 Issue/계약·담당·완료 기준으로 전환한다. #2 종료를 후속 구현 완료로 해석하지 않는다.

Backend 구현/모의검증/실 siblings 관찰/계약 게시가 완료됐다. Flutter 연결·사용자 등록관리 인수·발견차이 보완이 남아 #4는 OPEN이다. #1/#2는 Completed, #3은 전체 계정/장비·활동 후속으로 OPEN이다. 장비 challenge/소유권·활동/대표 Flutter 쓰기, 실기기/release·전체세션실인수·운영HTTPS/배포·탈퇴/약관은 별도다.

이번 commit/push로 개발 DB 초기화·자료삭제/Firebase변경·운영배포는 수행하지 않았다. 검증이 완료된 코드에는 추가 변경이 없어 테스트/외부조회/서버재생성을 반복하지 않았다. 게시 기록 문서 커밋은 동일 구현·계약 SHA를 유지한다.
