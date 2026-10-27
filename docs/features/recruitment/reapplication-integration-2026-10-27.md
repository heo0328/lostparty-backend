# 모집 재신청 보완 브랜치 통합 기록 — 2026-10-27

**통합 결과:** 문서eb8c409를 push한 뒤 [PR28](https://github.com/heo0328/lostparty-backend/pull/28)을 이력 보존 merge해 dev `41a47ed2ae0a0e2e4d6356b885bfd6a589b048aa` 원격 반영을 확인했다. 병합 트리와 PR head 전체 파일 동일, 현재 checkout dev·완료 수정 브랜치 로컬/원격 삭제·미완료 활동 선택 브랜치 보존. main18830c2·실행 API/DB·AWS는 변경하지 않았다. 아래 병합 예정은 문서 게시 당시 계획이며 실제 결과는 이 문단과 DEV_LOG를 따른다.

작업 구간은 **개인 완료 탈퇴 후 다른 캐릭터 재신청 정합성 보완·1차 인수 마감**, 구현 브랜치는 `fix/raid-recruitment-reapplication`이다. 사용자 지시로 이 브랜치의 코드·DB 제약·계약·검증·개발 반영·Native 기기 인수·Issue13 종료를 최신화하고 `dev`에 이력을 보존해 병합한다. 이전 모집 전체 통합은 [기존 체크포인트](integration-checkpoint-2026-10-27.md)다.

## 구현과 공개 계약

| 변경 | 처리·보존 기준 |
|---|---|
| 재신청 판정 | 개인 완료 탈퇴 뒤 과거 completed Assignment 때문에 후보는 있어도 context가 stale로 거절되는 흐름을 재현했다. 실제 주차/현재 세대의 최신 종료 CM·해당 revision 불변 이벤트·전체 Assignment 바인딩과 종료 상태를 공통 확인한다. |
| 새 참가 설치 | 증명된 종료 이력과 새 참가를 분리해 새 CM ID/가입순번·Assignment/바인딩을 만든다. 기존 완료 캐릭터·직업/레벨/전투력·주간 점유·정원/한도·권한·동의/CAS·원ACK는 유지한다. |
| 과거 기록 | 과거 CM/배정/완료·동의/해제 예약·N 업무 행을 보존한다. 종료 snapshot을 우선하고 이전 snapshot 없는 자료는 과거 Assignment에 귀속된 불변 해제 예약에서 읽어 재사용된 현재 일정에 덮이지 않게 한다. |
| DB0033 | `0033_reapplication_history`는 현재 Assignment 부분 유일 인덱스에서 completed만 제외한다. active/stopped 중복 차단 유지·행 변환/삭제/backfill·새 테이블/컬럼 없음. readiness·베타·worker/관련 서비스는0033을 명시 지원하고 미지 head는 거절한다. |
| API | 현재178경로/199동작·기본116/133·wire2/profile1, 기존 요청/응답/ACK·오류 코드는 유지한다. 현재 OpenAPI의 스키마/재참가 정책 메타데이터만 보완했다. |

상세 [구현/검증](participation/reapplication-history-fix-plan.md)·[후보 소비 계약](participation/candidate-contract.md)을 따른다.

## 게시·개발 반영

| 기준 | 정확 값·상태 |
|---|---|
| 분기 기준 | dev/main `18830c21bd260592a5455526b7565a3a7ef7a1a9` |
| 구현 | `c1f86d8948601781e6c593341899c07ce83f1b68` push/원격 확인 |
| 반영 기록 | `3e905ec187fa293191719a418ebb3faed4671a7f` push/원격 확인 |
| 인수·종료 기록 | `59f040ee47480d42ef8e29c835eed351407028e9` push/원격 확인 |
| 실행 API | `sha256:581a1a5ed2566061d4c1d23a83d622e36ed9f6da166666b74c1e76a28dfe13f2` / sourcec1f86d8 / DB0033 |

후보 소스262파일/고정 runtime31/두 OpenAPI 확인 후 API/동일 worker 중지→0033 DDL→새 API 시작을 완료했다. DDL 전후112업무표1,883행·전체 sequence 값 동일, DB 컨테이너/이미지/볼륨/환경과 API 환경/명령/보안/포트/로그·읽기 전용 키/내용 해시를 유지했다. DB33 이후 구420 이미지만 재시작하지 않고 장애 시 자료/구조를 유지한 전진 수정이다. [실제 개발 반영](../../engineering/operations/reapplication-history-rollout.md)·[실행 집계](../../engineering/operations/records/reapplication-history-rollout.json)를 따른다.

## 검증·인수·종료

- 격리 PostgreSQL의 고유20PASS(신규14/관련 기존6). 수정 전 stale 실패 재현, 수정 후 신청/승인·직접가입·새 ID/과거/N 불변·pending 무점유·자격 거절·동시성/롤백/원ACK·기존 자료0032→33·HTTP/복수 아이템을 확인했다.
- 두 OpenAPI 전체/기존 paths·components 보존·닫힌 bundle·130예시/원ACK32/음성3 확인. 실행 소스262/runtime31·HTTP6·READONLY2계정 C/N 목록/한도 합집합 일치·anchor34·현재 종료 근거13·health/3주기 작업·확인 로그 ERROR0이다. 합성 시험과 실제 서버 읽기·인증거절 HTTP를 정상회원 쓰기/기기 성공으로 합산하지 않는다.
- [전체186/187 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437319946)에서 사용자 기기의 과거 기록 보존·다른 캐릭터 신청→가입과 오류창 가독성 확인, [전체189 표시 인수](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437895407)·[전체190 최신 인수표](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418)에서 보고된 정상 흐름/표시 기기 통과를 수신했다. Native 구현cf75ea75·문서bd3b6e58 push/자체시험 보고는 Backend 독립 시험과 구분한다.
- 사용자 명시 승인으로 [전체192 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)을 게시하고 Issue13 `closed/completed`를 확인했다. 추가 Backend 구현 요청은 없다.

현재 통합은 검증된 구현 이후 코드/DB/계약 변경이 없는 문서 정리이며 기존20PASS·배포 검증을 재사용한다. 문서 참조/diff와 Git 포함 관계·원격 SHA를 확인하며 전체 회귀·DB 복원·서버 재시작·실회원 명령을 반복하지 않는다.

## 차후 보완과 Git 통합 범위

[전체191 Flutter 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)의 정밀도 소비·다음 주 개방 알럿·제안 발견성/웹소켓 등은 [차후 보완 대장](follow-up-backlog.md)에 담당/재착수 조건으로 남겼다. 현재 착수나1차 인수 선행 조건이 아니며 해당 별도 구간 재시작 때 최신 계약/코드·UX 확인 및 필요한 전용 Issue로 추적한다. 미수행 성능/실회원 원ACK 키 검증을 통과로 바꾸지 않는다.

이번 승인 범위는 **문서 최신화·이 브랜치의 dev 병합·commit/push**다. dev는 현재18830c2의 후손으로 코드 충돌이 없고 main도18830c2다. 문서를 게시한 뒤 PR의 이력 보존 merge로 dev에 통합하고 원격을 확인한다. 통합된 작업 브랜치는 AGENTS의 상시 정리 규칙에 따라 로컬/원격 삭제하고 미완료 `feat/activity-selection`은 보존한다. main 갱신·AWS/서버/DB/자료 변경·다른 Issue 종료는 이번 통합에 포함하지 않는다. 실제 병합 SHA/PR·브랜치 정리 결과는 DEV_LOG와 이 문서에 후행 기록한다.
