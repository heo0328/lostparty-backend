# Issue #8 — 공식 provider schema 조사·제공 가능성 판정

2026-10-15. [#8 요청](https://github.com/heo0328/lostparty-backend/issues/8)과 [보완 질문](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183781483)의 독립 Backend 조사 결과다. **공개 공식 Swagger 원문 확보·schema/현재 코드 대조 완료**. 기능 구현/실provider 캐릭터 관찰·소유권 검증 완료가 아니다. 대표 API 구현cd3e003·인계기록c4e21bf와 별개이며 현재 feat/representative-selection의 문서 변경이다.

## 1. 실제 원문 위치·버전·재현

이전 /api-docs/characters 등 접근 실패 기록을 보완했다. 공식 [시작 안내](https://developer-lostark.game.onstove.com/getting-started)의 공개 HTML은 API 항목을 클릭하면 data-path를 소문자로 바꿔 `/swagger-doc/endpoints/{name}`을 SwaggerUIBundle에 지정한다. 다음 **소문자 URL**로 인증 없이 HTTP200 JSON을 확보했다. 대문자 URL은 paths/definitions가 빈 문서를 반환했으므로 이를 실제 schema로 해석하지 않았다.

| 원본 | 실제 조회 결과 | 원문 SHA-256 |
|---|---|---|
| [Characters Swagger](https://developer-lostark.game.onstove.com/swagger-doc/endpoints/characters) | Swagger2.0, info.version=v1, paths1/definitions1, 2,875bytes | ae8f0c0f6155098f54d025f678518b913de286438602974a881f957790c294eb |
| [Armories Swagger](https://developer-lostark.game.onstove.com/swagger-doc/endpoints/armories) | Swagger2.0, info.version=v1, paths12/definitions38, 42,178bytes | eb8f293aa2f70362e3dee9125755162c07aa52f671561b4ce8a6c78bdafe6893 |

해시는 확보 시점의 공개 문서를 식별하며, URL의 불변성이나 게임 데이터 revision을 보장하지 않는다.

원문에 로그인정보/캐릭터명/키를 보내지 않았으며 데이터 조회 API는 호출하지 않았다. 웹 본문 추출 도구는 JSON 접근에 실패했지만 Python 표준 urllib의 공개 URL GET으로 확보했다. 공개 HTML과 JSON은 /tmp에 조사용으로만 저장했고 서버/기기/DB 원본 응답은 수집하지 않았다. info.version=v1은 swagger 문서 표기이며 게임 영구 ID나 데이터 revision이 아니다. 공식 changelog의 최신 기능 버전과 같은 뜻으로 해석하지 않는다.

재확인은 아래 공개 경로에 urllib.request.urlopen을 사용해 응답 bytes의 SHA-256, JSON paths/definitions/properties/required를 비교하면 된다. Authorization/Cookie 주입이나 실회원 token 조회는 필요 없다. URL 외 임의 endpoint 추측이나 제3자 SDK schema를 근거로 삼지 않았다.

## 2. 문서 사실과 미기재 보장

| 대상 | 원문에서 확인한 사실 | 보장하지 못하는 항목 |
|---|---|---|
| siblings 요청 | GET /characters/{characterName}/siblings, path string characterName만 요구 | account_id/character_id/생성세대 입력·페이지/cursor/revision 입력 없음 |
| siblings 성공 | 200 array of CharacterInfo. API 설명은 계정 전체 캐릭터 프로필 반환을 뜻함 | 결과별 totalCount/hasMore/complete/snapshot revision·삭제 사건/생성세대·소유회원 identity 없음. response headers로 전체성을 인증하는 계약도 선언하지 않음 |
| CharacterInfo | ServerName·CharacterName·CharacterLevel·CharacterClassName·ItemAvgLevel의5필드. 문자열4개·int32 정수1개로 현재 parser와 대응 | 영구 캐릭터/원정대/계정 ID 없음. properties required 목록 미선언. 필드 없는/null/상한/반영지연의 세부 보장도 이 정의만으로 확정 불가 |
| ArmoryProfile | 이름·서버·직업·레벨·item level과 CombatPower/string, ExpeditionLevel·TownName 등 표시 속성 | 영구 캐릭터/원정대 ID·생성세대 없음. 원정대레벨/영지/길드 등을 식별자로 사용할 유일성·불변성 보장 없음 |
| ArmoryEquipment | Type/Name/Icon/Grade/Tooltip string의5필드, equipment API는 해당 객체 배열 | Type enum/필수 목록 없음. 슬롯 해제 시 원소제거/null/빈값 의미·모든 슬롯의 완전성·최신 반영시간 보장 미기재 |
| Armory 종합 | /armories/characters/{characterName}의200은 ArmoryProfileAll | 단건 profile/equipment를 합친 원자 snapshot·source revision 보장 미기재 |
| 갱신 지연 | 공식 [FAQ](https://developer-lostark.game.onstove.com/faq)는 게임 데이터가 실시간이 아닐 수 있고 수분 동기화 지연을 안내함 | 30분 후에도 최신이 아니면 문의하라는 안내는 30분 이내 최신성/전체성 보장 또는 소멸 확정 기준이 아님 |
| 404/빈/실패 | 공식 [usage guide](https://developer-lostark.game.onstove.com/usage-guide)는404를 일반 Not Found, 점검503을 설명함 | 404가 캐릭터삭제/개명/원정대소멸임을 구분하는 사건 계약 없음. 빈배열이 원정대소멸이라는 계약 없음 |

위 미기재는 **이번에 확보한 문서/모델 범위의 결론**이다. 공급자 내부에 영구ID가 없다는 주장이나 모든 미래 API에서도 불가라는 뜻이 아니다. 문서상 fields의required가없다는 사실도 실제정상응답에항상null이온다는뜻은아니다. TownLevel의default문자열null 같은표기도 runtime자료로 대체하지않는다.

`CharacterInfo` 요약은 string4개+integer1개다. 현재 parser의 문자열 길이/중복/조회이름1개·최대200/유한한수치 검증은 **우리 adapter의 방어 규칙**이며 공식 schema의 상한·필수성 보장으로 소개하지 않는다. siblings 원문에는 CombatPower가 없고 profile에만 있다. 이력의 마지막 전투력은 서버가 성공 관찰한 profile 값이며 로컬 선호역할 Snapshot 값이 아니다.

## 3. 해석·판정 — 현재 조건에서 어디까지 제공 가능한가

공식 siblings의 전체 조회라는 의미는 확인됐다. 하지만 한 응답이 부분누락/갱신지연/이름재사용으로 영향을 받았는지 식별하는 장치는 확인하지 못했다. **HTTP200/정상배열 전체수신은 API 의미를 따른 관찰이지 공급자 원본과의 일치 증명은 아니다.** 전체조회라는 명세를 서비스의 수용 기준으로 채택하는 정책은 가능하지만, 이를 영구 동일성/오류없는 소멸확정 보장으로 설명할 수 없다. #8의 실패/부분응답 삭제0 기준을 완화하는 별도 합의 없이 자동정리를 켜지 않는다.

| 흐름 | 현재 근거로 내릴 판정 | 필요한 조건/다음 조치 |
|---|---|---|
| 미인증 preview·저장자료GET·표시용 profile | 제공 가능·기존 기능 | 기존유효성/범위/회원키검사 유지, 소유권 생성 없음 |
| 대표GET/PUT | Backend 독립구현/게시 완료 | 현재 소유/활동/confirmed 자격이있는사용자만가능. Flutter연결/실인수별도 |
| 신뢰된 기존 원정대에 새 캐릭터추가 | 조건부구현가능. **소멸용전체성은불필요** | 긍정관찰+검증된account연결+claim충돌없음·현재revision. 현live에서account연결판정근거는미완료 |
| suspect로 사용차단 | 상태/transaction/경합구현은가능 | 기존원정대의신뢰된관찰에서구체적불일치가성립해야함. 요청실패/404/키오류만으로차단하지않음 |
| suspect를동일ID로복구 | 현재문서만으로동일세대보장불가 | 단순재등장/동일직업/레벨/영지/다회동일목록은충분조건아님. 영구ID/생성세대/독립검증또는제한을명시한새정책필요 |
| 소멸확정·퇴역·종속자료정리/claim해제 | 현재합의의증거수준으로live활성불가 | 원정대연속성/신뢰된완전관찰의구체근거또는의미완화를명시한별도합의필요. 횟수/대기시간으로대체안함 |
| 기준이름404뒤다른알려진이름으로조회 | 관찰/후보수집은가능, 자동재연결확정은미완료 | 새후보lookup의형태일치와기존account/세대연결을분리. 모든기존이름소실시자동원정대복구보장불가 |
| 다른원정대옛이름재사용 | 세대/claim분리로오류전파차단은구현가능 | 기존claim미해소면충돌보류. 이름중첩으로소유이전/ID승계하지않음. 새소유인증과기존claim해제는각각근거필요 |
| 장비변경challenge | schema의필드형태는확인, liveproof판정은보류 | Type실값·요청슬롯해제/비요청슬롯유지표현과갱신의실관찰·완전성정책미확인. PROVIDER_EVIDENCE_PENDING유지 |

현재 canonical_candidate는 관찰된서버+이름중첩으로기존account를찾고reconcile는같은이름을confirmed로복구한다. 주석의‘이름만으로추론하지않음’이기술적보장인것처럼인용하지않는다. 현재liveproof보류와 별개로 **향후인증활성화전 반드시바꿔야할 경로**다. 이번문서조사에서소스/API/DB를바꾸지는않았다.

원정대(account) 경계는 공식 siblings의계정그룹과우리서버내부Account가같다는판정이필요하다. 서버명이여러개있을수있는필드를하나의고정원정대ID로해석하거나원정대레벨을대리키로사용하지않는다. 특히같은이름/같은그룹에서조회사이에삭제·재생성됐으면이schema로탐지불가다.

## 4. 독립 구현 단위와 보류 조건

전체조사판정을‘schema접근대기’로남기지않고이번문서로완결한다. 원문확보/필드대조는완료, 필요한보장의미기재는미기재로판정한다. 추가실관찰이증명할수있는것은별도다.

- **L1 검토수용후구현가능**: 기존ID유지+재사용불가세대/lifecycle·NameClaim/이력모델, canonical이름단독추론차단, 모든기존writer/장비/전투력의세대fencing·캐시분리, 최신상태read/이력cursor·정리재적용계약. 실제퇴역/claim해제live는꺼둔상태로모의증거에서PostgreSQL원자성·rollback·순서/동시성·late결과·권한부활0검증가능. 기존V1동작제한/DTO전환을Flutter와합의후게시한다. 새schema근거가없다는이유로DB/동시성구현까지막는것은아니다.
- **L2 장비실관찰단위**: 실제사용자가원할때별도합의된대상/명시행동으로장비Type·요청슬롯해제표현·비요청슬롯유지·실패처리를최소확인한다. 원문키·민감payload를Issue에요청하지않고agent가임의기기/게임상태를조작하지않는다. 장비실관찰성공은영구ID나roster전체성증명이아니며활성화기준을별도판정한다. 이번조사의추가자료로필수요청하지않는다.
- **L3 제품/증거합의전제**: 관찰기반소멸정리/동일ID복구/모든기준이름소실복구. 공급자명시보장또는현재제한을수용한새정책없이는live활성화하지않는다. 현정책을유지할경우suspect보존/충돌보류가정상결과다. 사용자본인앱자료의명시제거는가능한별도제품선택지이나캐릭터실소멸/소유이전/claim자동해제증거가아니다.

기존[생명주기검토안](ISSUE_8_LIFECYCLE_REVIEW.md)의P0~P3·V1/V2/이력의미·기기ID매핑선행은검토단계다. 대표계약수용을L1전체수용으로간주하지않는다. 다음Flutter회신은**본조사판정과L1비활성기반구현구간수용/수정**이다. 추가정책을필요로하는L3는그때영향/선택지를사용자에게제시하고결정하며,지금증거없는자동정리동작을미리확정하지않는다.

## 이번 수행·미실행

공식공개HTML/FAQ·usage guide/Swagger2개read-only조회·SHA/paths/definitions/필드/required대조·현재parser/proof/canonical/reconcile코드대조·문서검증을수행했다. 실회원JWT/캐릭터자료조회0·provider장비조작0·서버/DB/기능/OpenAPI/migration/테스트변경0. 이번문서에새기능/계약SHA·새자동테스트결과없음. 브랜치feat/representative-selection·기존원격c4e21bf, 이번조사문서는미커밋/미push·dev미반영이다. 상대가읽을수있도록필수결과를#8댓글본문에직접회신한다.

[공식 조사/가능성 판정 Issue 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184587789) 게시 완료. 다음은 Flutter의 판정 대조·독립 기반 구현 구간 수용/수정 회신이다.
