> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [ownership](../../../../features/rosters/ownership/README.md) · [registration](../../../../features/rosters/registration/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #8 — 기존 원정대 재인증·갱신·이전 연결 검토

> **후속 구현:** [본인 원정대 목록 갱신](ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md)은76번째API목록기준으로기존POST의소유범위반영/현재claim의비퇴역suspect복구·404대체조회와실패/인증보존을구현했다. 아래refresh차단/대체조회미구현은당시상태다. 본인장비재인증/타소유pending도전은별도후속이다.

> **최신 확정:** [76번째 Flutter 사용자 정책 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6212824900)로 아래73번째 당시의 한계수용 답변 대기는 해소됐다. 원정대 구성은 로스트아크 API목록 기준이며 API에없는 영구ID/생성세대 증거를 본인갱신/해당등록재인증의 추가필수조건으로 요구하지 않는다. 인증대상C가 사라져도 B원정대인증/owner는 유지한다. [77번째 자동실행 실제 누락](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6212848615)으로 Backend refresh 제공 → Flutter 자동 상세검사 앞 목록갱신 연결이 다음순서다. [78번째 Backend 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213197093)에 회신했다. 아래 미결정 설명은 당시 검토 이력이며 현재 대기 사유가 아니다.

## 현재 다음 작업

1. Backend: 본인 등록/account/owner/revision 범위의 실제 siblings refresh를 제공한다. 정상 목록 기준 현재active 기록 유지·새이름 신규UUID/빈자료·누락 이상처리, 실패/부분/형식오류/429/기준404의 자료·인증보존, 같은원정대 대체 조회기준 복구/미확인 경계를 구현·인계한다. suspect해소/종료ID/퇴역·claim정리는 최신정책과 대조해 실제지원범위를 구분하고 소멸용 근거를 일상갱신 전체에 요구하지 않는다.
2. Flutter: 게시된 refresh를 환경/회원별1회 준비의 상세/빌드 검사 앞에 연결한다. provider목록갱신→최신revision/canonical재조회→유효활동집합→상세검사 순서다. 나이스단OFF도 목록갱신은 수행한다. 실패준비 미소진·동일실행 멱등/명시재시도·회원전환 late차단을 유지한다. 현재GET만 읽는 경로는 이 단계를 완료한 것이 아니다.
3. Backend 독립 후속: 해당등록 범위 본인 장비 재인증 및 타소유 start201/pending·장비확인후미연결pending/이력·소유불변을 구현한다. 24시간수동분쟁/자동이전·통지는별도다.

현재 코드의refresh는siblings호출은있지만owned reconcile의binding필수검사로실제canonical반영은불가하다. lookup_name실패가owner를지우지는않으나대체조회복구도미구현이다. 이번정책수신/검토로이를구현완료로표시하지않는다. 새사용자결정/Flutter추가자료를전체선행으로다시기다리지않는다.

2026-10-16. [72번째 장비 인증 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211928415) 후 사용자 진행 지시에 따른 계약 검토다. 신규 장비 인증 `13d9f68`/현재 `489c8b6`과 최신 Issue 본문·댓글72개를 대조했다. 신규 인증·기존 앱/로그인/등록/설정 등 완료 결과와 현재8000/DB0010/자료는 유지한다.

## 확인한 원인

서버에는 `Registration.user_id/account_id`와 `Account.owner_id`로 본인 원정대를 식별하는 내부 관계가 이미 있다. 새 원정대 연결 관계가 없어서 처음부터 다시 등록해야 하는 문제가 아니다.

현재 `canonical_candidate`는 이름 claim이 있는 모든 live start를 `ACCOUNT_BINDING_EVIDENCE_PENDING`으로 거절한다. 저장된 관계가 본인 owned인지도 이 함수의 대체 근거가 되지 않는다. `reconcile`도 기존 account에는 BindingEvidence를 필수로 요구한다. live fetch는 장비 제어 수집 근거만 발급하고 binding은 발급하지 않으므로 본인 재인증·owned roster refresh가 모두 차단된다. 이는 Flutter 화면 미연결이나 사용자 키/게임 테스트 부재와 구별되는 서버 정책/연결 공백이다.

다만 `owner_id`는 앱의 저장된 권한 관계이며 현재 조회 이름이 과거와 같은 캐릭터 세대라는 공급자 증거는 아니다. 소유권 검사와 관찰 내용의 적용은 분리해서 설계해야 한다. 내부 snapshot digest는 경합/변경 검사용이며 외부 동일성 증거가 아니다.

## 기존 합의와 충돌하지 않는 경계

Issue 본문은 개명 b를 신규 UUID/빈 개인 빌드로 추가하고 a→b 자동 승계 금지, 다른 원정대 이름 재사용에 과거 ID/권한 이전 금지, suspect의 단순 재등장 복구 금지, 조회 실패/부분 응답으로 소멸 확정 금지를 요구한다. 기존 provider 검토도 안정적인 원정대/캐릭터 생성세대 식별자를 확보하지 못했으며 제한을 수용한 새 정책 없이는 동일ID 복구/소멸정리를 활성화하지 않도록 정리했다. 이번 코드/기존 자료 검토를 새 공급자 보장 확보로 보고하지 않는다.

관찰 사이에 캐릭터가 삭제되고 같은 서버/이름으로 재생성되면 현재 수집 필드로 구분하지 못할 수 있다. 모든 active ID를 이름만으로 유지하는 정책은 이 한계를 수용하는 제품 선택이다. 본인 회원/등록 UUID를 아는 것만으로 이 한계가 해소됐다고 주장하지 않는다.

## 최소 연결안 — 검토 제안, 미구현

| 구간 | 제안 / 서버 검사 | 보존·보류 |
|---|---|---|
| 본인 owned의 일상 갱신 | 명시 registration_id의 내부 account/owner/revision으로 적용 범위를 고정. 정상 관찰에서 대상 주소가 해당 account의 현재 active/confirmed claim이고 타 account claim이 섞이지 않았는지 확인 | owner/ID를 새로 추론하거나 타계정에 연결하지 않음. 현재 active ID의 주소 유지 적용에는 아래 관찰 한계 수용 필요 |
| 캐릭터 추가/누락 | 위 원정대 연결 조건을 통과한 긍정 관찰의 미점유 새 이름만 신규 UUID/빈 개인설정으로 추가. 기존 누락은 suspect로 신규 사용 차단 | 개명 매칭/빌드 승계·대표/활동 자동 선택·퇴역/claim해제 없음. 실패/형식오류는 적용0 |
| suspect 재등장/조회 기준 소실 | 기존 주소만 다시 나타났다고 같은 UUID를 usable로 복구하지 않음. 기준 이름404/전체 기준 소실은 원정대 전체 삭제로 보지 않음 | 이번 일상 갱신 허용을 복구/소멸 확정으로 확대하지 않음 |
| 본인 재인증 | 서버 내부에 연결된 같은 본인 원정대를 대상으로 새 장비 challenge. start/confirm의 회원/키/등록/account/claim snapshot과 장비 기준 검증 | 소유권 이전 없음. 본인임을 재확인해도 suspect 복구·세대 승계는 별도. 이름 claim만으로 새로운 canonical 후보를 선택하지 않음 |
| 타소유 원정대 도전 | 장비 제어 검증을 소유 이전과 분리. 도전 허용 시 unresolved 상태로 challenge/관찰 소유관계를 고정하고 최종 연결은 기존 pending으로 남기는 안 검토 | owner_id/기존캐릭터/활동/claim을 건드리지 않음. 신규 verified로 위장하지 않음. 기존 24시간 운영자 수동 방어/이전은 별도 계약 |

일상 갱신 구현에는 전체성/소멸 증거를 일괄 요구하지 않는다. 다만 현재 active 주소의 계속 사용을 관찰 정책으로 허용하는지는 확정해야 한다. BindingEvidence를 이름으로 생성해 기존 강한 의미를 약화하는 방식 대신, 승인된다면 **현재 owned 등록의 관찰 적용**을 별도 내부 경로로 표현하고 기존 세대복구/이전 증거 검사는 유지한다.

## 필요한 계약 대조

1. **본인 owned 일상 갱신의 관찰 정책 수용 여부.** 위 내부 소유관계/active 기준/충돌 검사하에 기존 active ID 유지·새 이름 신규 ID·누락 suspect까지만 허용하며, 관찰 사이 같은 이름 삭제·재생성은 식별 불가라는 한계를 명시한다. 이전 합의가 이 범위를 이미 수용했는지 근거가 있으면 확인하고, 미수용이면 검토 답변으로 임의 승인하지 말고 필요한 사용자 결정 항목으로 구분한다.
2. **타소유 도전 시작과 이전의 분리.** 현재는 start409라 장비 확인까지 갈 수 없다. 제안은 기존 start201/pending으로 도전은 기록하고, 장비 일치 후에도 account binding이 없으면 confirm200/pending+ACCOUNT_BINDING_EVIDENCE_PENDING으로 남기는 것이다. 새 DTO/enum은 필요 없지만 HTTP 진행 방식이 바뀌므로 기존 화면 의미를 대조한다. 도전 이력 보관만으로 24시간 자동 이전을 승인하지 않는다.

이 검토 요청은 기존 Flutter 구현을 다시 조사하거나 재작성하라는 뜻이 아니다. 새 API·ID 정책/분쟁 시스템을 임의 확정하지 않는다. 확정 전에는 현재 보류를 유지하고 코드/OpenAPI 동작을 바꾸지 않는다.

## 합의 후 구현·검증 순서

1. 승인된 본인 관찰 적용 경로와 start/confirm의 재인증 대상을 분리 구현. 허용/보류 규칙을 원본 OpenAPI 정책에 반영한다.
2. 본인/타인·등록삭제/소유변경·키변경·늦은응답/중복·서로 다른 원정대 동일이름의 양쪽 순서/경합·추가/누락/실패·suspect재등장 복구0·활동/대표 자동변경0을 격리 PostgreSQL에서 검증한다.
3. 해당 작업 구간 commit/push·원격 확인 후 Flutter 계약 소비를 인계하고 현재8000 API에 반영한다. 실제 게임 관찰은 사용자 결정대로 나중이며 기존 정상 로그인 전체 시험을 반복하지 않는다.

현재 결과는 설계/계약 검토다. 새 기능 구현/검증/운영 완료가 아니다. 문서만 갱신하므로 자동시험/서버 재실행·DB 변경을 하지 않는다.

[73번째 Backend 검토/계약 대조 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6212414683)을 게시하고 순번을 전체 조회로 확인했다. 다음 Flutter 대조 회신 후 Backend 합의 범위 구현이다.

## 79번째 핵심 데이터 정의 보충

[79번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213474915)·[80번째 Backend 대조](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213521483): 회원은복수실제게임원정대를등록/인증하고API전체소속/회원귀속·인증/활동선택/표시를분리한다. 서버최소요약/설정저장으로반복호출을줄이며현재목록GET은provider호출없이DB조회만수행한다. 기존복수등록제약과조회경계를유지하고refresh만합의시점에연결한다. 78번째구현순서/나이스단OFF목록갱신·인증대상소실시원정대인증유지불변. 추가승인/제품질문없음·새코드미구현이다.
