# Issue53 — 즉시 저장 기본 정렬·문맥 계약 보완

2026-11-14 / 정적 조사·계약 후보, 미구현.

## Backend — 기본 정렬 보존·정확 계약 보완안 / DB 초기화는 사전 확인 필수

전체12의 실제 Native 정렬을 기준으로 전체11의 rank/UUID 기본안을 정정합니다. 아래는 정적 조사 후 **계약 후보**이며 API/OpenAPI/DB 구현이 아닙니다.

### 사용자 초기화 방침 정정
사용자는 기존 유저 자료 보존 때문에 구조/기능을 추가할 필요는 없다고 했지만, **로컬·dev·운영 모든 DB의 초기화는 실행 전에 반드시 사용자 확인을 받아야 한다**고 명시했습니다. 초기화 가능성을 실행 승인으로 해석하지 않습니다. 지금 초기화/키·환경·볼륨 삭제를 하지 않았고 Native도 임의 초기화하지 말아 주세요.
이번 추천안은 기존 Configuration.version과 preferences.display_order를 재사용할 수 있어 **초기화가 필요하지 않습니다.** 기존자료 전용 이관/이중원장/legacy 순서 복원 기능도 추가하지 않습니다. 순서원자성·CAS·기존 API/원ACK 보존은 데이터 이관 장치가 아니라 실제 동시소비 계약이므로 유지합니다.

### 1. 기본순서와 첫 드롭
대표 표시우선은 별도 단계로 두고, 전체 비퇴역 canonical 문맥의 기본순서를
**display_order ASC(null 마지막) → item_level DESC(null 마지막) → character_name ASC → UUID ASC**
로 만듭니다. 대표는 이 수동/기본순서에서 제거·rank0으로 쓰지 않고 표시할 때만 맨앞입니다. Native가 알려준 기존 순서와 맞춥니다.
서버 Character.summary.item_level과 Character.character_name, preferences.display_order를 같은 RR에서 읽습니다. 기존 roster/lifecycle reader 역시 summary의 item_level을 반환하고 power overlay는 전투력 표시용이므로 실시간 provider/전투력재수집으로 정렬하지 않습니다.
- 레벨은 유한 비음수 decimal 수치로 비교, null/비수치 관측은 정렬값null(0/적격으로 추정하지 않음). 원천정규화·파서 상세는 Native 기존 itemLevel 변환과 대조합니다.
- 이름은 locale/대소문자 변환 없이 UTF-16 code-unit 사전순을 후보로 명시합니다(Dart 문자열 비교와 교차언어 일치를 위해). 이름/레벨이 UI DTO에서 다른 방식으로 변환되는 부분이 있으면 Native가 차이를 알려 주세요. 추가 사용자 제품 결정이 아니라 기술 comparator 대조 항목입니다.
- 새 관리화면은 **v2 GET의 ordered_all_character_ids와 동일 관측의 characters**를 기준으로 표시/첫드롭을 해석합니다. 서로 다른 시점의 기존 캐시 level/name을 섞지 않습니다. 초기 렌더링 때 두 정렬의 동등성을 fixture로 대조합니다.
- GET/ON·OFF/대표 변경에는 rank를 전혀 쓰지 않습니다. 최초 드롭도 movable 순서가 현재와 동일하면 no-op으로 두어 기본 정렬을 임의 수동고정하지 않습니다.
- 실제 순서가 달라지는 드롭만 전체기본순서의 movable 슬롯을 교체하고 결과를0..N-1 rank로 확정합니다. 미활동/대표/누락캐릭터의 상대위치는 보존하고 숫자rank 자체는 불변 조건이 아닙니다. 이후 신규 null캐릭터는 rank뒤에서 같은 level/name/UUID 기본정렬을 따릅니다.

### 2. 관측버전·순서지문
order_digest=소문자SHA-256 hex64. 회원/원정대/ownership_revision·정렬policy·**전체 canonical 집합의 ID/rank/정규 level/이름과 결과순서**를 같은 관측으로 지문화합니다. 관측시각/전투력/role/visible은 지문에서 제외합니다. 대표우선은화면정책이며대표/활동변경은settings_version으로 검사합니다.
기존 roster_revision뿐 아니라 실제 정렬입력 지문을 재검사하므로 갱신이 level/name/rank를 바꾸거나 새캐릭터를 추가하면 옛 드롭은409입니다. 서버가 최신정렬을 기준으로 옛사용자 드롭을 조용히 재해석하지 않습니다. Native는 최신GET 후 사용자가 실제 본 목록과 의도를 다시 적용해 새key 명령을 만듭니다. 송신한 원key/body는 변경하지 않습니다.
같은 game write lock에서 CAS→최종선택/대표/순서·지문 검증→rank부분갱신→settings_version/변경된preferences version·ACK저장을 한 트랜잭션으로 처리합니다. role/visible은 DB현재값을 보존합니다. 신규 preferences가 필요할 때만 기존기본 null/true를 사용합니다.

### 3. 지원량·정확 wire 후보
전체 비퇴역 문맥은 **최대1000명**, 최종 활동선택은 **1..200명**으로 분리합니다. GET/PUT에서1001행 sentinel이면413 CHARACTER_CONTEXT_TOO_LARGE, 잘라 전체문맥을 가장하거나 페이지를 나눠 저장하지 않습니다. 1000은 새 가입/데이터삭제 정책이 아니라 관리문맥 지원 상한이며 구현 때 비용을 측정합니다.

신규 GET/PUT /v2/me/game-accounts/{registration_id}/character-settings. 모든 객체 closed/additionalProperties=false.
GET/성공PUT 같은200 envelope:
- scope={registration_id,game_account_id,registration_version,settings_version,ownership_revision,roster_revision,policy_version:'character-management-1'}.
- data={configuration_state,activity_character_ids,representative_character_id,ordered_all_character_ids,order_digest,characters,evaluated_at}.
- configuration_state=unconfigured/configured/needs_reconfiguration. activity 최대200, ordered_all/characters 최대1000, canonical lowercase UUID·중복금지. representative_character_id만nullable UUID이며 configured면활동집합 안에 존재해야 합니다.
- characters 각행={character_id,display_order(nullable 0..2147483647 정수),item_level(nullable decimal문자열),character_name(필수1..64),usable(bool),blocked_reason(nullable 기존정책코드)}. UUID별정확1행/전체ID집합동등. item_level은 비교값의정규 decimal문자열(지수/쉼표없음), 길이1..64/비음수, null기본표시. 현재 Character 이름원본/기존 API의 형식을 대조해 고정하며 가짜이름은 만들지 않습니다.
- 별도 ineligible_character_ids는 중복제공하지 않고 characters 중 usable=false인 activity 행으로 도출합니다. blocked_reason은 null 또는 CHARACTER_UNUSABLE/IDENTITY_CONFLICT. 소유권없음은행별false가아닌GET/PUT전체403입니다. 이명령은current-owned 관리문맥이지preview목록API가 아닙니다.
- evaluated_at은UTC Z/0..6소수초 관측시각. versions는1..2147483647 정수, 지문64hex. 시각/UUID검증은새DTO경계에만적용합니다.

PUT 필수:
activity_character_ids, representative_character_id(필수 nonnull UUID), expected_registration_version/expected_settings_version/expected_ownership_revision/expected_roster_revision, expected_order_digest.
선택필드 ordered_character_ids는 **생략=순서보존**, **null=400**, **[]=최종활동이대표한명일때만유효**입니다. 제공하면 최종활동-대표 집합과 정확히 같아야 하고 최대199명입니다. duplicate/집합누락·잘못된rank형식은400 INVALID_REQUEST. 외부 원정대/비소유 캐릭터는현재자격/대상 정책으로404/403, EMPTY_ACTIVITY_SELECTION/REPRESENTATIVE_REQUIRED·CAS409는기존규칙을유지합니다.
등록/소유/문맥상한 확인 후 final activity의모든캐릭터를기존 activity_policy로검사합니다. 기존 선택에누락/usable=false가남아있으면사용자수정이필요할수있으며순서변경으로자동OFF/삭제하지않습니다. Native는경고·명시변경/복구와거절을표현해야합니다. 이자격차이를우회하려고기존경계를완화하지않습니다.

### 4. no-op·응답유실·현재조회
유효CAS에서선택집합/대표/구성상태가동일하고 순서생략 또는현재movable과동일하면no-op: settings/preference version·rank/saved_at을변경하지않습니다. 단, unconfigured→configured 첫명시확정은상태변경이라no-op이아닙니다.
성공ACK은커밋당시 완전문맥이며변경여부와무관하게같은응답형태입니다. 같은key/body는저장된원ACK, 같은key다른본문은기존멱등충돌코드로거절합니다. 재송신시현재데이터로ACK를새로만들지않습니다. 권한확인은기존규칙을지킵니다.
새key명령성공은그명령의의도세대에만적용하며다음대기의도는반환문맥에재적용합니다. 과거명령복구/세대불확실·409·ACK후조회실패는**새v2 GET으로현재확정**하며PUT전체재실행/원ACK최신상태간주를하지않습니다. GET실패면이전확정값/에러표시이며성공이나초기버전1로위장하지않습니다.
같은원정대write lane·회원/환경/인증epoch·늦은응답폐기·원pending보존은전체11과같습니다.

### 검증·다음 담당
Native는 기존기본정렬 comparator와v2 canonical GET목록 사용, 전체1000/활동200·413, 위closed DTO/eligibility/no-op·옛ACK/GET 절차를대조해 주세요. 합의 후 Backend가 JSON Schema/정상·거절예시 및실제writer/동시수정·최초드롭/부분rollback 검증을고정합니다. 이번은소스정적조사/문서대조로신규API·DB/시험/서버변경을실행하지않았습니다.
**DB초기화는필요없고실행하지않았습니다. 추후필요해져도대상·영향을알리고사용자의명시확인전에는실행하지않습니다.** 문서는같은feat/my-account-contracts 로컬미커밋·미push,운영배포/Issue종료없음입니다.
