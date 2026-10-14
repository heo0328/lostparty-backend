# 현재 작업과 다음 실행 계획

기준일: 2026-10-14. 현재 그룹은 **Issue #3 로컬 Backend 구현·자동 검증 완료 후 계약 인계와 Flutter/실provider 검증**입니다.

## 근거·범위

[Issue #3](https://github.com/heo0328/lostparty-backend/issues/3), [Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159847616), [설계](../ISSUE_3_IMPLEMENTATION_PLAN.md), [실행/인계 안내](../ISSUE_3_DEVELOPMENT.md), [원본 OpenAPI](../../openapi/openapi.yaml)가 기준입니다. [협업 작업 단계](../API_COLLABORATION_WORKFLOW.md)에 따라 구현 가능한 영역을 먼저 완료하고 실검증 입력을 분리했습니다.

브랜치 `feat/3-account-restoration`, 기준 dev `e6c72e4`. 변경은 미커밋·미push이며 원격 계약/구현 SHA는 아직 없습니다. dev/main은 변경하지 않았습니다.

## 현재 상태

| 단계 | 상태 |
|---|---|
| 요구/계약 방향 합의 | A/B·버전·멱등·등록·대표·보존/제한 수용 회신 확보 |
| Backend 로컬 구현 | 12개 업무API, auth 재검사, 등록/전체설정/pagination, challenge/identity/소유권/audit, atomic 활동/대표, TTL/quota/summary합류 구현 |
| DB/원본 계약 | additive0002의11개테이블, 기존7경로/인증schema 보존·신규12operation 반영 |
| Backend 자동 검증 | 격리 PostgreSQL17 pytest114개 통과(기존46+판정/transport37+업무API31), 기존 경고1개. migration 전후 기존회원 행 보존·권한/경쟁/rollback/TTL 검증 |
| 로컬 API 적용 | 개발DB additive migration·API 갱신, 기존 인증6테이블 건수 보존, health200/미인증업무401·전체OpenAPI 일치 확인 |
| 원격 게시/계약 SHA 인계 | 미완료. [로컬 구현·검증 인계 댓글](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6160605157)은 게시했으며 원격 계약은 승인 범위 확보 후 진행 |
| Flutter 업무 API 적용 | 미확인. #3 계약 연결/화면 테스트는 후속 |
| 실provider/장비 | 키/schema/해제표현·quota/지연 미확인. live확정은pending 증거보류, 감소roster 자동missing/이전 보류 |
| 운영 배포 | 미실행 |

mock proof는 pytest dependency에서만 주입하며 공개 API/임의env 우회가 없습니다. 소유권 transaction은 구현·자동 검증했고 실제 미실증 입력의 성공 판정만 보류합니다. 현재 game 쓰기는 짧은 전역advisory lock으로 직렬화하며 네트워크는 밖에서 수행합니다. 처리량 개선은 실사용 근거에 따라 후속 검토합니다.

## 다음 실행

1. 사용자 승인으로 작업 브랜치의 변경을 commit/push하고 원격 OpenAPI/구현 SHA로 정확히 인계한다. dev/main 병합은 이번 승인에 포함하지 않으며 별도 후속이다. 미게시 로컬 파일을 원격에서 사용할 수 있다고 안내하지 않는다.
2. Flutter가 사용한 계약버전을 기록하고 가능한 빈등록/CRUD/상태/페이지·세version/409/유실·삭제replay·로컬보존 흐름을 연결·테스트한다. Backend는 결과를 재현·수정·대상회귀로 검증한다.
3. 사용자·Backend가 서버 LOSTARK_API_TOKEN을 안전한 로컬 설정으로 준비한다. 값은 Issue/앱에 공유하지 않는다. Backend가 실제 siblings/Armory schema·수치/null·장비해제·실quota/지연을 확인한다.
4. 실증 후 adapter 품질판정을 보완하고 사용자 수동 장비조작으로 실제 인증/이전·누락 관찰 기준을 공동 검증한다. 불완전roster 이전/자동missing은 합의한 근거가 생길 때만 허용한다.
5. 실provider·Flutter 테스트에서 발견된 계약차이/오류를 Issue에 기록하고 구현·OpenAPI·인계예제를 함께 수정한다. 운영배포/DB초기화/Firebase변경으로 확대하지 않는다.

## 후속 입력과 완료 기준

작업 브랜치 commit/push는 사용자 승인됐다. 남은 입력은 dev/main 통합 승인 범위, Flutter 계약소비/테스트 결과, 안전한 server key 준비와 실제provider 근거입니다. 같은 미확인 자료를 반복요청하며 Backend 구현을 미루지 않습니다. 실제인수/Flutter적용/운영완료는 자동테스트 통과와 별도입니다. Issue는 임의 종료하지 않습니다.

#2 인증 원본 SHA `519c609495966a3d785c6671c09bf513b28875a6`은 기존인증 기준입니다. #3의 새로운 업무 계약 SHA로 사용하지 않습니다. #2의 전체세션/실기기/release 인수는 기존잔여작업으로 보존하며 Flutter 최신 회신의 로그인/재실행/로그아웃 성공보고는 독립 실검증의 참고 근거입니다.
