# Issue #8 — 인증 대상 선택·본인 재인증·타소유 도전

2026-10-16. [86번째 계약 합의](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6215477051)·[87번째 Flutter 복구UX 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6215781843)·[88번째 Backend 확인](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6215857575) 후 사용자 진행 지시에 따른 구현이다. [착수](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6216006619)에 범위/호환성을 공유했다.

## 요청 계약

기존 `POST /v1/me/game-account-verifications`와 UUIDv4 Idempotency-Key를 사용한다. 등록 원정대의 선택 시작은 아래 형태다.

```json
{
  "source": "registration",
  "registration_id": "00000000-0000-4000-8000-000000000001",
  "target_character": {
    "server_name": "sample-server",
    "character_name": "sample-character"
  },
  "expected_registration_version": 1
}
```

- target의 두 이름은 엄격 문자열·앞뒤공백정리·1~64자다. version은 boolean/float를 허용하지 않는 엄격 정수1이상이다. nested target의 추가 필드는 거절한다.
- 새target/version은 둘 다 지정해야 하며 명시null·하나만 지정은400이다. direct_input에는 이 두 필드를 null로도 보내지 않는다. 기존 direct_input/source+character_name과 registration_id-only 경로는 유지한다.
- UI는 최신 등록 version/해당 전체 목록에서 서버+이름을 선택한다. preview UUID는 요구하지 않는다. 현재 본인 owned 등록은 canonical 비퇴역/현재claim, 그 외 본인 등록은 저장 preview 주소 범위를 검사한다. 활동/대표·visible/count·1700으로 후보를 줄이지 않는다.
- 선택 대상은 fresh siblings/Armory의 실제 서버/이름과 일치해야 한다. 등록version/회원·키·현재소유/claim·목록 문맥을 검사하고 시작~확인10분/장비6부위·무작위1~3해제/비요청장비유지를 검증한다. 단순선택/start로 소유·활동/대표·운영 lookup을 바꾸지 않는다.
- 구형 요청에는 새optional 기본null을 정규화body에 넣지 않는다. 기존 source/registration_id/character_name의 null 포함 형태를 그대로 유지해 이미 저장된 구형멱등digest와 유실동일명령재시도를 보존한다. 새 target/version 변경은 body 변경이므로 같은key로 전송하면멱등충돌이다.

## 응답과 소유 처리

VerificationOut은 기존8필드 `challenge_id/status/required_slots/expires_at/remaining_seconds/result_code/result_reference/registration_id`를 유지한다. 대상요약/선택단계는 Flutter의 불변 원명령 문맥을 사용하며 응답에 새필드를 추가하지 않는다.

| 시작 범위 | 장비 검증 후 결과 |
|---|---|
| 이름claim충돌없는신규 | 기존 account/등록/canonical캐릭터/감사 생성·verified. 등록선택경로면 지정 registration_id를 유지하며 새등록으로 우회하지 않음 |
| 명시 registration의현재본인owned | 같은account/owner/ownershiprevision·캐릭터ID 유지하며재인증·verified_at/등록/roster갱신·새감사기록. 정상API목록적용은본인refresh정책을사용. 기존활동/대표는보존·필요시needs_reconfiguration·운영lookup자동변경없음 |
| 타소유/연결미확정claim | start201/pending으로장비도전발급. 장비제어확인을통과해도confirm200/pending+ACCOUNT_BINDING_EVIDENCE_PENDING. 요청/관찰소유관계·장비제어확인시각/결과를기록하고owner/기존ID/등록연결·활동/claim은쓰지않음 |

claim/해당account snapshot은 시작과 확인 사이 재검사한다. 시작 후 다른소유/claim/원정대revision이 바뀌면 충돌로 거절한다. 한 번 미연결pending으로 시작한도전을 GET/같은명령replay로 소유성공으로 승격하지 않는다. 향후 연결승인/분쟁시스템·24시간방어/자동이전은 별도이며 이번에 만들지 않는다. 기존 trusted BindingEvidence 격리시험경로는 유지하지만 실제provider는 이이전근거를발급하지 않는다.

미연결pending의 GET도 기존 result_code 필드에 보류사유를 유지한다. 취소/만료 후에는 pending code를 현재판정처럼 표시하지 않는다. 성공뿐아니라 미연결장비제어확정도 최종 DB flush 뒤 기한을 재검사하고 만료면 savepoint전체rollback·expired/실행이력만 반영한다. 정상목록API기준·기존인증대상소실시원정대인증유지와실제장비제어확인은별개다.

## 거절·복구

| HTTP/code | 조건·경계 |
|---|---|
| 400 INVALID_REQUEST | source/필드배타·이름/버전형식·target/version짝·명시null/추가필드위반 |
| 404 REGISTRATION_NOT_FOUND | 본인등록아님/삭제/없음 |
| 404 CHARACTER_NOT_FOUND | 선택주소가해당저장목록범위에없음 |
| 409 REVISION_CONFLICT | 기대등록version불일치·조회중/확인전등록·소유/account/claim문맥변화 |
| 409 IDENTITY_CONFLICT | 선택주소와fresh서버/이름불일치·본인등록에다른account claim혼입/현재claim불일치 |
| 400 EQUIPMENT_INCOMPLETE | 시작시6부위착용미완료 |
| 기존키/503/429오류 | 외부/형식/키/호출제한등. 실패를성공·소유이전으로처리하지않음 |
| 200 pending+ACCOUNT_BINDING_EVIDENCE_PENDING | 장비확인은통과했으나소유연결은확정하지않은정상보류. HTTP실패/소유성공과구분 |

ID없는시작응답유실은같은POST/key/정규화body재시도로저장201/challenge_id를회수한다. 완료replay는새provider호출/도전생성0, 진행중은REQUEST_IN_PROGRESS/Retry-After, retryable/lease만료는같은명령generation fencing이다. ID회수뒤현재GET으로실제상태/남은시간을확인하고replay원응답의remaining을현재시간으로보지않는다. ACK후GET실패는GET만재시도한다. 단순네트워크실패로새key/다른대상을만들거나재시작으로우회하지않는다. 명확한거절과처리불확실을구분해기존복구UX를사용한다.

별도key결과조회/최근challenge목록endpoint·새journal/DB는추가하지않는다. 앱종료로key/body가소실된영속복구는미제공이다. 최초실기기연결실패의서버원인은code/request_id근거없이이번계약공백으로단정하지않는다.

## 검증·인계

실제수집기/transport parser+모의HTTP와격리PostgreSQL에서선택/저장등록범위·낮은레벨후보·본인재인증/활동보존·타소유장비확인/보류/GET·형식/소속/버전/장비거절·구형digest/유실replay·새선택같은key거절·타회원등록차단·조회중version/claim/최종만료경합을검증한다. 이전의타소유start409시험은새합의의start201/pending에맞춰바꾸며소유변경0/감사권한불변검증은유지한다.

StartIn/VerificationTarget만요청schema를보완하고공개paths/기존응답schema/DB구조는유지한다. OpenAPI정책설명은본인재인증과미연결pending에맞춰갱신한다. 기존8000API/DB0010·현재자료/키/flag를유지한다. 실제게임/provider/기기인수는사용자결정대로나중이며Flutter picker는검증코드/고정SHA게시후상대측이연결한다. 실행수/실패/실행반영/게시상태는DEV_LOG와결과댓글을따른다.

최종 격리 PostgreSQL **449PASS·기존경고1·194.55초**, 첫 직접130PASS/61.41초와합산하지않으며실패없음. 활동보존/목록수치변경·조회중등록변화·pending소유관계변화·보류증거최종만료를추가검증했다. 기존8000API반영·실행전체OpenAPI/새StartIn/응답8필드/health·DB0010유지확인·test-db만중지했다. 실제provider/게임/기기와Flutter picker는미확인/미연결이다.

구현/계약cc372bfa77edb102450cd9addbfe29ea3b0375d0·feat/representative-selection push/원격일치·dev/main미통합. [90번째Backend결과/Flutter picker인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6216253151). 다음 담당Flutter선택입력/새계약·오류/기존복구UX연결이다.
