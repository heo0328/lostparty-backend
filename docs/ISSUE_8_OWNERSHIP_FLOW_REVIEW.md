# Issue #8 — 원정대 등록·소유 인증·사용 캐릭터 연결 검토

> 후속: [서버 장비 해제 인증 연결](ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md)로 신규/이름 claim 충돌 없는 원정대의 서버 수집·검증 성공 경로를 구현했다. 아래 live=false 설명은 당시 상태다. 기존 ID 연속성/타소유 이전·퇴역은 계속 별도이며 실제 게임 인수는 나중이다.

2026-10-16 사용자 지시로 현재 코드/계약을 대조했다. [Flutter UI/UX 재검토 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208702210)을 게시했다. 현재 환경/자료를 유지하고, 실제 게임 관찰은 나중에 진행한다. 기존 완료 기능 재개발·기초 인수 요청이 아니다.

## 현재 서버 단계와 경계

| 단계 | 서버 구현 | 남은 확인 |
|---|---|---|
| 원정대 등록 | Registration/preview 저장, 본인 등록 목록·메인/라벨 관리. 소유 미인증과 owned/ownership_lost 구분 | Flutter 목록에서 소유/설정 상태 표시와 인증/사용 캐릭터 설정의 실제 진입 경로 |
| 인증 시작/진행 | registration/direct_input 중 하나로 시작, 지정 장비·10분 기한·조회/취소/confirm·키/회원/등록 snapshot 검사 | 단계/만료/오류/보류 UI, 현재 대상 유지와 다른 회원 late응답 차단 |
| 실제 증거 검증 | 장비 비교는 구현됐으나 live Observation.proof_validated=false, binding=None | 실제 소유 증거를 생성할 검증 규칙·server adapter 연결이 미완료. 실제 관찰은 나중이며 bool만 true로 바꾸지 않음 |
| 원정대 연결 | canonical_candidate는 이름을 충돌로만 취급. 유효 내부증거의 소유귀속/등록연결·감사·canonical reconcile transaction 구현 | 기존원정대 연속성·현재세대/claim충돌·소유변경 근거를 live에서 공급할 경로 미완료. 단순 이름중첩으로 연결/이전 금지 |
| 사용 캐릭터 저장 | character-settings는 활동 UUID 전체집합과 집합 안 대표·settings/ownership/roster 기대version 검증 후 원자 저장. 빈/중복/외부·부적격 대상 거절 | 인증후 canonical 목록 재조회→명시선택→저장/복구의 Flutter E2 연결 검토 |
| 표시/자동 갱신 | 역할·선호/visible/count·활동/대표는 별개. 기존 저장/복원 구현 유지 | UI에서 상태 구분·현재활동 대상과 표시목록 혼동 방지. 실제 소유가 필요한 새 실검증만 조건충족 후 |

근거: `app/game_accounts/service.py`의 create_registration/ownership/start·confirm/apply(settings)/canonical_candidate/reconcile, `observations.py`, `lifecycle.py`, `schemas.py`, 기존 대표 계약/P2 OpenAPI. 이 검토는 코드/계약 읽기이며 새 자동시험/실사용자 결과가 아니다.

인증 성공 경로는 결과 registration_id를 반환하지만 활동/대표를 자동 설정하지 않는다. 설정행이 생겨도 unconfigured이며 유효 활동/대표의 명시 저장이 필요하다. 이를 인증/소유와 별개로 안내해야 한다. 전체설정은 메인에만 제한되지 않으며 해당 본인 소유 등록 원정대별로 저장한다. 대표 전용 왕관 PUT의 현재 메인 한정과 혼동하지 않는다.

## 다음 서버 작업 단위

1. **현재 연결 검토 완료:** 단계·서버입출력·live 미완료 지점을 위와 같이 확정했다. Flutter의 실제 화면/API 연결·보류/오류·E2 누락 회신을 대조한다. 기존 테스트 근거는 재사용하고 반복 전체시험을 요구하지 않는다.
2. **소유 증거 공급 경로:** challenge에 고정한 대상/키/등록 snapshot, 요청 장비 변경·비요청 장비 불변, 제한시간/반영 지연·불명확 응답을 어떻게 검증된 증거로 수용할지 구체화한다. 관찰 CLI는 인증을 발급하지 않으며 실게임 결과·문서화된 한계와 현재 계약을 구분한다. 필요한 의미 변경은 합의 후 구현한다.
3. **기존/신규 연결 경로:** 신규 account 생성과 기존 account 연결/소유변경을 나누고, 이름claim 충돌·suspect 복구·등록 중복·늦은 응답에서 어떤 근거로 허용/보류할지 정한다. 공급자 전체성/동일세대 근거가 없는 퇴역·claim해제까지 이번 소유 증거로 확대하지 않는다.
4. **구현/영향 검증 및 인계:** 확정된 범위만 구현·계약대조·격리검증→작업브랜치 게시→같은Issue 결과회신. 보류 제거를 코드 없이 완료로 보고하지 않는다. 현재 사용하던8000/DB0009와 자료는 유지한다.

## Flutter 회신 대기

현재 등록/인증/사용 캐릭터 선택을 end-to-end 실사용자로 모두 확인했다고 볼 근거는 없다. 일부 선행 UI/모의 검증은 보고됐고 E2는 다음 독립 구간으로 보고됐다. 요청은 화면/액션→API/상태→완료/일부/미연결→기존 검증/실기기 미확인의 대응표다. 미연결을 소유 서버 보류와 섞지 않는다. 추가 사용자 결정이 필요한 실제 계약 공백이 있으면 그 부분만 질문으로 정리한다.

## 회신 수신/사용자 정책 추가

Flutter6208744179는등록사전선택/인증후E2전환·활동전체편집미연결과E1복구보완필요를확인했다. 6208967265의사용자채택정책은미인증기본조회/서버조회용저장유지·전투력/상세는소유인증이후다. [Backend차이검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208988839)에서미인증power갱신/replay·preview/목록cache노출변경필요를확인했다. 현재구현이정책완료상태가아니며다음권한/응답계약보완범위를구체화한다. 실제소유증거미완료와UI미연결을분리한다.

## 기본 조회/전투력 권한 구현 후속

[Backend 정책 구현](ISSUE_8_BASIC_ACCESS_DEVELOPMENT.md)은 미인증/소유상실 power명령·replay403 및 V1/V2/직접preview/등록replay 과거수치비노출을구현했다. 격리256PASS·기존8000에반영하며paths/DTO/enum/DB구조변경없음. 이는소유증거발급·원정대연속성미완료를해소한것이아니다.
