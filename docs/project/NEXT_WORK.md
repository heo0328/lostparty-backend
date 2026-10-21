# 다음 실행

2026-10-21 / **feat/raid-recruitment**, W1/W2 완료 구간 로컬 커밋 기준(직전 HEAD6490f69)·기존 실행 구현 cc003e9 계열.

[전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083) 기준 **계약0.4.1 / policy two-cycle-contract-4** 유지. [W1](../ISSUE_13_W1_CYCLE_FOUNDATION.md)·[W2-A](../ISSUE_13_W2_READ_SLICE.md)·[W2-B 생성/조회/일반 참가](../ISSUE_13_W2_CYCLE_ADMISSION.md)는 로컬 구현·격리 검증 완료·구간 커밋/미push다. 다음은 **W3**다. W2-B 후보는 main에 미등록이며 W3~W5·실제 서버 공개/Flutter 인수는 미완료다. [전체 작업계획](../ISSUE_13_TWO_CYCLE_WORK_PLAN.md) 기준.

작업 구간 종료마다 검증·문서 갱신 후 커밋한다. push/PR/merge·배포는 기존 승인 범위를 따른다.

## 다음 작업 순서

1. **W3 — 다음 주 참가·개방·취소·공대장 위임**: W2-B `cycle_creation/commands/admission/schedule`·0025의 명시 target 저장/일반 참가를 이어 쓴다. 기존 C 참가자 N즉시참가·대체캐릭터·B충돌보존, 명시개방/재개+최초참가·N취소/자동승계·직접위임을 구현한다. 취소 후 같은 세대 재참가는 기존 Assignment를 재활성화하고 새 순번·이벤트로 구간을 남긴다. 완료 Assignment 부활/타 주차 lease 해제는 금지한다. 생성에서 대체 N 캐릭터가 되는 것만으로 기존 C 회원 특례 구현 완료라 하지 않는다.
2. **W4 — 주차별 일정·완료·공통 관리·전환**: 조율/제출표·확인예약/완료·정정, G1 공통설정·전역leave/end, 06시worker/v1호환. 0024/0025에서 구 API 활성화/worker는 거절하므로 새 worker·v1 adapter·legacy review·닫힘 세대 조회/실행 fixture를 함께 전환한다. 현재 후보 plan의 후속 명령 권한은 아직 준비되지 않았다.
3. **W5 — 통합 검증·성능·실행 계약·네이티브 인계**: 보존/경합·성능/전체56동작 원본OpenAPI 대조, 소비가능구간 묶음 commit/push·원격확인·인계. 중간 인계도 같은 기준을 충족하면 진행하며 W5까지 일괄 대기하지 않는다. 실제 DB 이행/이미지전환의 대상·영향·승인 범위는 별도다.

## 담당·완료 조건

- 다음 Backend: W3. 관련 Issue 본문/최신 회신·Git 상태를 먼저 확인한다. 사용자 추가 제품결정·동일 계약 재검토는 선행 조건이 아니다.
- 다음 Flutter: 주차메타/actualcycle·계정summary/선택기. 착수 시 실제 준비 경로/실행SHA와 계정·캐시·회원격리 회귀 범위를 확인한다. Backend W1 기반만으로 실제 API 준비 완료를 안내하지 않는다.
- 최초 생성만 C/N 함께, 이후 참가·탈퇴·위임·완료는 T별 독립이다. L1/G1/A1·기존자료/원ACK 보존 유지. #19 통계 미확정은 별도 후속이다.

## 기준과 실제 상태

- [계약4판](../ISSUE_13_TWO_CYCLE_CONTRACT_R4.md) + [ACK 보완](../ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), [전체83번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310051618). docs/design/issue13-two-cycle.full.openapi.json이 구현 명세이며 core issue13-two-cycle.openapi.json은 재현 입력용이다.
- 53경로/56동작/204schema, canonical SHA256 fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1. Backend/Flutter 합성84사례·CAS6쌍·endpoint흐름2개와 W1 실행 검증을 구별한다.
- W1: 신규 0024/10표·주차/세대/실참가·복합 FK/원천 보존·target/06·10시/순번·원 ACK/worker 차단. 관련 고유63사례 확인: 1차56PASS/계약파일1FAIL 후 컨테이너 파일 동기화·보완 재검증17PASS(중복10)로 모두 통과. 제한 LOGIN/합성자료·기존 표 모든 열 지문 보존. 초기21PASS는 중복이다.
- W2-A: GET /v2/raid-cycles·POST /v2/me/raid-weekly-summary를 main에 연결하고 원본에2경로/10schema 추가. 기존114경로/schema 변경0·현재116경로. 합의 명세의 실제 입력/응답 제약 대조/107고유사례 확인(103+추가3 후 종료이력 제한 보완/신규조회33재검증·추가1), 신규 두 경로·기존 계정/캐시/회원격리·RR/원장·기존 표 보존 확인은 격리 합성자료 기준이다.
- 별도 검증 이미지에서 FastAPI/원본 전체 일치와 DB0023 readiness 통과. 개발 서버/API 이미지·DB는 전환하지 않았다. 신규 v2 쓰기/target 목록·selector 의존·운영 성능·실회원·기기는 미검증이다. Flutter 인계 전 실제 준비 경로/실행 SHA·게시 상태를 확인한다.
- W2-B: 후보17경로/19동작·0025 추가3표, C/N 단일 생성·초기순번/리더·원 ACK/롤백, target 검색·상세/개인계획·그룹 projection·본인/신청목록·일반 참가/승인·거절·철회. 신규35PASS 후 최종 조회 보완6PASS 재검증(중복), W1/W2-A·기존 생성/일정/계정·시각 회귀121PASS. 실제 lease 인원/정원·SQL 필터/정렬·T cursor/리더·private plan 권한 격리, N 복사일정 예약0 확인. 상세 증거/후속은 W2-B 문서 참조.
- W1/W2 코드·문서/기존 설계 도구를 완료 구간 커밋에 포함·미push. 0025까지 shadow head이며 현재 API/worker와 혼용 금지. W2-A 조회만으로 0024/25 이행은 필요 없다. main/OpenAPI116경로는 유지하고 신규 후보는 미등록했다. 설계 builder는 immutable cc003e9 baseline fallback/--base-openapi로 기존 hash를 재현한다. 완료 구간 커밋은 사용자 상시 지시로 수행한다. 새 Flutter 시험 요청/Issue 댓글·push·merge·배포는 없다.
