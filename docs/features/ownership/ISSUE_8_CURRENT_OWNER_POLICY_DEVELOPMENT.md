# Issue #8 — 현재 소유자 인증 차단·같은 회원 목록 재등록

2026-10-17. 사용자 작업 지시·[102번째 정책](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217677854)·[103번째 Flutter 선행UX](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217851176)·[104번째 Backend 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217953832)를 기준으로 한다. 90번째의 현재본인 재인증 허용은 대체한다. 실제 최초 장비인증1회 성공은 유지하며 소유이전/분쟁은 구현하지 않는다.

## 현재 소유자 차단

기존 start/confirm 경로와 DTO를 유지하고 `409 ALREADY_VERIFIED`를 사용한다. 현재 account.owner_id가 요청회원이고 verified_at이 존재할 때만 본인 유효인증으로 본다. 과거 verified 도전 이력이나 이름 한 개만으로 소유상실/타회원 도전을 차단하지 않는다.

- 유효한 등록 start는 본인 활성등록 접근검사 뒤 현재연결/owner를 먼저 확인한다. 현재본인이면 target/version의 런타임 비교·키 조회/쿼터/외부호출 전에409다. 엄격DTO/인증·타회원/삭제등록검사 및 멱등key/body충돌 검사는 기존대로 선행한다.
- direct_input 및 연결 안 된 등록은 정상 파싱 siblings의 현재 server/name claim이 단일 비퇴역canonical account로 연결되는지 확인한다. 그 account의 현재owner/verified_at과 요청회원의 저장등록 연결(삭제된 등록 포함)이 있어야 차단한다. 미관찰 신규 이름도 같은 목록의 현재anchor로 확인할 수 있으면 Armory 전에 차단한다. 단일account 판정 불가/다른회원/anchor없음은 본인인증으로 추론하지 않고 기존 도전/보류 규칙을 따른다.
- 전송 중 소유 변화가 있어도 최종 transaction에서 다시 확인해 새 challenge/소유감사/revision 쓰기를 막는다. 이미 발급된 pending의 확인도 현재본인이면 차단한다. 기존 pending을 삭제/취소하거나 새 결과로 조작하지 않는다.
- 이미 완료된 원명령의 replay는 새 도전이 아니므로 저장ACK를 그대로 회수하고 현재GET으로 상태를 확인한다. 이미verified인도전의 confirm/GET도 유지한다. 진행중명령은 REQUEST_IN_PROGRESS, 실패후동일명령재실행은 현재소유판정을 적용한다.
- A가 B원정대소유중 C가 도전하면 정상요청의 챌린지를 발급한다. C의 장비검사가 통과해도 pending/ACCOUNT_BINDING_EVIDENCE_PENDING·A소유/ID·설정유지이며 자동이전하지 않는다. 소유를잃은A도현재owner가아니므로도전가능하다.

차단 응답은 기존 GameErrorOut의 code/message/request_id이며 새필드/성공 상태는 추가하지 않는다. Flutter는 서버ALREADY_VERIFIED를 ‘이미 인증된 원정대입니다.’로 표시하고 새 인증이나 강제key초기화를 하지 않는다. 종료된 원명령의 ACK/현재GET 회수와 차단을 혼동하지 않는다.

## 같은 회원의 삭제 후 재등록

기존 등록 POST/201 RegistrationOut을 재사용한다. 현재정상목록의 모든 기존claim이 하나의 비퇴역canonical account로 모여야 하고, 해당account의 현재owner/verified_at과 요청회원의 과거등록연결이 있어야한다. 삭제된등록은이력근거로만사용하고그행/경로/key를부활시키지않는다. 네트워크전후의회원/키·과거등록/소유/account/claim snapshot을 비교해변하면409 REVISION_CONFLICT다.

확정되면 새등록을 같은account에 연결해 verification_status=verified/ownership_status=owned로 반환한다. account/characterID·owner/verified_at/소유revision/rosterrevision·소유감사는변경하지않는다. 이전활동설정은종료상태를유지하고새설정은unconfigured/활동없음/대표null로시작한다. 같은소유수명의기존개인자료는삭제하지않는다.

다른회원/소유상실·미확인계정/복수account충돌·현재anchor없는목록·퇴역claim·회원등록연결근거없음은자동연결하지않고기존unverified등록을반환한다. 이미같은account의활성등록이있으면REGISTRATION_EXISTS다. 새등록의새이름을정상조회가포함하더라도기존다른anchor/현재claim으로단일account를확인해야한다. 모든기존주소가사라진경우이름만으로예전account를찾거나소유를추정하지않는다.

## 검증 경계

격리PostgreSQL과모의HTTP/실제collector에서본인등록·검색/newalias차단/Armory0·타회원도전/소유상실도전·pending보류·원명령replay/현재GET·기발급pending차단·등록삭제후새등록/설정초기상태/개인자료보존·소유변화경합·서버직전재검사·불명확연결거절을검증한다. 이전본인재인증허용을기대하던시험만최신정책에맞게바꾸고기존설정보존/구key세대/fencing등검사는유지한다. 자동검증과실제provider/기기상태는구분해실행결과를DEV_LOG에남긴다.

공개paths/DTO·DB구조·기존멱등정규화/8필드응답불변. OpenAPI정책설명/ALREADY_VERIFIED만보완한다. 기존8000/자료/키/flag유지·DB초기화/새환경/자료이전·실제인증POST/게임조작·소유분쟁이전/배포는하지않는다.

최종 관련격리PostgreSQL **483PASS·기존경고1·221.38초**. 앞선직접2실패/84PASS·넓은2실패/480PASS는불가능한NOT NULL fixture와대체된과거본인재인증허용기대였으며정정후최종범위전부통과했다. 실행합산없음. 기존8000개발API만반영·health/전체OpenAPI·DB0010확인. 실제기기새정책/삭제재등록실행·타회원실게임분쟁은미실행이며최초실인증성공과별도다. 게시SHA/Issue링크는결과인계·DEV_LOG에남긴다.

반영시기존개발DB가작업전부터중지돼초기health는503이었다. 기존DB컨테이너를동일볼륨으로start한뒤health/API·DB ok·DB0010·기존소유자료유지와읽기전용정책probe409를확인했다. 이는실제start요청/장비시험을대신한것이아니다.

구현/계약 `19c2dcc33630078fa0d88a1dd60e11857a44472b`·feat/representative-selection commit/push·원격일치/dev-main미통합. [105번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800)로Flutter서버ALREADY/재등록201 owned 소비·기존replay/타인도전경계확인을요청했다. 다음Flutter구간회신대기이며반복실인증/전체기능재시험요청은없다.
