# Issue #8 — 첫 화면 저장 정보 일괄 조회

기준2026-10-18 / [전체145번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247415075). 실제 계약 원본은 `openapi/openapi.yaml`이다. 기존 로컬 Docker API8000/DB0016을 사용한다. 새 표·마이그레이션·이중 저장·자료 이관은 없다.

## API와 응답

`GET /v2/me/account-bootstrap` / Bearer / 200 JSON / Cache-Control:no-store. query와 body는 받지 않는다. 다른 회원/캐릭터 ID 입력은 허용하지 않고 서버의 현재 로그인 회원 등록 관계에서 범위를 구한다. 기존 단건 GET/쓰기/V2분쟁 endpoint와 DTO/정책은 보존한다.

| 필드 | 의미 |
|---|---|
| server_now | 스냅샷 조회 시작 시 DB 절대시각, UTC RFC3339 |
| complete | 항상 true. 등록·기본 목록·활동 대상의 성공 응답을 임의로 자르지 않음 |
| registrations | 삭제되지 않은 본인 등록, created_at/id 순서. 미등록이면 [] |
| registrations[].registration | 기존 RegistrationOut 전체: 본/부·소유/인증·등록/원정대/설정 revision·활동/대표/기본 요약 |
| registrations[].characters | 기존 V2 LifecycleCharactersOut 전체. 현재 캐릭터 기본 목록·상태/usable/차단 근거·power 관찰. 이 응답 next_cursor는 항상 null |
| registrations[].representative | 기존 RepresentativeOut. 현재 소유일 때 설정 미생성도 unconfigured/default version으로 반환, 미인증/소유 상실은 null |
| registrations[].presentation | 기존 PresentationOut. 현재 소유 기본 visible_count=6/version=1/saved_at=null. 미인증/소유 상실은 null |
| registrations[].personal_profiles | 기존 PersonalProfileOut 목록. 현재 소유의 활동 캐릭터 전체에 두 역할 저장요약/문제·확인시각/version 및 개인 선호/순서/표시. 활동 ID 순서 |
| registrations[].unavailable_characters | 활동 참조 중 퇴역/조회 불가 ID 또는 현재 이름 점유 충돌은 character_id와 CHARACTER_UNUSABLE/IDENTITY_CONFLICT를 명시. 이 ID의 profile/weekly는 반환하지 않음 |
| weekly_states | 기존 WeeklyStates: current_cycle/cycle_key/catalog_version/entries. 같은 조회 시각의 KST수요일06시 주차·허용된 활동 대상별 전체 카탈로그 레이드의 저장 완료/점유·revision/차단 근거 |

현재 소유지만 활동 미선택이면 개인profile/weekly entries는 빈 배열이며 기본 캐릭터 목록은 유지한다. 숨김 캐릭터/표시 개수 밖 캐릭터와 나이스단 OFF도 활동이면 저장 개인profile 복원 대상이다. 비활동 캐릭터의 개인profile은 이 응답에 포함하지 않으며 기존 단건GET으로 필요 시 조회한다. 대표가 비활동이어도 기존 대표 DTO/기본 요약은 유지한다.

미인증/소유 상실은 기존 registration.preview 기본 투영만 characters에 반환한다. 캐릭터 ID=null·usable/eligible=false·OWNERSHIP_REQUIRED, power 값/관찰시각=null이다. 다른 회원의 canonical 캐릭터 상세·개인profile·선호·저장 power를 노출하지 않는다. 기본 등록의 character_count 의미는 기존 RegistrationOut과 같다. 본인 등록이 없는 타회원 자료는 응답에 없다.

개인설정/역할요약 미생성은 기존 GET처럼 default version=1/saved_at=null, 역할 summary=null, preferred_role=null/visible=true/display_order=null이다. 저장한 역할의 integrity/issue/observed_lifecycle_revision을 고쳐 쓰지 않는다. suspect이지만 본인 소유/현재 claim이 맞으면 기존 GET과 같이 profile/주간 근거를 복원하고 사용 불가는 별도 usable/mark_blocked_reason으로 표시한다. 자료가 없는 것과 기존 활동 ID가 사용 불가한 것을 구분한다.

## 일관성과 부작용 경계

하나의 PostgreSQL REPEATABLE READ / READ ONLY transaction에서 DB시각·회원/세션·등록·소유·roster/settings/lifecycle/현재 이름 claim·개인자료·주간 근거를 읽는다. 별도 단건HTTP/다른session 배치를 호출하지 않는다. 같은 스냅샷 안에서 읽은 값을 조합하므로 중간에 소유권/활동 변경이 commit돼도 전후 상태가 섞이지 않는다.

주차는 처음 캡처한 server_now로 딱 한 번 계산한다. 수요일06시 경계를 처리 중 넘으면 응답 전체는 시작 시 주차이며 다음 조회가 새 주차를 반환한다. 읽기 응답이 미래 쓰기 권한을 예약하지는 않는다. 후속 쓰기는 기존 현재 권한/revision/CAS·주차 검사를 계속 수행한다. Flutter도 회원·환경·generation, pending/outbox·미저장 편집 보호를 유지해야 한다.

외부HTTP/provider 갱신/회원 키 복호화·장비인증·자동 활동/대표 선택·캐시 저장·명령 ACK/자료 삭제가 없다. 기본값은 응답 투영이며 DB 행을 만들지 않는다. 기존 앱 실행 시 실제 목록 갱신·활동 상세 검사/준비GET→PUT→후속GET은 별도 후행이다.

## 범위·쿼리·크기

현재 등록 한도20개, 원정대당 기본/활동 캐릭터200개로 최대4,000개를 완전 복원한다. 기존 주간 GET의50-ID 제한은 그 endpoint 입력 제한으로 유지한다. 새 endpoint는 같은 스냅샷에서 모든 허용 활동의 현재 주간 행을 한 번에 읽고 동일 entry 투영을 재사용하므로50개 이후를 자르거나 독립된 transaction으로 조회하지 않는다. 현재 카탈로그5개 기준 최대20,000 weekly entries다.

DB 조회는 자료 종류별 배치이며 캐릭터별 SELECT를 하지 않는다. power는 회원 범위의 최신 정상 관찰/현재 lifecycle 최신 확인을 각1개씩 가져와 기존 overlay 정책으로 합친다. 개인자료는 현재 소유 revision만 읽는다. 프로필/주간을 새로 저장하거나 파생 표에 복제하지 않는다. 실제 최대범위 statement 수·처리시간은 DEV_LOG에 기록한다. DB 엔진의 기존 statement/lock timeout은 유지한다.

응답 JSON은 UTF-8 **16MiB**까지다. 20/200 한도를 넘는 저장 상태는409 BOOTSTRAP_LIMIT_EXCEEDED, 직렬화 결과가16MiB를 넘으면409 BOOTSTRAP_RESPONSE_TOO_LARGE로 전체 실패한다. 임의 truncation·성공 빈 배열·부분 성공은 없다. 최대 대상 수 안이라도 저장 역할요약이 많으면 크기 제한에 걸릴 수 있다. Flutter는 이 명시 오류 때 기존 단건/페이지 조회를 계속 사용할 수 있다. 이 초기 실험은 모든 최대 역할요약을 무조건 한 응답에 담겠다는 보장이 아니다.

## 오류와 예시

기존 GameErrorOut `{error:{code,message,request_id}}`와 상태 코드를 사용한다.

| 상태 | code/의미 |
|---|---|
| 400 | INVALID_REQUEST — query/body 입력 |
| 401 | 기존 ACCESS_INVALID/ACCESS_EXPIRED/SESSION_REVOKED/SESSION_EXPIRED 등 |
| 403 | ACCOUNT_DISABLED |
| 409 | BOOTSTRAP_LIMIT_EXCEEDED / BOOTSTRAP_RESPONSE_TOO_LARGE. 부분 결과가 아니며 기존 읽기 경로로 대체 가능 |
| 503 | BOOTSTRAP_DATA_UNAVAILABLE — 저장값이 기존 DTO와 불일치. 또는 SERVICE_UNAVAILABLE — DB/transaction 오류. 빈 정상 목록으로 대체하지 않음 |

[완전한 합성 응답 예시](contracts/account-bootstrap.examples.json)는 빈 회원·본인 활동1개/레이드5개·크기 초과 오류를 포함한다. 실제 회원 자료가 아니다.

빈 회원 응답(현재 주차 예시):

```json
{"server_now":"2026-10-18T08:00:00Z","complete":true,"registrations":[],"weekly_states":{"current_cycle":{"server_time":"2026-10-18T08:00:00Z","cycle_key":"2026-10-14","starts_at":"2026-10-13T21:00:00Z","ends_at":"2026-10-20T21:00:00Z","timezone":"Asia/Seoul"},"cycle_key":"2026-10-14","catalog_version":"2026.08.20","entries":[]}}
```

```json
{"error":{"code":"BOOTSTRAP_RESPONSE_TOO_LARGE","message":"BOOTSTRAP_RESPONSE_TOO_LARGE","request_id":"00000000-0000-4000-8000-000000000001"}}
```

성공 응답의 기존 nested DTO는 새 nullable/기본 규칙으로 변형하지 않는다. unavailable_characters는 생략하지 않는 배열이며 없으면 []다. 저장자료 오류/버전 충돌을 profile=null로 숨기지 않는다.

## 검증·인계

본인/타회원·미인증/소유상실/숨김·단건투영동일·기본행미생성·쓰기/외부HTTP0·기본미설정/누락/최대/크기초과·동시소유/활동 변경·주차경계/점유·캐시 선택과 관련 단건 권한을 격리 PostgreSQL로 검증한다. 실행 결과와 게시SHA/브랜치/push/실행8000 반영은 DEV_LOG 및 인계 댓글을 따른다. Flutter 기기에서 같은 계정/설정의 displayReady/weekly·요청 수 비교는 계약 연결 후 별도다. 최초서버수치만으로 체감 개선 완료를 보고하지 않는다.

최종표적/관련회귀 **261PASS/158.21초**, 기존Starlette/AnyIO경고1개. 최대4000대상은10,607,440bytes·20statements·0.902초(격리PG/TestClient). 로컬8000최종이미지·실행OpenAPI전체일치·공개4개200/신규경로비로그인401·DB0016/50표행수전후동일을확인했다. 실제회원인증GET/Flutter연결/기기성능비교는미실행이다.

구현/계약 `8d03e962b48917c4b0f0dec28d285ca993b9de2d` / feat/raid-services push·원격SHA확인완료. [#8 전체146번째 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247620588) 후 다음담당은Flutter 연결/관련표적검증·동일조건기기비교다. dev/main은미병합이다.
