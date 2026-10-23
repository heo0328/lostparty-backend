> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [activity-and-presentation](../../../../features/rosters/activity-and-presentation/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 수동 활동·대표 선택 정책 정정 작업 구간

2026-10-17. 상태: **구현·자동 검증·push·로컬 API 반영 완료, Flutter 실제 저장 확인 대기**. [119번째 Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230483893). [118번째 Backend 설계 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230431817)에 공유했다. 현재 브랜치 `feat/raid-services`, 기준 코드 `ac79ce4`(주간 구현 `bce6133` 포함). 기존 로컬 문서 변경은 보존한다.

기준은 [115번째 Flutter 사용자 정책 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230281148), [116번째 Flutter 구현 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230345749), [117번째 Backend 코드 대조](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230374459)다. 조회 시 #8 댓글117개, #11 댓글2개, #12/#13 댓글0개였고 #13 본문의 수동 활동 정책도 정정된 것을 확인했다. 댓글 순번과 아래 작업 순서는 다른 의미다.

## 확정 정책과 적용 범위

- 1700은 Flutter의 최초 unconfigured 기본 선택 기준으로만 사용한다. 사용자가 직접 선택한 현재 유효한 본인 캐릭터와 그 안의 대표는 1700 미만이라는 이유로 거절하지 않는다.
- 현재 소유·등록 범위·canonical UUID·active/confirmed·정상 NameClaim, 대표의 활동 선택집합 포함, 대표 전용 명령의 main 조건을 유지한다. 타회원·소유상실·suspect/retired·이름 충돌·오래된 revision은 계속 차단한다.
- 레벨은 수동 활동 권한과 분리한다. 레벨 누락/파싱 실패만으로 정상 UUID의 소유/생명주기를 무효화하지 않는다. provider 자료 파싱 규칙이나 원본 수치·정밀도를 이번에 느슨하게 바꾸지 않는다.
- 최초 기본 선택은 Flutter가 현재 전체 목록에서1700 이상 유효 후보를 고르는 기존 동작이다. 서버에 자동 초기 선택/대표 교체 API를 추가하지 않고, 기존 CAS 저장으로 확정한다. configured/needs_reconfiguration의 사용자 선택을 자동 초기화하지 않는다.
- #13의 실제 raid/difficulty 입장레벨은 별도다. combat_power의 상세 갱신 기준 등 무관한1700 사용처를 일괄 수정하지 않는다. #10 카탈로그/주차와 #11 주간 원장 정책은 유지한다.

## 구현할 한 구간

서버 정책·조회/갱신 판정·계약 설명·관련 검증을 **하나의 작업 구간**으로 묶어 게시한다. 작은 변경마다 분리해 인계하지 않는다.

| 대상 | 현재 동작 | 변경 결과 |
|---|---|---|
| `app/game_accounts/activity_policy.py` | usable과레벨>=1700을함께검사 | 수동 eligible/require_eligible는 lifecycle/claim 사용 가능 조건만 검사. 사용하지 않게 된 레벨 전용 코드는 제거하되 공통 상수는 보존 |
| `service.py` 전체 character-settings PUT | 선택집합/대표의레벨추가검사 | 기존 원자 저장·CAS·대표 포함·권한 검사를 유지하면서 저레벨 수동 저장 허용 |
| `representative.py` 전용 PUT | 선택된캐릭터의레벨검사, no-op도거절 | 선택된 저레벨 대상의 변경/no-op 허용, main/소유/UUID/선택집합/버전 경계 유지 |
| `service.settings_out` | 저레벨/레벨미상 선택을 ineligible로 보고 | 현재 소유·생명주기/claim이 유효하면 레벨만으로 부적격 목록에 넣지 않음 |
| `service.reconcile` | 레벨 하락만으로 needs_reconfiguration | 레벨 하락만으로 설정 상태/버전을 바꾸지 않음. 실제 누락/suspect/claim 이상은 기존 차단 유지 |
| V1 캐릭터 eligible / V2 usable | 이미 lifecycle/claim 의미 | 의미/필드 유지. 전수 호출부 대조·회귀로 확인하고 필요 없는 응답 변경은 하지 않음 |
| `app/main.py` / `openapi/openapi.yaml` | activity_selection에 수동1700 하한 설명 | 초기 기본 선택과 수동 자격을 명시적으로 분리. 예: `initial_selection_minimum_item_level`로 초기1700을 설명하고 validation/stored 설명 정정. HTTP 경로/DTO 필드/오류 envelope는 그대로 |

기존 저레벨 선택 때문에 needs_reconfiguration으로 남은 설정은 GET/refresh로 임의 configured로 복구하지 않는다. 선택·대표·revision을 그대로 읽고, 유효한 현재 목록/예상 버전을 확인한 기존 명시 저장 성공으로 configured가 되도록 한다. DB 일괄 보정·자료 초기화·migration은 필요 없다.

## 검증과 완료 조건

격리 PostgreSQL에서 아래 의미 있는 경계를 확인한다. 과거 레벨 제한을 고정한 기존 테스트의 기대값은 최신 계약으로 바꾸되, 권한·rollback 검증은 삭제하지 않는다.

1. 1700 미만 수동 활동 집합/대표 저장·재조회 복원, 메인과 부원정대 전체 설정, 대표 전용 변경/no-op, 동일 원명령 재전송을 확인한다. 레벨 미상은 수동 권한과 독립하되, 잘못된 provider 원본을 정상으로 바꾸지는 않는다.
2. 정상 roster 갱신에서 레벨만 하락해도 선택/대표·configured가 유지되고 ineligible에 들어가지 않는지 확인한다. 기존 needs_reconfiguration은 읽기로 변경하지 않고 다음 명시 저장으로 정상화되는지 확인한다.
3. 타회원/타원정대·소유상실·suspect/retired·claim 충돌·대표 미선택·비main 전용명령·stale revision과 응답 유실/멱등 충돌의 거절·원자성을 확인한다.
4. 최초1700 기준의 명시 초기 draft 저장·기존 대표 유지/무자동 재선정, 레이드 정밀 입장레벨과 combat_power 기준이 이번 수정으로 바뀌지 않는지 확인한다. Flutter 자동 초기선택 자체는 원격 보고/별도 연동 근거이며 Backend 테스트로 실기기 완료를 주장하지 않는다.
5. 활동/대표·기본 설정/조회·생명주기/갱신·전투력 및 카탈로그/주간의 직접 영향 범위로 검증한다. 실행 이미지와 전체 OpenAPI 일치를 확인한다. 관련 검사 통과 후 이유 없이 전체483개를 반복하지 않는다.

인계 순서는 **구현/자동 검증 → 같은 작업 브랜치 commit/push → 원격 SHA 확인 → 기존 로컬8000 API 반영/health·실행 계약 확인 → #8 결과 회신**이다. 코드·문서·API 반영 SHA와 자동 검증/실제 서버/Flutter 적용·실기기를 구분한다. 개발DB0011·기존 자료/키를 유지하며 merge/운영 배포는 하지 않는다. 낮은 레벨 실제 사용 저장은 서버 반영 뒤 Flutter/사용자 결과로 확인하고 기초 로그인/소유 인증을 다시 요구하지 않는다.

## 다음 구간

이번 정책 보완 인계 후 #12 그룹 G1 생성/검색/내 그룹·상세/멤버 명세로 복귀한다. #11 실제 점유 중 완료·영향 확인과 #13 파티 연결은 별도다. 현재 설계에 추가 사용자 결정 입력은 없다. 최종 검증·구현 SHA/원격 게시·서버 정책 반영 결과를 완료 후 기록한다.


## 구현·검증 결과

- 활동 정책 모듈의 eligible/require_eligible를 lifecycle.usable/require_usable로 한정했다. 공통 호출부인 전체설정·대표저장·settings_out·reconcile에 동일하게 적용한다. server GET의 자동복구/선택이나 새API·DTO·DB변경은 추가하지 않았다.
- OpenAPI는 x-game-account-policy.activity_selection의 초기기준키/validation/stored/identity 설명만 변경했다. HTTP paths/DTO 및 나머지 모든 정책값 보존을 값 단위로 대조했다.
- 최초 관련9파일 실행은260PASS/5FAIL/114.83초였다. 실패는신규활동테스트의잘못된자료형1개·NameClaim제약과충돌한fixture1개·명시선택집합과다른helper요청3개였다. 기능의권한차단을완화하지않고테스트자료/요청만수정했다.
- 보완한 활동파일 **20PASS/12.26초**. 최초실행의다른8파일244PASS와합쳐현재유효한검증범위는총264개이며 단일실행264PASS라고보고하지않는다. 기존Starlette/AnyIO경고1개가있다. 개발DB와분리된PostgreSQL에서실행했고실제사용자저레벨저장시험과구분한다.
- 최종대상: test_activity_policy / test_representative / test_game_accounts / test_lifecycle_reads / test_owned_roster_refresh / test_power_ownership / test_combat_power / test_raid_catalog / test_raid_weekly. 같은코드의전체483개는반복하지않았다.
- 구현/계약 `d33f87350f7ef93a19ca800120107194a7a5ee21`을push·원격확인 후 기존8000 API반영·실행OpenAPI전체일치/health/DB0011유지를확인하고 [119번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230483893)로회신했다. 실행이미지의내부helper확인과실제회원HTTP저장은구분하며사용자실기기성공보고는아직없다.
