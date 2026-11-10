# Issue17 공개 계약 검토 후보

현재 구현은 [공개 계약 구현 기록](roster-participation-implementation.md)을 따른다. 이 파일과 고정 JSON은 Native가 수용한 **당시 검토 입력**이며 아래 실행 미구현/다음 단계 문장은 당시 상태다. 최신 실행 OpenAPI와 검증 범위를 구분한다.


최신: [Native 전체15번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6720431541)에서 고정 후보의 기존 본문 소비 대조를 수용했다. 상세/preview 잔여2경로 이번2PASS·이전5PASS 재사용이며 추가 후보 수정/정책·UX 협의 요청은 없다. Native 소비 대조 대기를 해소하고 다음 Backend 공개 wire·M/P 공통 해석 구현/검증으로 넘긴다. examples SHA256 `bd1d31bbcd8eb2113c1fc6b2eeb70251a3db923a9e0913dc83db69d6e6fb8955`, OpenAPI 후보 해시는 유지한다. 신규 DTO/실HTTP·서명/CAS·동시성·기기는 미검증이다.


Native [전체9번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6720005902)의 마지막 소비 경계3항목에 대한 Backend 후보다. **고정 후보의 기존 본문 소비 대조 수용·공개 wire 실행 미구현**이며 실행 계약 `openapi/*.yaml`을 대체하지 않는다. 고정 구현 커밋은 없고 아래 산출물은 로컬 미커밋·미push다.

- [전체 후보 OpenAPI](examples/roster-participation-candidate.openapi.json): 기존 two-cycle 계약을 복사한 독립 검토 파일. `x-baseline-sha256`은 입력 계약, `x-opt-in-response-map`은 실제 경로별 기존/단독/동시 opt-in 응답 component 대응표다.
- [합성 JSON 예시](examples/roster-participation-candidate.examples.json): 각 예시의 경로·query·HTTP·component와 완전 응답 또는 이름에 명시한 metadata 범위를 구분한다. 토큰은 합성 자료로 실행할 수 없다.
- [생성기](tools/build-contract-candidate.py)·[검증기](tools/validate-contract-candidate.py): 현재 실행 계약을 읽어 재생성한다. 산출물 변경 시 해시와 검증 결과를 다시 남긴다.

## 위치·조합·구버전

모든 새 선택은 query다. `include_character_issues=true`는 본인 memberships의 최상위 `character_issues`, detail/plan의 최상위 `character_issue_context`를 추가한다. `participation_profile=remaining-active-1`은 최상위 `participation_context`를 추가한다. candidates/preview는 `RosterParticipationChangeContext.actor`, memberships/detail/plan은 `RosterParticipationReadContext.members` 안에 `active_assignments`·`preserved_assignments`·`current_character`를 둔다. 기존 strict actor에 새 필드를 끼워 넣지 않는다. 완전 envelope를 대응 component로 검증한 뒤 지정 metadata만 분리하고 기존 본문 DTO를 검증한다.

기존 reader는 memberships 기본/membership-actions-1, detail 기본/membership-actions-1/application-display-1, plan 기본/membership-actions-1이다. beta·group_policy·group_state는 기존 허용 범위 안에서 조합한다. resume는 기존 plan 범위, coordination_wait는 기존 beta 범위다. 새 query가 기존의 잘못된 조합을 허용하지 않는다. 생략/false는 기존 shape, 경고만/참가만/동시는 대응 component를 사용한다. 잘못된 값/조합은400 INVALID_REQUEST, schema 미지원은503 RECRUITMENT_COMMAND_NOT_READY다. 기존 인증/접근/세대/CAS/만료 오류는 유지한다. capability는 권한이 아니다.

부분 완료 후 교체가 최초 성공한 **방·실제 주차·세대**를 capability 대상으로 고정한다. 단순 누락/같은 ID 재등장은 이를 활성화하지 않는다. 이후 재교체·경고 해제·active0이 되어도 살아 있는 해당 세대의 혼합 표현 제한을 유지한다. 다음 실제 주차/새 세대로 자동 승계하지 않는다. 종료 기록 전용 reader는 assignment별 원본을 보존해 기존 계약으로 읽고, 저장된 원 ACK는 새 capability 검사보다 먼저 원래 shape로 재생한다.

능력 표식 없는 live detail/plan·새 쓰기는409 CLIENT_UPGRADE_REQUIRED. 본인 목록은200으로 **영향 항목만** 기존 복구 표현을 사용한다. 기본 reader는 recovery_only=true·room=null·권한 거절, membership-actions-1은 content=null·viewer.mode=recovery·recovery.reason=CLIENT_UPGRADE_REQUIRED·모든 실행 권한 거절이다. beta 필드도 원래 필수/nullable을 유지한다. 실제 참가나 방을 복구 상태로 저장하는 처리가 아니다. 예시 `old_beta_list_one_restricted_item`은 기존 strict component로 검증한 영향/정상 항목이 함께 있는 완전 응답이다.

## M/P·서명·현재 카드

M은 선택한 실제 주차·세대·cycle_member의 현재 active 전체, P는 같은 연결의 완료/종료 보존 assignment다. ID 중복/교집합은0, 참조 revision은 정확히 일치하고 `(item_id,round_id,assignment_id)` 순으로 정렬한다. M의 동일 item 중복을 허용하지 않는다. 원 참가 연결·소유/claim·등록 검사를 유지한다.

후보 기존 `data.actor.assignments=M`, preview 기존 `data.targets=M`, POST 기존 assignment_id/expected_revision 집합=M·target_items=M이다. P는 최상위 metadata로 전달하며 POST body에 새 필드를 추가하거나 기존 journal body를 재작성하지 않는다. M0은 ROUND_NOT_ACTIVE다.

`binding_revision`은 profile·서버 인증 actor·room/cycle/실제T/generation·membership/cycle_member/relation revision·정렬한 M/P의 ID/revision/캐릭터/역할/자리·P 보존 근거·관련 그룹 정책/일정/기한 revision의 정규화 snapshot 해시다. 대상 후보 선택과 무관한 actor binding을 후보/preview에서 동일하게 검증한다. context 서명은 이 binding에 선택 캐릭터/활동/소유/자격 revision·정책 snapshot·만료를 함께 묶는다. 클라이언트가 해시를 생성하거나 토큰을 조립하지 않는다. 최종 transaction에서 다시 읽어 CAS·최종 시각을 확인한다. 완료/교체 경합으로 M/P가 바뀌면409·전체 rollback·재조회이며 남은 일부 자동 성공은 없다. 이 암호/CAS 동작은 아직 구현·실행 검증하지 않았다.

현재 카드는 `current_character`가 명시한 M의 현재 선택으로 표시하며 과거 P의 정렬 순서로 선택하지 않는다. M은 같은 캐릭터/역할이며 M0이면 current_character=null이다. 완료 카드의 이름·편성·역할·일정은 기존 assignment별 snapshot에서 표시한다. P metadata는 연결 참조이며 과거 표시 원본을 대체하지 않는다. 일정/worker/완료/탈퇴도 이 공통 해석을 적용해야 하며 새 metadata만 추가하는 것으로 구현 완료가 아니다.

## Bootstrap·presence·캐시

`GET /v2/me/account-bootstrap`와 `GET /v2/me/game-accounts/{registration_id}/characters` 모두 `include_roster_presence=true`를 지원하는 후보다. bootstrap의 registrations[].characters와 단독 characters가 **동일한 RosterPresence_LifecycleCharactersOut**을 사용한다. 각 item.roster_presence는 state=present|missing|unknown, observed_at은 unknown만 null이다. 루트 roster_presence_scope는 registration_id/version·ownership_revision·roster_revision·presence_revision·evaluated_at을 제공한다. bootstrap마다 원정대별 추가 HTTP를 만들지 않고 같은 배치 projection/근거 조회를 재사용한다. 원본 행/설정/페이지를 삭제하거나 표시 projection을 전체 관찰 증거로 사용하지 않는다.

같은 등록/소유/원정대/생명주기·관찰 근거 snapshot은 두 경로에서 같은 presence_revision을 만든다. 불투명 해시의 대소 비교나 서로 다른 응답의 원자성을 가정하지 않는다. 샘플 두 경로의 scope와 items가 동일한 것을 검증한다.

- opt-in 응답: 회원/환경·등록 scope·요청 generation이 현재일 때 명시 상태를 적용한다. missing만 표시에서 숨기고 present는 같은 ID 누락을 해제한다. unknown은 현재 정상으로 합성하지 않는다. 마지막 관찰을 별도 stale 정보로 남길 수 있지만 현재 판정으로 사용하지 않는다.
- 생략 응답: presence 생략을 present로 해석하지 않는다. 기존 기본 DTO의 관련 scope/revision이 같으면 별도 presence 캐시를 보존한다. 변경됐으면 unknown으로 무효화하고 다음 정상 배치 opt-in에서 갱신한다. 캐릭터/원정대별 무조건 추가 요청을 만들지 않는다.
- 명령 전 시작한 읽기·이전 generation 응답은 적용하지 않고 후속 조회로 교체한다. 전역 경고는 전용 권한 있는 전체 summary를 기준으로 하며 표시 목록/presence 일부로 정상0을 합성하지 않는다. 읽기 실패와 authoritative 정상0을 구분한다.

## 검증과 다음 담당

후보 schema/합성 JSON 검증과 실제 API 동작은 다르다. 완전 beta 목록/상세/후보/preview·원래 기록/ACK·bootstrap/characters 예시, 권한 없음 false/0 및 잘못된 unknown/ACK 확장을 거절하는 예시를 검증한다. Native의 고정 후보 기존 본문 소비 대조는 전체15번째로 수용됐다. 새 metadata DTO 전범위/실연결은 별도다. 다음 Backend가 합의 후보를 기준으로 공개 wire·M/P 공통 해석을 구현하고 격리 DB·HTTP/OpenAPI·경합/rollback을 검증한다. 기존 내부 고유23PASS를 새 공개 계약 검증으로 전용하지 않는다. Penpot·화면·기기는 별도 지시 전 보류다.
