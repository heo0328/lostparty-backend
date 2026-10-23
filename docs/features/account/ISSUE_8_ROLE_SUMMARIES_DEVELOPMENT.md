# Issue #8 — P1 역할요약 구현·검증·인계

> **현재 서버 반영 완료(2026-10-16):** 사용자 진행 지시로 사용하던 Docker/포트8000/기존DB에 0007~0009와 최신 P2 API를 반영했다. 기존 전 테이블의 원래 컬럼/행 내용 동일·애플리케이션 모델 정합·API/DB healthy·health/P2 OpenAPI 전체일치 및 신규 GET4개 인증차단401을 확인했다. 아래 미적용/별도승인 대기는 각 단계 당시 이력이다. DB내용 초기화·새환경 채택·실provider/소유인수는 수행하지 않았다.

> **2026-10-16 실행 기준 정정:** [최신 지시](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)에 따라 현재 사용하던 환경과 개발자료로 개발을 계속한다. 아래 별도8001 구성·채택/기본 재인수 안내는 작업 이력이며 현재 실행 순서가 아니다. 별도환경 삭제/재설정도 실행하지 않는다. 현재 필요한 기능별 schema/API 작업과 개발자료 초기화를 구분한다. Flutter 별도DB/키 연결은 원래 연결로 복구됐고 최종1524PASS다.

2026-10-15. [수정 계약 수용/P1 구현 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6193638580), [수용 계약](ISSUE_8_PROFILE_RESTORE_CONTRACT_DRAFT.md) 기준. feat/representative-selection에서 진행하며 P2는 이번 구현에서 제외한다.

P1 게시 이후 P2 구현 상태·preferences 실제 복원/호환 경계는 [P2 실행 안내](ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md)를 따른다. 아래 P2 미구현 설명은 P1 불변 SHA 당시 범위다.

## 제공 범위

- GET `/v2/me/characters/{character_id}/personal-profile`
- PUT `/v2/me/characters/{character_id}/role-summaries/{role}` (`dealer|support`)

모두 앱 Bearer/no-store, 외부 provider/키 조회0. canonical UUID만 사용하며 preview/이름/legacy ID를 연결하지 않는다. GET은 반복가능읽기 snapshot의 현재 회원/활성등록/소유/NameClaim·현재 수명과 자료를 반환하고 행을 만들지 않는다. suspect 기존자료는 읽되 신규쓰기는보류, retired조회/쓰기는409다.

personal-profile은 character_id/game_account_id/ownership_revision/lifecycle_revision/lifecycle_state/dealer/support/preferences 8필드다. 역할객체는 version/summary/saved_at이며 미저장 version1/summarynull/saved_atnull. 같은 UUID의 lifecycle_revision 변화는 과거 역할요약을 삭제하지 않고 observed_lifecycle_revision으로 오래된 관찰을 구분한다. 새 UUID/회원/소유수명은 자동승계없다.

**P2 미구현:** preferences는 `{version:1,preferred_role:null,visible:true,display_order:null,saved_at:null}` 고정 가상기본값이다. 이 단계의 읽기결과를 개인설정의 서버저장 ACK/복원완료로 사용하지 않는다. preferences PUT·presentation GET/PUT·관련테이블/정리후처리는없다. P2실구현시nullable 선호역할/rank등을 위한 스키마 확장을 별도게시한다. 현재의 Literal기본값을 미래P2 wire라고 가정하지 않는다.

## 역할 PUT/DTO·검증

body4필드필수: expected_version/expected_ownership_revision/expected_lifecycle_revision(엄격양의정수), summary(nonnull). UUIDv4 Idempotency-Key필수. summary는 source/analysis_rules_version/analyzed_at/combat_power/item_level/combat_power_observed_at/item_level_observed_at/integrity_status/catalog_version/issues/observed_lifecycle_revision 11필드필수. 원본OpenAPI가정확한필수/nullable계약이다.

source는flutter_analysis고정. nullable수치문자열은최대32자·비음수plain decimal(공백/쉼표/지수/NaN금지), 값없으면관찰시각도null/값있으면UTC필수. 입력시각은UTC RFC3339 `Z` 또는 `+00:00`, 출처시각은클라이언트주장이고saved_at은서버저장시각이다. catalog_version은필수nullable/analysis_rules_version은nonnull, ASCII식별자1~64자. observed_lifecycle_revision은expected_lifecycle_revision과같아야한다(불일치400).

issues는최대20개/code대문자ASCII1~64자/severity warning|error·중복(code,severity)금지/추가raw필드금지. clean=빈issues, review=warning1개이상/error없음, error=error1개이상, unavailable=빈배열또는warning/error없음. null카탈로그나빈issues로clean을추론하지않는다. unknown code는형식상수용하고서버가그코드의게임판정을인증하지않는다. source/수치/무결성은provider캐시/Character.summary/퇴역이력·소유/활동/대표권한에영향없다.

PUT전체body는JSON파싱전에32768bytes로제한하며chunked도누적검사한다. 초과413 REQUEST_TOO_LARGE, unknownquery/GETbody·잘못된UUID/role/key·strict/추가속성/조합오류400 INVALID_REQUEST. 응답오류에입력원문/SQL/토큰없다.

PUT200은version/summary/saved_at/character_id/role/ownership_revision/lifecycle_revision 7필드(모두필수/nonnull). 저장은회원/캐릭터/소유revision/role PK·독립version이다. 첫저장2, 실제요약변경만+1, no-op도expectedversion먼저 검사/동일payload는saved_at유지. 반대역할은변경하지않는다. 나이스단회원bool OFF나활동미선택이저장/유효pending복구를막지않는다.

## 권한·멱등·오류

새명령:기존game쓰기lock→현재회원/세션→캐릭터/본인활성등록→현재소유→상태/NameClaim→소유/lifecycle→역할version→저장/ACK. 네트워크작업없음. 본인등록이없거나없는/타인ID404 CHARACTER_NOT_FOUND, 본인등록소유상실403 OWNERSHIP_REQUIRED, suspect/retired신규쓰기409 CHARACTER_UNUSABLE, claim불일치409 IDENTITY_CONFLICT, 소유/수명/역할version409 REVISION_CONFLICT.

operation role-summary·회원/UUIDv4key scope·digest에는canonicaltarget/role/정규화body. 30초lease/generation fencing, 진행중409 REQUEST_IN_PROGRESS/Retry-After2, 다른body/role/target409 IDEMPOTENCY_CONFLICT, 성공24시간/추가24시간tombstone409 IDEMPOTENCY_EXPIRED. 업무쓰기와ACK한transaction/실패rollback·retryable로같은key/body복구. 이전generation은commit불가.

replay는현재회원/세션·본인활성등록/소유/NameClaim 및원래요청과같은소유/lifecyclerevision을검사한다. 자료삭제/소유상실/퇴역/수명변경은거절한다. 통과한응답은과거ACK이며현재역할version은재검사하거나재적용하지않는다. GET이현재원본이며다른기기의새값을옛대기로덮어쓰지않는다. 기존401/정지403·분류가능DB장애503 SERVICE_UNAVAILABLE 유지.

## Migration·실환경 경계

`0008_role_summaries`는0007위에character_role_summaries한테이블만추가한다. 회원/캐릭터FK·회원/character/ownership_revision/role복합PK·role및양의수명/version제약·JSONB요약/서버시각. 기존행backfill/캐시복사/UUID/FK변경없음. downgrade는요약파괴삭제를하지않고RuntimeError로중단한다. P2정리경계는후속이며live퇴역/claim해제는여전히호출하지않는다.

**실제개발/운영DB에0007/0008미적용·API미재시작/미전환.** 현재실행API는대표구간이다. API/test이미지빌드는실행컨테이너를교체하지않는다. 별도전환승인전현재서버에서P1/V2호출가능하다고안내하지않는다. 운영배포·기기설치/인수·자료삭제·실provider시험·Issue종료없음.

## 검증·게시

1차최신이미지격리PostgreSQL P1/기존V2읽기/회원설정/metadata **108PASS, 61.72초, 기존경고1**. 추가 세션/같은이름새UUID/lease takeover/DB장애/실제기존행migration 경계 및 생명주기·대표·전투력/metadata 회귀 최종 **171PASS, 79.99초, 기존경고1**. 두실행을합산한단일suite로표현하지않는다. 실제provider/기기인수가아니다.

network-none이미지OpenAPI와원본대조, 기존모든paths/components/policy불변·새GET/PUT와새 schema/policy만추가확인. 구현/원본 OpenAPI `6e4f625c3b62c92ec412373b33ed8a3441af8149`를 작업브랜치 commit/일반push·원격동일SHA로 확인하고 [P1 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6194881739)를 게시했다. dev/main 미통합, 실제DB/API미전환이다. P1 인계 당시 다음 Flutter adapter는 아래 A1 회신으로 완료 보고됐다. P2도 별도 구현/게시됐으며 현재 상태는 P2 실행안내/아래 회신을 따른다. 기존 별도미커밋 lifecycle 전환준비문서는 보존했으며 구현/계약 게시와 구분한다.


## Flutter 소비 결과 — 2026-10-16 확인

[A1 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196135272)에서 P1 `6e4f625` strict GET/역할PUT·scoped 역할기록/불변명령·응답유실/재실행/충돌/24시간 경계 연결과 최종전체1432PASS/lib-test분석0을 보고했다. [A2](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196639685)는 P2 `7027f0b` 실제 preferences로 parser를 전환했다. P1 가상기본값을 개인설정 ACK로 적용하지 않는 경계를 수신 확인했다.

이후 [B](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197379381) 실행기와 [C](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197881822) 앱 수명/회원 주목록·진행 UI까지 코드 연결/모의검증 완료 보고다. Flutter feature/scoped-account-cache/기준cc6a0b0에서 미커밋·미push·dev미반영이며 새 인계SHA없음, 기본flagOFF·실서버/provider/기기 인수미확인이다. 현재 추가Backend수정/반복mock시험요청없음. 실제 서버 전환 준비·별도승인/적용과 사용자 인수는 [NEXT_WORK](../../project/NEXT_WORK.md)를 따른다.


## 최신 실행 상태 — 새 환경 준비

위의 DB/API 미적용 표기는 각 구현 인계 당시 기록이다. 2026-10-16 사용자 진행 지시 후 별도 `lostparty-fresh-dev`에 새 빈 DB0009/P2 API8001을 구성했고 health/원본 계약 일치·사용자자료0건을 확인했다. 원본8000/0006은 유지했다. [새 환경](../ownership/ISSUE_8_LOCAL_TRANSITION_READINESS.md)·[관찰 도구](../ownership/ISSUE_8_OWNERSHIP_READINESS.md)가 현재 기준이다. 실제 게임 검증은 사용자 결정으로 나중에 진행하며 소유/canonical·퇴역/전체 인수는 보류다. Flutter D는 [1528PASS/미게시 완료 보고](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207225790)이며 실기기 인수와 구분한다.
