# Issue53 — main-only 단일 사용자대표 계약 조사

2026-11-14 / 기존026a74f 기준 정적조사, 계약제안·미구현.

정확한 후속안은 [정책2 Schema/예시·자동 선정·원 ACK 복구](character-management-contract/policy2/README.md)와 [전체29 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873152385)를 따른다. 아래 전체26의 추천 중 최신 정책과 충돌하는 내용은 당시 이력이다.

## 최신 정책 — 전체28 Native 사용자 결정

[전체28 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6872855905)의 사용자 최종 결정에 따라 메인 전환 후 대표 재선택 대기 추천은 대체됐다. 유효 대표가 없으면 현재 메인 원정대의 활동·소유·usable 후보에서 아이템레벨 DESC → 전투력 DESC → 이름 ASC로 자동 지정한다. 기존 유효 대표는 관측값 갱신만으로 교체하지 않는다. 메인 전환도 같은 명령·게임 쓰기 lock·트랜잭션에서 대표를 확정하며 부원정대 시절 raw 대표를 그대로 승격하지 않는다. 후보 없음은 별도 예외로 다루고 가짜 대표/비활동 자동 활성화로 우회하지 않는다. 카드 수동 순서와 그룹 snapshot은 보존한다.

다음 담당 Backend: 정책2 정확 Schema/예시에 최초 확정·미설정 복구·메인 전환의 명령/버전/ACK 경계, 정규 관측값 출처·nullable/decimal/이름 비교, 동률·혼합 이름·후보 없음 예시를 고정한다. 저장 관측값 재사용·전투력 null 후순위·외부 provider 추가 호출 없음은 Native 제안으로 정확 계약 대조가 남았다. 부원정대 null/활동 전체 movable·정책1 journal/원 ACK 복구 요구는 유지한다. 이번 댓글은 기획 확정·계약 보완 요청이며 새 구현/시험/게시 결과가 아니다.

아래 본문은 전체26 당시 조사·제안 이력이다. 최신 정책과 충돌하는 재선택 대기·자동 지정 금지 추천은 현재안으로 사용하지 않는다. 정책2는 아직 미구현이다.

## Backend — main-only 계정대표 조사·최소 변경 제안 (미구현)

전체23 정책요청·24/25 UI조치를 현재 게시026a74f 코드와 대조했습니다. 계정대표는 메인 원정대의 활동캐릭터1명만, 부원정대는 대표선택/표시/자동선정이 없다는 사용자 정책을 수용합니다. **이번은 조사/계약 제안이며 서버/DB/API를 아직 변경하지 않았습니다.**

### 1. 현재 코드 사실
- Registration의 uq_registration_main partial unique index는 회원당 활성메인 최대1개를 보장합니다. 메인이 반드시 존재한다거나 유효대표가 항상1명이라는 보장은 아닙니다.
- representative.PUT만 is_main을 검사합니다. v1 settings와 현재v2 management는 원정대별 Configuration.representative_id·대표포함을 사용합니다. 따라서 사용자지적대로 부원정대 저장과 사용자대표 의미가 섞여 있습니다.
- accounts.reg_out / lifecycle 조회의 settings / bootstrap의 representative.value도 현재 원정대raw대표를 반환할 수 있습니다. 부원정대의 대표우선·그룹기본값을 UI만 막아도 이 서버 reader는 자동으로 바뀌지 않습니다.
- make_main은 기존메인의is_main=false/version++와 신규메인 설정 및 해당 patch의 version++를 같은게임쓰기 lock/트랜잭션으로 처리합니다. 현재v2 expected_registration_version으로 대상의메인변경을감지할기반은있습니다.
- 그룹 생성은 명시 registration_id/character_id·소유/usable·revision을 검증하고 입력캐릭터를 그룹representative_display/가입display snapshot으로 저장합니다. 가입selected_character는 활동집합을 검증하지만 **자동으로메인계정대표를조회하는서버경로는아닙니다.** 즉 서버가그룹기본값으로메인1명을항상선택한다고확인된것은아닙니다. 기본계정대표의자동채움은Native의기본값준비와구분해대조해야합니다. 그룹의명시캐릭터선택을이번정책만으로main전용으로제한하지않습니다.

### 2. 추천: 기존 자원의 의미 정정, 새 API/이중원장 없음
기존 v2 character-settings 경로를 유지하고 계약을 **character-management-2**로 갱신하는 안을 추천합니다. scope에 필수 is_main(bool)을 추가합니다. closed DTO/policy literal이 바뀌므로 Native DTO와맞춰로컬에반영하며현재v1계약을새v2로재해석하지않습니다. 새대표endpoint/동일기능profile·별도대표원장은추가하지않습니다.

GET:
- 메인: 현재소유와저장설정을읽고 대표는저장된메인대표를반환합니다. null/목록밖/unusable 복구문맥은기존대로허용합니다.
- 부원정대: representative_character_id는항상null입니다. 저장raw대표가남아있어도계정대표로노출하거나유효성/정렬/초기설정의기준으로쓰지않습니다. GET은raw를지우지않습니다.
- characters/ordered_all과activity·usable경고는유지합니다. 부원정대는대표없음만으로needs_reconfiguration/잘못된활동경고를만들지않습니다. 기존state가needs_reconfiguration이면실제활동의잔여/usable문제를분리해표현해야하고GET이자동configured로쓰지는않습니다.

새 v2 PUT:
- representative_character_id는필수키·nullable로확장합니다. 메인은현재본인활동중usable대표(nonnull)를요구, 부원정대는null만허용합니다. 부원정대에nonnull을새로선택하려는요청은409 MAIN_REGISTRATION_CHANGED로닫고재조회합니다.
- 부원정대의활동최소1/최대200은그대로유지하되대표포함/대표OFF금지는적용하지않습니다. raw대표캐릭터도다른활동과똑같이OFF가능합니다. 최초configured도활동만으로확정됩니다.
- ordered_character_ids: 메인은최종activity−대표 exact set, 부원정대는**최종activity 전체** exact set. 생략은rank보존. 부원정대활동최소1이므로부원정대빈배열은거절, 메인대표1명은빈배열허용입니다. 최대movable을부원정대200/메인199로구분합니다. 비활동슬롯·기본정렬/지문·no-op은기존원칙을유지합니다.
- 부원정대의명시v2 저장시raw대표를null로정리하는안을권장합니다. 이는GET/배치초기화가아닌사용자가누른정상관리명령의의미이며선택/순서와같은트랜잭션입니다. raw가실제로정리되면settings_version을올려한번의변경으로ACK합니다. 자동대표로채우거나별도정리요청을추가하지않습니다.
- 서버는현재is_main을기준으로조건을검사합니다. scope.is_main은단순UI장식이아니며메인변경은기존expected_registration_version/settings_version·게임lock으로다시검사합니다. 클라이언트가is_main=true를자기주장해권한을얻을입력은추가하지않습니다.

### 3. 기존 v1/원pending 최소 처리
v1 SettingsIn은이미대표nullable이고 SettingsOut/RepresentativeOut도대표nullable입니다. 경로·필드형태를유지할수있습니다.
- 새 v1 쓰기도서버현재main을검사합니다. 메인은선택/대표포함기존정책, 부원정대는활동만으로유효하며대표null을받을수있게합니다.
- 과거부원정대raw값을보낸**미확정원문**은현재raw와정확히같을때만legacy round-trip값으로허용하고그값을선택/대표자격·대표OFF금지에쓰지않는안을제안합니다. 임의다른캐릭터를대표로새지정하는nonnull은거절합니다. 숨은대표자동선정은하지않습니다. raw가이미정리돼옛원문과다르면409로명시거절합니다. 클라이언트가본문/키를고쳐재송신하지않습니다.
- 이호환경로는기존v1원명령/실제구버전소비의안전장치이지과거DB이관·이중원장추가가아닙니다. 신규 Native는부원정대에null을사용하고기존pending을새v2로변환하지않습니다.
- 이미성공한원ACK는과거결과로재생합니다. 당시nonnull대표가있어도현재계정대표로채택하지않고현재GET으로확정합니다. 과거ACK를새정책DTO로자동재작성/삭제하지않습니다. 현재 API의GET/신규명령 응답만main-only의미로정리합니다.
- 현재v2旧본문도대표nonnull필수였으므로같은round-trip예외를낡은정책writer에무조건추가하기보다 **Native기존v2 journal에미확정명령이있는지대조**가필요합니다. 있다면원요청복구/명시409·현재GET 절차를보존하고원ACK의정책버전은과거형태그대로검증해야합니다. 기본목표는새profile을늘려두writer를영구운영하는것이아닙니다.

### 4. reader와 그룹 snapshot
같은트랜잭션/snapshot에서사용자의현재메인등록을선별하고그등록의설정만사용자대표로해석하는공통selector를재사용합니다. 대상은 representative GET/value, settings projection, reg_out.representative_summary, bootstrap/lifecycle의대표표시입니다. 부원정대의사용자대표필드는null, 메인이라도대표미선택/자격상실이면타원정대후보로대체하지않고복구필요로표현합니다. 별도clock/provider/카드별대표조회는추가하지않습니다.
그룹생성/가입의기본값은Native에서현재main등록/계정대표의같은버전문맥으로채워야합니다. 서버의명시입력검증·그룹대표/가입snapshot은유지하고계정대표변경/메인변경때기존그룹snapshot을일괄덮지않습니다. '기본값'과'그룹의최종명시선택'을같은권한규칙으로단정하지않습니다.

### 5. 메인 변경 시 추천 처리·확인 필요
메인변경은새로운사용자행동이므로단일대표공개범위도그명령에서전환합니다. 기존메인은즉시사용자대표노출대상에서제외합니다. 신규메인의부원정대시절raw값을숨은대표로자동승격하는것은추천하지않습니다.
**추천은메인전환명령이신규메인의raw대표를null로정리하고대표선택필요상태로전환**하는것입니다. activity/rank는유지하고새메인의settings_version·등록버전을올려현재조회로재선택하게합니다. 기존그룹snapshot은변경하지않습니다. 메인이이미같은등록이면이정리를반복하지않습니다. 이행위는DB초기화가아니지만기존필드변경이므로계약에명시해Native UX와대조한뒤구현해야합니다.
메인이없는회원/미소유메인/대표미설정에는대표0명이정상인중간상태이며자동으로다른대표를만들지않습니다. '단한명'은유효대표최대1명의권위이며임의첫캐릭터로항상1명을강제하지않는것이추천입니다. 사용자께서메인전환때기존사용자대표를유지하는다른동선을원하면이부분은추가제품결정이필요합니다.

### 다음 단계
Native는 (a)scope.is_main/policy2·부원정대null/활동전체movable, (b)v1 raw round-trip/기존v2미확정journal 현황과옛ACK 검증, (c)메인전환시자동승격없이대표재선택 추천, (d)그룹기본값실제소비경로를대조해주세요. 그결과로정확Schema/전이예시를고정하고별도지시후구현합니다.
이번은정적조사/계약제안이며기능시험/DB쓰기·초기화/배포/commit/push를하지않았습니다. DB초기화는필요없고모든환경에서사용자사전확인없이실행하지않습니다.
