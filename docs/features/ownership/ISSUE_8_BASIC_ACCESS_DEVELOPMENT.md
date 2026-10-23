# Issue #8 — 기본 조회와 소유 기반 전투력 접근 분리

2026-10-16. [사용자 채택 정책](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208967265), [Flutter 항목 답변](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209178794)과 사용자 진행 지시를 기준으로 구현한다. 현재8000/DB0009/개발자료를 유지한다.

## 변경 범위

- 전투력 refresh는 현재 본인 소유 등록만 허용한다. 미인증/소유상실은 **403 OWNERSHIP_REQUIRED**이며 개인키·전투력 cache·provider보다 먼저 검사한다. 없음/삭제/타인 등록은 기존404, 세션오류는 기존 인증 처리를 유지한다.
- 같은 key의 과거 성공도 현재 소유를 다시 검사한다. dedup 조회 전과 성공 replay 반환 직전에 검사하며 후자는 기존 game write lock으로 현재 쓰기와 직렬화한다. 신규 실행은 기존 lease 획득·각 외부호출 전·최종 결과 저장의 snapshot/권한 재검사를 유지한다. 소유상실 중 도착한 결과를 성공/cache로 반영하지 않는다.
- owned이지만 활동/대표 미선택인 상태의 수동 전투력 조회는 허용한다. canonical 대상·현재 사용 가능성·item level 등 기존 검증은 유지한다. 표시/활동 권한을 이 명령에서 생성하지 않는다.
- V1/V2 미인증/소유상실 목록은 `combat_power`, `power_fetched_at`, `power_checked_at`, `power_reason`을 null, `power_status=unknown`, `power_stale=true`로 반환한다. preview scope는 cache를 읽기 전에 비노출 투영한다. 원본 preview/cache/빌드 자료를 삭제하거나 덮어쓰지 않는다.
- 직접 검색 preview의 combat_power는 항상null이다. 본인 소유로 확인된 canonical 수치/대표 요약은 기존 표시를 유지한다. 소유상실 후 등록 PATCH/refresh 과거 성공 replay의 representative_summary도 null로 투영하며 저장된 멱등 결과는 변경하지 않는다.
- P1/P2 최소 역할/개인설정은 기존 현재소유/등록/canonical/claim 검사를 재사용한다. 실제 소유 증거 발급·원정대 연속성·퇴역 활성화는 이번 변경 범위가 아니다. 인증용 내부 장비 조회는 유지한다.

## 계약 영향

endpoint/DTO 필드/nullable/enum/DB구조 변경은 없다. 기존미인증수동전투력허용에서현재소유필수로변경되는권한정책과기존nullable필드의비노출의미를 `x-game-account-policy.combat_power`에 함께 기록했다. 기존403/OWNERSHIP_REQUIRED를 재사용한다. 기본조회용Registration 저장/복원은 유지한다. Flutter R1의투영값과일치하며UI숨김만으로서버권한을대체하지않는다.

## 검증과 실행 상태

신규 경계는 미인증/소유상실의 credential/provider 접근0·보존된preview/cache비노출/비파괴·성공replay권한재검사·dedup예약후소유변경·진행중결과폐기·등록명령replay투영이다. 기존전투력회귀는모의소유인증된대상에서유지하고과거미인증수치허용기대는새정책에맞췄다. 실제provider가증거를생성하지않는transport시험은권한우회fixture로바꾸지않고직접전송파서와미인증거절을구분했다.

실제 실행 결과/초기 실패/게시·실행 반영 여부는 DEV_LOG와 Issue 결과 회신을 따른다. 구현 준비나 격리검증을 기존8000 실행 반영/실기기·실소유 성공으로 확대하지 않는다.

최종 격리 PostgreSQL 직접영향/회귀 **256PASS, 1 기존경고, 113.56초**. 최초251PASS/5FAIL은 DEV_LOG의 시험 기대/직렬화 보완 후 같은256건으로 재확인했다. 기본 미인증/소유상실 차단·보존cache비노출·성공replay/진행중소유상실·현재owned/활동미선택 허용을 포함한다. 기존8000 API에적용하고실행계약/소스동일/health·DB0009유지를확인한다. 실제사용자기기/실provider/소유인증성공은미확인이다.
