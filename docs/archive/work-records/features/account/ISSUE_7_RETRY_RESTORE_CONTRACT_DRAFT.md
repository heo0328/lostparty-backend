> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [api-keys](../../../../features/login-account/api-keys/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Lost Ark 호출 대기·본인 기기 키 복원 추가 계약 제안

2026-10-15. [Flutter 추가 회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6172594991) 기준. 기존 구현 SHA38d66dadab1e91b6721aee64f6f32c7b0fa5c14d의 인수 완료가 아니라 추가 계약 검토다. [Flutter 수용 회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6172746952)으로 아래 계약이 합의되었다. 보완 구현 요청을 확인했으며 Backend 코드/OpenAPI에 반영했고 검증·로컬 적용 결과는 아래 구현 상태가 기준이다.

## 호출 제한 안내

[공식 usage guide](https://developer-lostark.game.onstove.com/usage-guide)의 API Request Limit 예시는 Reset=1668659557을 UNIX timestamp로 설명한다. [getting started](https://developer-lostark.game.onstove.com/getting-started)는 epoch time/long 및 client100/min을 명시한다. 이 근거로 Reset을 UNIX epoch **초**의 절대시각으로 해석한다. 남은 초로 처리하거나 임의 ms 환산을 하지 않는다. 실제 실키 응답 관찰은 미실행이다.

외부 응답의 Limit/Remaining은 bounded nonnegative integer로만 파싱하고 raw header/body는 공개하지 않는다. Remaining=0의 성공 응답 또는 HTTP429를 관찰하면 해당 token HMAC fingerprint의 upstream blocked_until을 PostgreSQL에 공유한다. 키버전/회원 변경으로 같은token 대기가 초기화되지 않는다. 다른token은 독립이다. 이미 전송된 요청은 기존 결과/credential version 정책을 유지하고 새 외부 호출만 보류한다. 캐시hit/저장자료GET에는 추가 호출이 없으므로 대기를 이유로 열람을 막지 않는다.

Reset이 누락/비숫자/음수/이미지남/현재보다300초초과라면 해당 관찰 시점부터 **60초** 유한 기본 대기. 유효 미래 Reset은 그 절대시각 사용. 이미 알려진 대기는 새 관찰에서 max로 병합하되, 새 실제제한관찰 없이 로컬차단 자체로60초를 계속 연장하지 않는다. 기간 경과시 새 명시요청을 허용하고 무기한잠금/즉시반복호출을 피한다. Remaining/Limit이 누락되어도429는 기본대기를 적용하며 정상200의누락헤더만으로차단하지않는다.

서버 자체80/min RATE_LIMITED는 기존 rolling-window 최오래 이벤트 만료 시각으로 계산하고, upstream429 UPSTREAM_RATE_LIMITED와 구분한다. 양쪽 제한이 동시에 알려져 있으면 실제 요청 가능 deadline은 두 deadline의 max이며 upstream제한이활성이면UPSTREAM_RATE_LIMITED로안내한다. 공용fallback/전체호출동기화서비스/자동sleep-retry없음.

### 응답 추가 위치

단건 game 업무 오류의 `error` 내부에 `retry_after_seconds`와 `retry_at`을 추가한다. 제한 오류에서는 두필드를 모두 제공, 다른오류는 생략 가능(있으면null). `retry_after_seconds`는 integer>=1의 초, `retry_at`은 timezone UTC RFC3339 string. 현재 GameErrorDetail에 optional nullable 두필드를 추가하는 안이며 이를 공유하는 계정/회원설정/회원키 오류 DTO는 새필드를 인식해야 한다. 기존 auth 전용 오류 DTO는 변경하지 않는다. 실제 field 추가 시 route별 serializer/OpenAPI를 함께 맞춘다.

단건 RATE_LIMITED HTTP429 및 UPSTREAM_RATE_LIMITED HTTP503의 Retry-After 헤더는 동일 응답의 retry_after_seconds와 일치한다. 서버DB 현재시각 t와 실제blocked deadline d로 `max(1,ceil((d-t).total_seconds()))`를 계산, retry_at은d의UTC절대시각이다. 반올림으로 남은초가 1초미만 차이날 수 있으나 헤더/JSON 초값은 같다. 입력 header의epoch/rawmetadata를그대로노출하지않는다.

HTTP200 전투력 결과는 **PowerResult item**에 required nullable `retry_after_seconds:int>=1|null`, `retry_at:UTC|null` 두필드를 추가한다. 실패/보류 RATE_LIMITED 또는UPSTREAM_RATE_LIMITED에두값, 그밖의성공/실패/skip/키거절은null/null이다. batch200에는 전체 Retry-After를 붙이지 않는다. 기존 power_reason/reason 구분은 유지한다. 일반 캐릭터 GET의 CharacterOut에는 새필드를 추가하지 않는다.

partial failure cache10초가 upstream60초를 가리지 않게 해당요청에서 현재deadline을 다시읽어전달한다. 키정상과provider제한을혼동하지않으며 앱이 키교체/로그아웃으로 처리하지 않는다. Flutter는 deadline기준대기안내·해당동작비활성→기간경과후명시재시도/new command key. 동일 멱등key의완료replay는과거응답이며 자동 새호출을하지않는다. 과거retry_at이지났으면재시도판단은현재시각으로하며새외부호출이또제한될수있다.

transport가관찰한metadata는비밀없는내부결과로전달하고, orchestration에서quota상태를기록한다. power worker의업무DB/cache쓰기금지와기한뒤결과미반영을유지한다. 늦은transport의제한정보도새자료쓰기와분리하며다음실행에서정의/검증한다. 최소token대기테이블및cleanup을추가할수있지만실구조는Backend소유다.

## 본인 키 복원

기존 metadata GET은 바꾸지 않는다. 새 **POST `/v1/me/lostark-api-key/restore`**를 제안한다.

- 앱 Bearer 본인회원/현재세션 필수. body 엄격 `{expected_version:integer>=1}` 한필드, 추가필드/query거절.
- 200 `{token:string,version:integer>=1}` 두필드. token/version은 같은 잠금된 credential행에서 복호화한다. no-store, 외부LostArk호출·키저장/버전증가없음.
- 원문을 RequestResult에 보관하지 않도록 **Idempotency-Key를 요구하거나 멱등결과로저장하지 않는다**. read-only POST이므로 응답유실시같은expected_version으로재시도가능. 현재버전이바뀌면409 LOSTARK_KEY_CHANGED. 현재키가없으면409 LOSTARK_KEY_NOT_CONFIGURED,복호화설정/무결성실패503 LOSTARK_KEY_UNAVAILABLE. 앱세션오류는기존401/403.
- Flutter는 로그인/새환경에서metadataGET→등록상태/버전확인→restorePOST→회원/서버별기기보안저장소에저장한다. 본문키를등록화면에표시하거나log/debug/analytics/cache/평문설정에남기지않는다. 서버는restore response/body 원문을진단/로그에남기지않는다.
- 서버의user/credential읽기및응답구성은키수정과같은transaction잠금기준을사용한다. 응답구성이후다른기기에서키가변경될수있으므로전역실시간동기화는보장하지않는다. Flutter는회원/서버/세션/진행요청generation·키version이달라졌거나로그아웃한뒤도착한응답을버린다. 이후명시적metadata재조회에서새버전이면재복원/삭제를반영한다.
- 서버등록성공과기기보안저장실패는부분성공이다. 서버키를자동삭제하거나기존원문을자동업로드하지않는다. 앱은서버등록상태와기기복원/로컬사용가능상태를구분하고기기저장재시도는restore로진행한다. 서버DELETE와기기삭제의일부실패도분리안내한다.
- logout시Flutter가해당회원기기원문을정리해도서버키는삭제하지않는다. 게스트/다른회원이이전회원기기키를사용하지않게한다. TLS가구성된서비스에서전달하며현재개발loopback연동과운영HTTPS인수를구분한다.

이API의명시적원문복원만사용자새방향으로확대하고공용키자동배정·기존기기키자동업로드는금지한다. 기존UI에키원문표시/전체빌드서버전환·별도secret서비스를추가하지않는다.

## 검증·후속

Flutter는 오류 DTO 확장 위치/PowerResult 두필드·필수nullable 의미, readonlyPOST restore/expectedversion/no-dedup에차이가있는지검토한다. 합의후 Backend가 mock정상/누락/invalid/past/과도미래Reset·Remaining0/429·token격리/기간만료/부분결과/replay·헤더JSON일치,복원본인격리/동일version·교체삭제race/세션/원문미로그·서버및기기부분실패경계를구분해구현한다. 실키한도소진시험/사용자키원문자료요청없음.

독립적인구현은실provider관찰을기다리지않고공식예시+mock으로진행한다. 38d66da는기존개인키구현기준이며새복원/대기계약은이번보완게시SHA로인계한다. 합의된보완구간검증·commit/push후새정확한OpenAPI SHA로인계한다.

## 수용 후 구현 주의

성공200/Remaining0인 현재 응답은 성공으로 유지하고 다음 외부 호출만 보류한다. 늦은 transport의제한관찰은캐릭터/cache/멱등성공쓰기와분리하며관찰한tokenfingerprint에만deadline max로기록한다. 키교체후새token대기에옛응답을적용하거나현재deadline을단축하지않는다. 기존기한/회원·credential version fencing은그대로다.

Flutter 현재 ServerPowerResult는정확한필드집합검사이므로새requirednullable필드응답과호환되지않는다. Backend보완게시만으로기존앱연결/사용자인수완료로표현하지않는다. 새immutable OpenAPI SHA를인계한뒤Flutter가새DTO/키reason/복원·대기UI를연결한다. Backend보완구현·자동검증이완료되었으며Flutter연결/실사용인수는별도다.

## 구현 경계

`app/lostark_keys/rate_limits.py`의 control observer를 orchestration에서 해당token fingerprint로 생성해 transport에 전달한다. worker가 늦게 끝나도 이 observer는 **별도 limiter transaction만** 기록한다. 캐릭터/power cache/업무 멱등 결과는 worker가 쓰지 않으며, 기존기한과최종credential fencing을유지한다. 업무결과폐기와provider대기관찰보존은구분한다. 관찰시각은서버UTC,응답대기계산은DB현재시각이다.

같은조회합류자는기존실패를받을때알려진token대기를읽어시간을전달한다. 전투력cached 제한실패는현재deadline을읽고,제한만료후에는기존10초실패cache로재시도를막지않는다. 일반성공cache/GET은대기를이유로차단하지않는다. provider-limit행은만료후2분이상지난경우기존cleanup에서정리한다.

추가API의정확한공개DTO는원본OpenAPI의LostArkKeyRestoreIn/Out,GameErrorDetail(optionalnullable시간),PowerResult(requirednullable시간)이다. REST26개operation이있으며provider-limit1table의additive0006을사용한다. 실제검증·로컬반영·게시상태는 [실행 안내](ISSUE_7_DEVELOPMENT.md)와Issue최신인계댓글에서확인한다.
