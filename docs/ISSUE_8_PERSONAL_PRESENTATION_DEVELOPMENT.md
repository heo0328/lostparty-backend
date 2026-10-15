# Issue #8 — P2 개인설정·원정대 표시 구현/검증

2026-10-16. [P2 별도 구현 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6195124835)과 [수용 계약](ISSUE_8_PROFILE_RESTORE_CONTRACT_DRAFT.md)이 기준이다. feat/representative-selection에서 P1 6e4f625 이후 이어간다. 실제 DB/API 전환과 live 퇴역은 포함하지 않는다.

## 제공 경로와 P1 호환 경계

- 기존 GET `/v2/me/characters/{character_id}/personal-profile`의 preferences가 실제 개인설정을 읽는다.
- 새 PUT `/v2/me/characters/{character_id}/personal-preferences`.
- 새 GET/PUT `/v2/me/game-accounts/{registration_id}/presentation-settings`.

기존 모든 paths operation과 P1 RoleSummary/RoleSummaryIn/RoleSummaryOut/AnalysisIssue/StoredRoleSummary 스키마는 유지한다. PersonalProfileOut의 preferences 참조를 PendingPersonalPreferences에서 **PersonalPreferences**로 바꾸고 더 이상 쓰지 않는 PendingPersonalPreferences를 제거한다. PersonalPreferences·PersonalPreferencesIn·PersonalPreferencesOut·PresentationIn·PresentationOut 5개 스키마를 추가한다.

이는 P1의 const 가상기본값 소비자에게 호환 변경이다. P2 원본을 소비한 adapter만 실제 선호역할/표시값/version을 복원하며 P1 고정값 parser로 P2 personal-profile을 읽지 않는다. 실제 전환은 별도 승인·원본 버전 확인 후다. P1 역할요약 PUT/summary wire·독립version/오류·출처·멱등 의미는 유지한다.

## 개인설정

PersonalPreferences 5필드 전부 필수: version(엄격양의정수), preferred_role(dealer/support/null), visible(strict bool), display_order(null 또는 엄격정수0~2147483647), saved_at(UTC|null).

미저장은 version1/null/true/null/null이며 GET은 행을 생성하지 않는다. PUT6필드 전부 필수: expected_version, expected_ownership_revision, expected_lifecycle_revision, preferred_role, visible, display_order. 앞3필드는 엄격양의정수/null불가다. PUT200은 개인설정5필드+character_id/ownership_revision/lifecycle_revision의8필드다. saved_at만 실제 변경 시 서버시각으로 기록하고, 기본값 그대로 첫 no-op이면 row 생성 없이 version1/saved_atnull로 성공 ACK를 남긴다. 실제 변경만+1, 같은값이라도 stale expected version은409다. 기본값으로 되돌려도 행/version을 삭제하지 않아 오래된 요청이 version1로 통과하지 않는다.

회원+canonical character UUID+ownership_revision PK로 격리한다. 현재 회원/세션→활성 본인등록/소유→캐릭터 상태/NameClaim→수명/개인version을 검사하고 기존 game 쓰기 lock 안에서 업무/ACK를 같이 commit한다. suspect는 기존 설정 GET 가능·새 PUT409 CHARACTER_UNUSABLE, retired GET/쓰기409. claim불일치409 IDENTITY_CONFLICT, 수명/version409 REVISION_CONFLICT. 같은 UUID 수명 변화에서 설정을 임의 삭제하지 않는다. 이름 재사용 새 UUID/새 회원/소유수명에는 승계하지 않는다.

source/provider 수치·양역할 summary·활동·대표·회원 나이스단bool을 바꾸지 않는다. hidden 대표를 강제 표시하거나 rank 하나 저장으로 다른 캐릭터를 재번호화하지 않는다. rank의 의미는 동일 원정대/소유수명 안의 개인 순서이며 최종 표시 정렬은 Flutter가 계약대로 계산한다. 부분 저장/중복 rank는 허용하고 전체 정렬 ACK로 과장하지 않는다.

## 원정대 표시 개수

GET/PUT200 7필드 전부 필수: registration_id, game_account_id, registration_version, ownership_revision, version, visible_count, saved_at. saved_at만 nullable, UUID2개/양의revision·version/visible_count strict1~200이다. 미저장 version1/visible_count6/saved_atnull. 현재 캐릭터 수가 저장count보다 작아도 저장값은 줄이지 않는다.

PUT4필드 필수: expected_version, expected_registration_version, expected_ownership_revision, visible_count. 회원+canonical game_account_id+ownership_revision PK이며 registration_id는 접근/변경 fence다. 비메인도 허용하고 일부 suspect가 있어도 표시count 저장을 막지 않는다. 캐릭터를 선택하는 명령이 아니므로 전체 roster의 NameClaim/활동완료·나이스단ON을 요구하지 않는다.

본인 활성등록→canonical 소유를 검사한다. 미인증 preview·소유상실403 OWNERSHIP_REQUIRED, 없음/삭제/타인등록404 REGISTRATION_NOT_FOUND, 새 PUT의 등록/소유/표시version차이409 REVISION_CONFLICT. 기본6 첫 no-op은 row 생성 없이 version1/saved_atnull, 실제변경만+1이다. settings_version·대표·활동·캐릭터 개인version과 독립이다.

등록해제는 옛경로 GET/PUT/replay 접근을 막고 저장자료를 즉시 지우지 않는다. 신뢰된 연결로 동일 회원/account/ownership_revision의 새 활성등록을 얻으면 새 경로에서 이전 값을 읽을 수 있다. 옛 key/명령을 새 경로로 이식하면 digest충돌이며 새 명령은 현재등록version을 사용한다. 새 account/소유수명에는 기본6이고 소유가 돌아와도 이전 소유수명값을 자동승계하지 않는다. 이름만으로 소유 연결을 생성하지 않는다.

Flutter 정렬은 원정대별 visible 제외→현재대표→rank(nonnull오름차순/null후순위)→아이템레벨 수치 내림차순/null후순위→이름→UUID다. 대표가hidden이면 숨김을 유지하고 suspect 대표는 경고와 저장상태를 구분한다. 서버가 권한이나 선택을 변경하거나 목록을 정렬해서 반환하는 새 API는 없다.

## 전송·멱등·오류

모두 Bearer/no-store, 외부 provider/키조회0·GET무쓰기. PUT은 UUIDv4 Idempotency-Key 필수, unknown query/GET body/추가필드·strict오류400 INVALID_REQUEST. P2 body는 JSON파싱 전 **4096 bytes**로 제한하고 chunked도 누적 검사하며 초과413 REQUEST_TOO_LARGE다. P1 역할요약의32768 bytes는 유지한다.

operation은 character-preferences/account-presentation으로 분리한다. digest에 canonical character 또는 registration target와 전체 body 포함, 회원/operation/key·30초lease/generation fencing·업무/ACK 원자성·24시간성공+추가24시간tombstone을 재사용한다. 같은key/body 복구·다른입력409 IDEMPOTENCY_CONFLICT·진행중409 REQUEST_IN_PROGRESS/Retry-After2·만료409 IDEMPOTENCY_EXPIRED. 오래된 대기의 expectedversion만 바꿔 자동 덮어쓰지 않는다.

preferences replay도 현재 회원/등록/소유/NameClaim 및 원래 소유/lifecycle 수명을 확인한다. presentation replay는 같은 활성 registration/현재소유수명을 확인하고 label변경 등 현재등록version차이만으로 과거 ACK를 재실행하지 않는다. 현재값은 GET이 원본이다. 양쪽 모두 삭제/소유상실은 거절하고 당시 version을 재적용하지 않는다. 기존 앱401/정지403·분류 가능한 DB장애503 SERVICE_UNAVAILABLE과 입력원문/SQL 없는 오류를 유지한다.

## Migration·내부 퇴역 정리

`0009_personal_presentation`은0008위에 character_personal_preferences/account_character_presentation 두 테이블만 추가한다. 회원/character 또는 account FK·소유수명 복합PK·role/rank/count/version 제약, 기존행 backfill/UUID/FK변경/캐시복사/자료삭제 없다. downgrade는 설정 파괴삭제 대신 RuntimeError로 중단한다.

내부 lifecycle.retire의 기존 검증된 complete evidence transaction에서 **퇴역 대상 canonical UUID의 모든 소유수명 역할요약·개인설정**을 정리한다. claim해제·간략 provider 이력·활동/대표 재구성·수명/roster 변경과 같은 transaction이며 중간실패는 전부 rollback한다. 다른 UUID/원정대 표시count·간략이력/FK는 유지한다. client 분석값으로 기존 provider 기반 퇴역이력을 덮지 않는다. 공개/API/live caller를 새로 추가하지 않으며 실제 누락관찰이 이 정리를 호출하지 않는다. 등록해제/일시suspect를 퇴역 정리로 취급하지 않는다.

## 실제 환경과 검증/인계

실제개발/운영DB0007/0008/0009 적용·API재시작/전환·배포/기기조작·실자료이관/삭제·live proof/퇴역/claim해제 보류 해제는 없다. 현재실행API는 대표구간이며 P1/P2/V2 즉시호출 가능 상태가 아니다. 이미지 빌드는 실행컨테이너를 교체하지 않는다. 원본OpenAPI 비교는 network-none 최신이미지로 수행한다.

검증/불변SHA/push/Issue 인계 결과는 아래 후속 기록을 따른다. Flutter는 게시 P2 원본을 소비해 P1 가상preferences와 실제복원을 구분하고 strict adapter/개인설정·표시 저장/대기·모의검증을 진행한다. 실제서버/기기 인수는 별도 전환 준비·승인 후다.

### 초기 검증 기록

첫 실행은127개 중109PASS/18FAIL(82.05초·기존경고1)이었다. 등록 인증 후 증가한 registration.version을 반영하지 않은 P2 fixture와 신규 설정행 saved_at 할당 전 DBclock 조회가 일으킨 autoflush/NOT NULL 오류가 원인이었다. fixture는 현재 등록 GET으로 보완하고 저장시각은 신규행 add 전에 확보하도록 수정했다. 이를 통과 결과로 표시하지 않으며 수정 후 최종 실행을 아래에 별도로 기록한다.

### 수정 후 P1/P2 검증

최신이미지·격리PostgreSQL17에서 P2/기존P1/metadata **128PASS, 96.19초, 기존경고1**. 실제 설정복원/default no-op·독립version·strict/4KiB·등록version/replay·등록해제/동일수명재등록·소유수명격리·suspect/claim·동시기기/rollback·이력/다른ID/account표시 보존·기존자료0009이관/제약을 확인했다. 초기18FAIL과구분하며 실제provider/기기시험이아니다. 추가같은key복구/표시replay소유수명과직접영향회귀는별도최종기록을따른다.

최신 network-none API이미지의app.openapi()와원본전체일치확인. 이전paths의operation전체불변·RoleSummary등P1역할스키마불변을대조했고, PersonalProfileOut의preferences참조교체/PendingPersonalPreferences제거 및 새5스키마·새2paths/3operations와profile policy변경만반영했다.

### 최종 직접 영향 검증

추가 같은key 복구/원정대replay 소유수명과 P2·생명주기·V2조회·대표·회원설정/metadata **143PASS, 75.80초, 기존경고1**. 앞선128개와 별도 실행이며 합산 단일suite로 표현하지 않는다. 초기 오류는 보완 후 최종 실행에서 모두 통과했다. test-db만 중지하고 실제DB/API를 변경하지 않는다. 다음은 이 구현·정확한원본OpenAPI를 작업브랜치에 commit/push·원격일치확인 후 같은Issue 인계다.
