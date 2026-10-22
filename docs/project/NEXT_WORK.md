# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

W4-B 구현 `0d8b581`·게시 기록 `88dcb3b`까지 push/원격 확인 완료. [W4-C 주차별 관리·공통 설정·전역 정리](../ISSUE_13_W4C_CYCLE_MANAGEMENT.md)는 구현·격리 검증 완료(**고유98PASS(25+26+47 분리 실행, 마지막47PASS/374.96초)**, 신규27 포함), 구현 `babb25b8599fb3564fec59bae13a690e2f53d5b6` commit/push·실제 원격 SHA 확인·[전체88번째 Backend · W4-C 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330196057) 게시 완료. 다음은 아래 W4-D다. 예비 실행은 최종 고유 통계와 중복 합산하지 않는다.

착수/인계 시 AGENTS → 협업 규칙 → 이 문서 → AI_CONTEXT → 계약4판/ACK 보완을 읽고 Issue 본문/최신 댓글·Git/코드를 확인한다. 최신 조회는 [전체88번째 Backend · W4-C 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330196057)이며 새 Flutter 요청/계약 변경·추가 제품 입력 대기는 없다. 계약0.4.1/policy two-cycle-contract-4를 유지하고 사용자 상시 지시대로 구간 종료 시 검증·문서·commit/push·GitHub 기록을 한다.

## 다음 W4-D — 주차 전환·v1/legacy 호환·활성화 준비

1. **남은 고정 GET1동작**: `/v2/me/raid-rooms/{room_id}/continuation-choices`를 legacy 보존 projection으로 연결한다. 과거 선택/의사를 새 실제 N 참가나 동의로 해석하지 않고, GET로 없는 회차·제출·예약을 만들지 않는다. 후보50경로/53동작 + main 주차/summary2동작 + 이1동작으로 전체53경로/56동작을 대조한다.
2. **06시 전환**: 주차별 실제 상태·세대·리더·현재 유효 참가순서를 사용하고, 기존 자동 함께하기 행으로 새 N/참가/예약을 만들지 않는다. 중복 worker·주차 경계·원장/이전 세대·완료/중단·source·원 ACK·소유/한도 review 분류를 검증한다. W4-A/B/C의 명시 동의와 새 예약 구간을 보존한다.
3. **v1 adapter/summary**: 옛 전역 RoomSettings/leader/members/plan을 새 T 권한으로 추정하지 않는다. 기존 v1 수동 완료에도 실제 C/수10시와 원 ACK 우선 예외를 연결한다. legacy 불명 자료는 실행 기본값으로 승격하지 않고 review를 유지한다. declared declined와 나중 일반 참가·다른 방 점유의 account weekly summary 우선순위를 연결한다.
4. **활성화 검증**: 현재 v1/worker의0023 guard와 shadow0029를 혼용하지 않는다. main 등록·실행 OpenAPI/준비검사·worker/lifespan·이행 전후 보존·복구 가능한 전환을 격리 환경에서 먼저 검증하고 실제 서버/DB 전환 대상·영향·승인 범위를 확인한다. 합의된 기능 계약만으로 실제 이행/배포를 실행하지 않는다.

첫 대조점은 `worker.py`·`continuation.py`·`resume.py`·`readiness.py`·`app/main.py`, weekly summary/v1 router와 `cycles`·`cycle_opening`·`cycle_outcomes`·`cycle_common`이다. 이전 W4-C의 신규 DDL은 없고 shadow0029를 사용한다. 추가 이행이 필요하면 planning/times/outcomes/readiness 허용 revision을 함께 검토한다.

## 보존·인계 기준

- T 설정·편성·제외는 actual T만 변경한다. 완료 Assignment/원래 자리·다른 T·persistent 관계·기존 예약 시각을 보존한다. target 제외와 전역 탈퇴/종료를 혼동하지 않는다.
- G1은 C 행이 없는 경우만 N 리더다. closed/completed C의 유효 리더 권한을 유지하고 review/권한 없는 C를 N으로 메우지 않는다. 전역 GlobalScope/원 ACK에는 가짜 target가 없고 persistent-only 영향0도 유효하다.
- 공통 title/scope 수정 no-op은 room revision 유지/영향[]이다. 전역 정리는 실제 전체 영향 context와 persistent CAS·120초 만료·최종 주차/시각·원 ACK를 한 transaction으로 검증한다. 완료된 C에 다른 참가자의 탈퇴가 발생해도 유효한 완료 리더 근거를 지우지 않는다.
- 현재 후보50경로/53동작은 main 미등록. main/원본 OpenAPI116경로·실제 개발 DB/API 이미지·서버는 유지한다. 실제 provider/회원/기기·운영 성능·Flutter 적용/인수는 별도다. 후보 소스 게시만으로 새 Flutter 서버 시험을 요청하지 않는다.
- 이후 **W5**: 전체 실행 계약·통합 보존/경합·성능을 확인하고 소비 가능한 구간을 게시·Flutter에 인계한다. W4 전체/서버 공개·Flutter 인수 완료로 확대하지 않는다. #19 통계는 별도 미완료다.
- 고정 명세 canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`, schema53경로/56동작/204schema·84합성 검증과 실제 HTTP/DB 검증은 분리한다. 검증/게시 근거는 [DEV_LOG](DEV_LOG.md)·각 구간 문서를 따른다.
