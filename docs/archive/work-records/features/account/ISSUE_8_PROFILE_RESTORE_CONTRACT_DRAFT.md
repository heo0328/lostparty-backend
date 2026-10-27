> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [power-and-profiles](../../../../features/rosters/power-and-profiles/README.md) · [activity-and-presentation](../../../../features/rosters/activity-and-presentation/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #8 — 역할별 분석 요약·개인 표시 저장/복원 계약안

2026-10-15. [Flutter 신규 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6191438610)과 [부분 수용/보완 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6192838766)을 반영한 2차 검토안. 최초안의 outcome 및 회원 전역 표시 설정은 이 수정안으로 대체한다.

## 상태와 기존 계약 대조

[Flutter 계약 수용/P1 구현 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6193638580)으로 수정 계약이 수용됐다. 아래 검토 당시 미합의/미구현 표현은 이 확인으로 대체하며 현재 P1 범위/검증/미구현 P2는 [실행 안내](ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md)를 따른다. Backend 기준 구현/OpenAPI는 c91af2e, 작업 HEAD는 dc09901(feat/representative-selection)이다. 새 기능/OpenAPI/DDL/구현 SHA 없음. 본 검토 문서는 로컬 미커밋·미push·dev 미반영이며, 협업에 필요한 전체 제안은 Issue 댓글 본문에 직접 게시한다. 실제 개발 DB0007/API 전환·live proof/퇴역·자료 이관/삭제·배포는 별도다. 기존 미커밋 문서는 보존한다.

| 기존 계약 | 재사용 | 부족한 부분 |
|---|---|---|
| V1 등록 목록 + V2 현재 캐릭터 | 본인 canonical UUID/account·등록/소유/캐릭터 수명과 현재 상태 | 역할별 Flutter 분석/개인표시 저장 없음 |
| V1 character-settings·대표 GET/PUT | 활동·대표·공유 settings_version | 선호역할/정렬/숨김과 의미가 달라 확장하지 않음 |
| V1 member-settings | 회원별 nice_group_auto_refresh_enabled/version | 역할요약 저장 없음. 회원bool로 NiceGroupPolicy 직업군 자동검사 포함/제외 |
| V1 combat-power/refresh·V2 power 표시 | provider에서 서버가 관찰한 수치/시각 | Flutter 전체 Armory 분석 결과 저장 아님 |
| game_account_requests | 회원/operation/key·30초 lease/generation·완료응답24시간/추가24시간 tombstone | 새 operation과 성공 replay의 현재 리소스 접근 검사 필요 |

더 최신의 역할요약/표시 복원 게시 계약은 현재 저장소에 없다. 원본 OpenAPI에 미합의 경로를 추가하지 않는다. Flutter S3b1394PASS/분석0은 모의 HTTP/SQLite 보고이며 실서버/기기 인수와 구분한다.

## 제안 경로와 DTO

모두 Bearer 본인 회원·Cache-Control:no-store. 외부 provider 호출/키 복호화 없음. strict DTO·unknown body/query 거절, UUID 엄격검사, bool/string을 정수로 자동변환하지 않음. 모든 응답 속성은 필수, 값 없음은 명시 null. GET은 body/임의 query 없이 조회하며 행을 만들지 않는다. 아래 이름·수치 상한·기본값은 수용 전 제안이다.

1. `GET /v2/me/characters/{character_id}/personal-profile`
2. `PUT /v2/me/characters/{character_id}/role-summaries/{role}` (`dealer|support`)
3. `PUT /v2/me/characters/{character_id}/personal-preferences`
4. `GET /v2/me/game-accounts/{registration_id}/presentation-settings`
5. `PUT /v2/me/game-accounts/{registration_id}/presentation-settings`

canonical 목록은 기존 등록/V2 조회가 원본이다. 새 GET은 canonical ID의 개인 보조자료만 반환하며 이름검색·활동/대표/소유 생성·새 목록 원본이 아니다. 1차는 단건 GET으로 복원하고 전체 roster 수집 후 제한된 동시성으로 읽는다. 새 bulk/전체 빌드 API는 제안하지 않는다. 다량 복원 비용이 문제면 별도 합의로 페이지 읽기를 추가한다.

personal-profile 응답:

```json
{
  "character_id": "11111111-1111-4111-8111-111111111111",
  "game_account_id": "22222222-2222-4222-8222-222222222222",
  "ownership_revision": 1,
  "lifecycle_revision": 1,
  "lifecycle_state": "active",
  "dealer": {"version": 1, "summary": null, "saved_at": null},
  "support": {"version": 1, "summary": null, "saved_at": null},
  "preferences": {"version": 1, "preferred_role": null, "visible": true, "display_order": null, "saved_at": null}
}
```

GET은 권한·현재 소유/수명 metadata와 개인자료를 동일 DB snapshot에서 읽고 직렬화한다. GET은 현재 본인 소유 canonical의 active/suspect를 읽을 수 있다. suspect에서도 기존 자료는 보존·표시하며 최종 사용 허가로 보지 않는다. 미저장 역할은 version1/summary=null/saved_at=null, 미저장 개인설정은 위 기본값. 캐릭터의 같은 ID에서 수명 revision이 바뀌어도 기존 역할요약은 지우지 않으며 summary의 관찰 수명과 현재 수명을 비교해 재확인 표시한다. 회원/소유 수명 변경 시 다른 회원 자료를 공개하지 않는다.

### 역할별 PUT

입력은 `{expected_version, expected_ownership_revision, expected_lifecycle_revision, summary}` 4필드 필수/null 불가다. UUIDv4 Idempotency-Key 필수. 대상과 role은 path로만 받는다. 성공200은 `{character_id,role,ownership_revision,lifecycle_revision,version,summary,saved_at}`이며 role은 path와 같다.

summary는 아래 속성만 갖는 strict 객체다.

| 필드 | 타입/제안 상한·의미 |
|---|---|
| source | 고정 `flutter_analysis` |
| analysis_rules_version | 1~64 ASCII `[A-Za-z0-9._-]+`. 식별자이며 숫자/시간 정렬 근거 아님 |
| analyzed_at | UTC RFC3339 시각. 클라이언트 주장 분석 시각이며 서버 검증/수집 시각 아님 |
| combat_power, item_level | 각각 null 또는 1~32자리 비음수 십진수 문자열. 공백/쉼표/지수/NaN/음수 거절, 소수점 앞뒤 숫자 필수 |
| combat_power_observed_at, item_level_observed_at | 각 값이 null이면 반드시 null, 값이 있으면 UTC RFC3339 필수 |
| integrity_status | `clean|review|error|unavailable`. 분석 무결성 상태이며 HTTP/저장 성공 여부와 별개 |
| catalog_version | null 또는 1~64 ASCII `[A-Za-z0-9._-]+` 문자열. Flutter 무결성 판정에 쓴 카탈로그 식별자. 미확보면 null |
| issues | 최대20개 strict `{code,severity}`. code 1~64 ASCII `[A-Z0-9_]+`, severity=`warning|error`, 중복 pair 거절. raw/자유문장/장비명/토큰/임의 metadata 없음 |
| observed_lifecycle_revision | 양의 엄격정수. 해당 분석이 묶인 수명이며 PUT expected_lifecycle_revision과 같아야 함 |

기존 outcome은 제거한다. 모든 업로드는 역할 확정·정상 분석 경로·유효한 로컬 저장을 마친 요약이며 HTTP200은 서버 저장 ACK다. 무결성 판정은 아래 명시 필드로만 복원하고 빈 issues/시각/catalog_version만으로 clean을 추론하지 않는다.

| integrity_status | 허용 issues 조합 | 의미 |
|---|---|---|
| clean | 빈 배열 | 필요한 판정이 완료됐고 문제 없음 |
| review | warning 1개 이상, error 없음 | 확인 필요 사항이 있으나 아래 unavailable 수준의 판정 불가와 구분됨 |
| error | error 1개 이상, warning 동반 가능 | 분석에서 확인한 규칙 위반 존재 |
| unavailable | 빈 배열 또는 warning만, error 없음 | 역할은 확정됐지만 무결성 결론을 낼 검증 근거가 부족함 |

예: ArkGridMinimumIntegrity 부재·issues=[]는 unavailable로 보존 가능하며 clean으로 바꾸지 않는다. 판정 불가 부분과 확인된 error가 함께 있으면 error+해당 warning으로 요약한다. 전체 무결성 상태가 기존 Flutter에서 다르게 계산되는 사례가 있으면 adapter 구현 전에 매핑을 대조한다. unknown status/금지 조합은400 INVALID_REQUEST. null catalog_version은 네 status 모두에서 형식상 허용하며 상태를 자동 변경하지 않는다. nonnull도 판정 가능/최신성을 보증하지 않는다. 숫자 카탈로그 버전이 있다면 Flutter adapter에서 같은 식별자의 십진수 문자열로 정규화하고, 스키마 dataVersion/analysis_rules_version과 혼용하지 않는다. 서버는 이 카탈로그를 다운로드/검증하지 않는다.

공통 후보 code: GEM_SLOT_COUNT/FOREIGN_CLASS_GEM/UNMATCHED_SKILL_GEM/ARK_GRID_MINIMUM/ARK_GRID_CONDITION은 error, SAME_CLASS_GEM_UNVERIFIED/GEM_UNAVAILABLE은 warning. raw BuildNotice·slot·장비명·자유문장은 받지 않는다. adapter는 rune/grid의 추가 notice도 고정 범주로 정규화하고 중복 제거하며 info를 warning/error로 승격하거나20개 초과를 임의 절단하지 않는다. 최종 매핑은 Flutter가 adapter 구현 전 고정한다. 서버는 기존 제안대로 code 형식/개수/중복·상태조합을 검증하고 미인식 code는 UI에서 일반 확인 안내로 표시한다.

Flutter 회신에 따라 양역할 combat_power/item_level로 현재 요구를 충족하며 별도 버프력/환산/임의 metrics는 추가하지 않는다. 역할 판정 불가/통신·파싱·로컬저장 실패는 업로드하지 않는다. unavailable 무결성은 이러한 전체 분석 실패와 다르며 역할/수치가 유효하면 저장할 수 있다. 저장된 판정은 새 소유/활동/파티 자격을 만들지 않는다.

timestamp는 분석/관찰 출처 설명용이고 다중기기 승자 결정에 사용하지 않는다. 숫자/시간 형식검사만으로 자료의 진위를 보장하지 않는다. source·role·관찰 수명은 DB에도 구분 저장한다. 이번 요약은 기존 Character.summary/ScopedPowerCache/퇴역이력/provider 관찰값에 덮어쓰지 않는다.

역할별 독립 version1 시작, 첫 유효 summary 저장은2, 같은 payload의 새key/no-op도 expected version 먼저 검사한 뒤 version 유지. 실제 summary 변경만+1, saved_at은 서버 commit 시각(UTC)이다. dealer 저장은 support/version/saved_at을 전혀 변경하지 않는다. PUT body UTF-8 JSON 전체32KiB 초과는413 REQUEST_TOO_LARGE(신규 제안), 초과 chunked body도 읽기 중 제한한다. summary=null 초기화/DELETE는 이번 제안에서 제외한다.

### 개인설정과 표시 개수

personal-preferences PUT 입력은 `{expected_version,expected_ownership_revision,expected_lifecycle_revision,preferred_role,visible,display_order}` 전부 필수. preferred_role=`dealer|support|null`, visible=strict bool, display_order=null 또는 엄격정수0~2147483647. 성공200은 `{character_id,ownership_revision,lifecycle_revision,version,preferred_role,visible,display_order,saved_at}`. 역할요약과 독립 version, 실제 변경만+1. 숨김/정렬/선호는 활동/대표·소유/나이스단 자격을 변경하지 않는다.

display_order는 **같은 회원·canonical game_account·소유수명 안의 캐릭터 rank**다. 원정대를 섞는 전역 rank는 폐기한다. 동일값 허용·캐릭터별 독립 ACK·부분저장 대기는 수용 회신대로 유지한다. 한 행 변경으로 다른 행을 재번호화하지 않는다.

원정대별 presentation GET200/PUT200은 동일 strict DTO다. 모든 속성 필수이며 saved_at만 nullable:

```json
{
  "registration_id": "33333333-3333-4333-8333-333333333333",
  "game_account_id": "22222222-2222-4222-8222-222222222222",
  "registration_version": 1,
  "ownership_revision": 1,
  "version": 1,
  "visible_count": 6,
  "saved_at": null
}
```

위 응답은7필드다. version/registration_version/ownership_revision은 양의 엄격정수. 미설정은 version1/visible_count6/saved_atnull, 행생성 없음. visible_count는 null 불가·엄격정수 **1~200**(현재 원정대 roster 상한). 기존 제안의 null=전체/0=접기/회원전역4000개는 폐기한다. 현재 목록이6개 미만이면 있는 수만 표시하고 저장값을 줄이지 않는다. PUT body는 `{expected_version,expected_registration_version,expected_ownership_revision,visible_count}` 전부 필수/null 불가·Idempotency-Key(UUIDv4) 필수·4KiB 상한. 첫6/no-op은version1 유지, 실제 변경만version+1/saved_at서버UTC. 전체 character-settings/settings_version·활동/대표·역할요약과 독립이다.

canonical game_account의 데이터 키는 회원+game_account_id+ownership_revision이고 경로 registration_id는 접근/등록변경 fence다. GET/PUT 모두 본인 활성등록→canonical 연결→현재소유 검증. 미인증 preview(account_id=null)는403 OWNERSHIP_REQUIRED이며 기본6을 서버저장 성공으로 반환하지 않는다. 이름으로 account를 만들지 않는다. 같은원정대 비메인등록도 사용 가능하며 메인전용이 아니다. 존재하지않음/삭제/타인등록은404 REGISTRATION_NOT_FOUND, 본인등록 소유상실은403 OWNERSHIP_REQUIRED. 새 PUT의 등록/소유/표시version stale은409 REVISION_CONFLICT, 같은값도 기대version 먼저 검사한다. 새 session에서도 동일 수명/권한 확인 후 복원 가능하다.

등록해제 시 해당 경로의 GET/PUT/replay 접근 차단, 이 계약으로 저장자료를 즉시 삭제하지 않는다. 이후 **신뢰된 기존 연결로 같은 canonical account·회원·동일 ownership_revision**의 새 활성등록을 얻으면 기존 표시 설정을 다시 읽을 수 있다. 새등록의 version으로 새명령을 만들며 옛 registration 경로/명령을 새경로로 자동 이식하지 않는다. 다른 account/새 소유수명/회원에는 기본6이며 과거 설정을 승계하지 않는다. 소유수명이 바뀌었다가 원래회원으로 돌아와도 옛값 자동복원 없음. 장기 보관/실자료 삭제정책은 별도다. 이 규칙은 이름 기반 재등록 연결을 새로 허용하지 않는다.

표시 설정은 캐릭터를 선택하는 명령이 아니므로 해당원정대 일부 suspect 때문에 원정대 표시개수 PUT을 막지 않는다. 개인 캐릭터 preferences PUT의 suspect 쓰기 보류는 기존안대로다. 장비/나이스단/활동완료를 새 선행조건으로 요구하지 않는다.

화면은 같은 원정대 안에서 visible=false를 제외하고 **현재 저장 대표 우선→사용자 display_order(nonnull오름차순, null후순위)→아이템레벨 수치 내림차순(null후순위)→이름 오름차순→canonical UUID 오름차순**으로 정렬한 앞 visible_count개를 표시한다. 대표가 hidden인 경우 강제로 되살리지 않으며 선호표시는 대표 변경이 아니다. item_level은 해당 화면의 기존 출처 선택 규칙을 유지하되 서버관찰/역할요약을 구분하고, 서버는 display_order를 저장할 뿐 raw 분석으로 fallback을 재계산하지 않는다. Flutter는 기존 숫자/이름 비교기와 canonical UUID 최종 tie-break를 사용한다. 대표가suspect여도 현재저장대표라는 표시와 사용불가를 구분하며 자동교체하지 않는다. 예전 기기 로컬 대표를 canonical에 이름으로 연결하지 않는다.

## 현재 회원/수명·저장 권한

새 역할요약·개인설정 쓰기는 현재 활성 본인 등록이 있는 canonical에 한정한다. 등록ID/이름/로컬ID를 canonical로 추정하지 않는다. 회원/세션→활성 등록·현재 소유권→캐릭터/NameClaim·현재 수명→expected versions를 짧은 transaction에서 검증한다. 현재 이름 claim 충돌/retired·suspect 쓰기는 보류하되 기존 요약은 임의 삭제하지 않는다. 선호설정도 최초안은 같은 수명 검증을 쓰며 suspect 개인설정 편집 허용이 필요하면 수용 때 분리한다. 이는 파티·활동의 새 사용 제한 정책이 아니라 잘못된 수명에 개인자료를 저장하지 않는 경계다.

요약 저장은 활동선택·대표·레이드 조건·서버 Lost Ark 키·회원 나이스단 ON을 요구하지 않는다. 나이스단은 기존 회원 공통 bool만 사용한다. nice_group_auto_refresh_enabled=false면 NiceGroupPolicy 직업군의 활성 캐릭터를 자동검사에서 제외하고 true면 포함한다. 비활성은 양쪽 모두 제외, 추가 캐릭터별/원정대별 bool이나 AND 정책은 만들지 않는다. OFF는 새 Armory/분석을 시작하지 않는 조건이며 이전 유효 summary의 미확정 전송복구까지 금지하거나 대기를 삭제하는 조건이 아니다. 자동 분석 대상/스케줄링은 Flutter가 결정하며 이 API로 나이스단 OFF를 임의 실패/부정으로 변경하지 않는다. ON/OFF를 바꿔도 기존 요약을 삭제하지 않는다. 기존 장비/소유 증거 보류를 우회하지 않으므로 canonical 미확보 사용자는 로컬 대기일 뿐 서버 복원완료가 아니다.

개인자료 키는 회원+canonical UUID+ownership_revision(+role)로 분리한다. ownership_revision은 개인자료의 소유 수명으로 쓰며 lifecycle_revision은 분석 출처/fence다. 같은 이름 새UUID·새회원/소유수명에 자료를 승계하지 않는다. 등록 삭제/소유 상실 시 접근 차단, 이름으로 재연결 없음. 실제 퇴역 시 관련 개인자료 정리를 기존 내부 retire transaction에 통합하되 live 퇴역은 여전히 비활성이다. 정확한 장기 보관/등록해제 후 정리 시점은 별도 정책이며 이번 migration으로 원본을 파괴 정리하지 않는다.

## 멱등·충돌·영속 대기

- operation 분리(`role-summary`, `character-preferences`, `account-presentation`), 회원+operation+UUIDv4 key. digest에 path target/role 및 모든 입력필드를 넣는다. 원정대표시 operation은 registration 경로도 digest에 포함하고 현재 등록/소유수명 접근을 replay 때 검사한다. 표시 replay는 현재 registration_version이 label 등으로 달라졌어도 접근·동일소유수명이 유지되면 과거 ACK 반환 가능하며, expected version을 다시 적용하지 않는다. 현재값은 GET으로 확인한다. lease30초/generation fencing, 진행중409 REQUEST_IN_PROGRESS/Retry-After2, 다른payload409 IDEMPOTENCY_CONFLICT. 업무 쓰기와 완료응답 저장은 동일 transaction이다.
- 성공 replay는 완료시점부터24시간, 이후24시간 tombstone/IDEMPOTENCY_EXPIRED, 48시간 이후 key 재사용 방지 보장은 없다. 기존 구현의 reserve/release/cleanup을 재사용하되 resource replay 검증을 추가한다. 완료 전 retryable lease도 무기한 기록 보존은 아니므로 로컬 대기에 최초 발송시각과 확정 여부를 보관한다.
- replay도 현재 회원/세션·본인 활성등록·현재 소유 수명을 검사한다. 삭제/타인/preview404, 소유상실403, retired 또는 현재 수명 불일치409로 과거 개인정보 반환을 막는다. 현재 접근가능해도 응답은 역사적 ACK이며 현재 version은 GET이 원본이다. replay로 현재 값을 재적용하거나 개인자료를 부활시키지 않는다.
- 같은key/body로 응답유실을 복구한다. expected_version stale은 같은값이어도409 REVISION_CONFLICT. GET 후 expected version만 자동 올려 오래된 대기를 새key로 덮어쓰지 않는다. 다른기기 변경이면 최신값/로컬 대기를 보존해 충돌 안내·명시 선택 또는 재분석으로 새명령을 만든다.
- 앱은 환경/회원/캐릭터/소유수명/역할별 대기를 분리하고 immutable 발송명령(key/body/expected version/최초발송시각)과 아직 발송하지 않은 새 초안을 분리한다. 진행/불명확한 옛명령 종료 전에 같은역할 새명령을 보내지 않는다. ACK 삭제는 해당 command에만 적용해 이후 새초안을 지우지 않는다. 반대역할은 독립이다.
- 동일회원 재로그인도 세션 fence와 현재 등록/소유/수명/서버version을 재조회한다. 미발송 초안은 현재 version 일치 시 발송 가능. 이미 발송한 불명확 명령은 보장기간 안에서 원래key/body로 먼저 복구하며 version 재조회 결과로 body를 바꾸지 않는다. 재로그인/환경변경의 늦은 결과를 버린다. 완료시각을 모르는 불명확 명령은 최초 발송 후24시간 이내를 자동 복구의 보수적 상한으로 쓰며, 이후에는 GET/명시 재확인으로 전환한다.
- 성공24시간 경과/미완료48시간 경과 시 blind retry 금지. 현재GET과 payload 비교가 같으면 현재 복원자료는 확인할 수 있지만 특정 과거명령의 완료증명은 아니다. 미확정 명령 정리는 알려진 lease 종료·서버시각/전환 지연을 고려하고 사용자 재확인 후 새명령으로 진행하며 무조건 자동재발송하지 않는다. 무기한 exactly-once를 약속하지 않는다.
- provider/로컬저장 실패·취소는 새 summary 업로드/기존 정상값 null 덮어쓰기를 만들지 않는다. 나이스단OFF는 새 자동분석을 만들지 않고 기존 유효 pending 복구/요약은 보존한다. 유효한 review/error/unavailable 분석 요약 저장과 HTTP/저장실패는 다르다. 서버 ACK 전 UI는 서버 저장 대기/충돌/확인불가를 유지한다.

## 오류·한도

기존 GameErrorOut `{error:{code,message,request_id,...}}` 사용. 400 INVALID_REQUEST(필수/nullable/strict/형식/query), 기존401/403 세션·정지, 404 CHARACTER_NOT_FOUND(없는/타인/preview/본인활성등록없음), 403 OWNERSHIP_REQUIRED(본인등록이 있으나 소유상실), 409 CHARACTER_UNUSABLE(suspect/retired), 409 IDENTITY_CONFLICT(claim불일치), 409 REVISION_CONFLICT(소유/수명/개인version), 기존멱등409, 413 REQUEST_TOO_LARGE, 분류가능한일시장애503 SERVICE_UNAVAILABLE. 입력원문/타인자료는 오류에 포함하지 않는다. 새 사용자 cooldown/활동제한이나 provider 호출 quota를 이 저장 API에 도입하지 않는다. 기존 공통429가 적용되는 경우에만 Retry-After를 따른다. 오류를 empty/default 성공으로 처리하지 않는다.

## DDL·검증·진행 단위

L1a0007 위 additive 후속 migration(번호는 구현 시 확정):

- character_role_summaries: `(user_id,character_id,ownership_revision,role)` PK, user/character FK, role check, version>=1, 최소 summary JSONB(서비스 strict 검증), saved_at. canonical account를 추가 저장하면 character 복합FK로 일치 보장. lifecycle 관찰revision은 summary에도 보관한다.
- character_personal_preferences: `(user_id,character_id,ownership_revision)` PK/FK, preferred_role/visible/display_order/version/saved_at 제약.
- account_character_presentation: `(user_id,game_account_id,ownership_revision)` PK, user/account FK, ownership_revision/version>0, visible_count1~200/saved_at 제약. 등록ID는 소유수명 자료의 PK로 저장하지 않음. 대표/캐릭터 퇴역이 원정대 표시count를 지우거나 재번호화하지 않음.
- 기존 UUID/FK/요약/cache/설정·legacy 기기자료 보존. GET 기본값은 가상값, PUT에서만 행생성. 회원별 자원 lock/현재 game mutation lock 규칙과 dedup 최종화 순서를 따른다. 네트워크 대기 없음. 퇴역 정리·성공 멱등 ACK 원자성/rollback도 함께 검증한다.

수용 후 구현 단위: P1 역할요약 GET/PUT+기반 migration/멱등 → P2 개인표시/선호+정리경계 → 각 격리검증·원본OpenAPI 반영·commit/push/원격확인·같은Issue 인계 → Flutter adapter/영속대기/복원 연결. 실제DB/API전환·사용자인수는 별도다. 최소검증은 회원/소유수명/새UUID 격리·양역할 독립/null·상한/strict·GET무쓰기·동일 version경합한승자·응답유실/lease takeover/rollback/replay현재접근검사·오래된대기충돌/24~48시간·suspect보존/퇴역정리·provider값불변·migration기존자료보존이다. 이번은 문서검토이므로 기능테스트/DB/API를 재실행하지 않는다.

## 다음 담당과 완료 조건

Flutter의 부분수용을 반영해 역할핵심수치·version/멱등/격리 원칙은 유지하고, 무결성4상태/nullable카탈로그·outcome제거·원정대별 기본6개로 보완했다. 다음 Flutter는 상태/issue 매핑과 catalog_version 정규화, 원정대별 DTO/상한·정렬/등록해제 경계를 대조해 수용/필요수정만 같은Issue에 회신한다. 특히 기존 대표숨김/수치출처 선택이 위 표시규칙과 다른 경우 그 차이를 확인한다. 수정안 합의 후 P1/P2 구현 구간을 별도 요청할 수 있다. 이번 검토는 기능구현/새wire adapter·실제DB/API/플래그ON·migration/배포·삭제 승인이 아니다.

[최초 Backend 검토 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6191634445) 이후 본 수정안이 충돌하는 항목을 대체한다. 나머지 strict/상한/독립version/lease·충돌·출처/수명·실행경계는 유지한다. 문서 미커밋·미push·dev미반영·새구현/OpenAPI SHA 없음.

[Backend 2차 계약 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6193183186) 게시 완료. Flutter 수정안 대조/수용 후속.

## P1 구현 게시 상태

수용된 P1 구현/원본OpenAPI `6e4f625c3b62c92ec412373b33ed8a3441af8149` 일반push·원격확인·[인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6194881739) 완료. 검토 당시 미커밋/미구현 표현은 이 범위에서 대체한다. 이 문단의 P2 미구현/가상기본값은 P1 게시 당시 범위다. P2 구현/정확한 호환 경계는 [P2 실행안내](ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md)를 따른다. 실행/검증/후속은 [P1 실행안내](ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md)를 따른다. 실제DB/API전환·dev/main통합은 없다.

## P2 구현 게시 상태

P2 구현/원본OpenAPI `7027f0b690e1c232fafc5d09faa9d6c169c99962` 일반push·원격확인·[인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6195735441) 완료. preferences는실제복원스키마로전환했고개인설정PUT/원정대표시GET/PUT·내부정리기반을제공한다. 검토당시미구현표현은이범위에서대체하며 [P2 실행/호환](ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md)이현재기준이다. dev/main미통합·실제DB/API/live퇴역은미전환이다.
