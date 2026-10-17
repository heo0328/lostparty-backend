# 그룹 G2 명세·구현 구간

2026-10-17. #12 본문·최신13번째 Flutter 인계접수와 사용자 G2 구현 지시를 기준으로 한다. 기존 feat/raid-services/G1·한도기초를 이어간다. **명세 게시 후 구현·검증/기존로컬0014반영완료. [개발/검증](ISSUE_12_GROUP_G2_DEVELOPMENT.md)과실행OpenAPI를함께따른다.**

## 사용자 확정과 범위

일반 그룹원도 정확한 캐릭터명 검색으로 인증된 앱 회원을 초대한다. 신청 승인/차단·코드 관리는 현재 그룹장만 한다. 초대는 회원UUID에 귀속하고 검색 캐릭터는 식별을 확인하는 수단이다. 최종 가입은 본인이 선택한 현재 소유·usable·활동 캐릭터와 현재 정원/가입한도를 검사한다. 그룹 대표나 1700·표시수는 가입조건이 아니다.

코드는 그룹장이 활성화/그룹원 공개를 선택하며 공개된 경우 그룹원도 현재코드를 조회·복사할 수 있다. 영문대문자/숫자 6자로 생성하며 혼동문자0/O/1/I를제외한다. 재생성은10분쿨타임, 기존코드는즉시폐기한다. 폐기후새생성으로쿨타임을우회하지못한다. 코드자체는기간만료가없다. **사용자 최종 확정: 공개OFF는화면에서만숨기며기존코드가입은유효하다. 사용차단은폐기/재생성으로한다.**

G2는초대/신청·수락/승인/거절/취소·차단/해제·코드와현재membership확정이다. G3탈퇴/추방/그룹장이전/해산·모집·통계집계는포함하지않는다. 현재그룹운영은개인한도초과로일괄정지하지않으며가입증가의해당한도만검사한다.

## 경로·권한

모든경로로그인필수·no-store, GET본문/미지원query/중복scalar는400이다. 쓰기는기존UUIDv4 Idempotency-Key/원key·정규화본문복구를쓴다. 코드preview는읽기전용POST로URL에코드를넣지않으며멱등키를요구하지않는다.

| Method/path | 내용/권한 |
|---|---|
| GET /v1/groups/{group_id}/invite-candidates?character_name=정확한이름 | 현재멤버만,현재인증소유/usable/claim의저장캐릭터. provider호출없음 |
| POST /v1/groups/{group_id}/invitations | 현재멤버·검색canonical UUID/소유·lifecycle revision으로대상현재회원확인 |
| POST /v1/groups/{group_id}/applications | 본인현재활동캐릭터선택·그룹revision, 신규pending생성 |
| GET /v1/me/group-relations | view=received_invitations/sent_applications/sent_invitations, state=pending/all |
| GET /v1/groups/{group_id}/join-relations | 현재그룹장만, state=pending/all·요청현황 |
| GET /v1/group-relations/{relation_id} | 수신당사자/현재발신멤버/현재그룹장만 |
| POST /v1/group-relations/{relation_id}/accept | 초대수신자,현재본인캐릭터선택+relation/group/members/limits/usage revision |
| POST /v1/group-relations/{relation_id}/approve | 현재그룹장·가입신청,relation/group/members revision |
| POST /v1/group-relations/{relation_id}/reject | 초대수신자또는신청의현재그룹장. block_future=true는신청그룹장만 |
| POST /v1/group-relations/{relation_id}/cancel | 신청자/초대발신현재멤버·현재그룹장(초대취소),relation/group/members revision |
| GET /v1/groups/{group_id}/blocked-subjects | 현재그룹장만,그룹범위subject UUID/표시/누적신청수/차단revision |
| POST /v1/groups/{group_id}/join-subjects/{subject_id}/block 또는 /unblock | 현재그룹장·subject/group/본인membership revision. 차단은pending종료,기존membership을추방하지않음 |
| GET /v1/groups/{group_id}/join-code | 현재멤버. 현재그룹장/공개ON일반멤버만원문,나머지는null |
| POST /v1/groups/{group_id}/join-code | 현재그룹장·없는코드생성,expected_code_id(null또는직전코드ID)/revision·group/membership revision |
| POST /v1/groups/{group_id}/join-code/regenerate 또는 /revoke | 현재그룹장·동일예상값,재생성은10분검사 |
| PUT /v1/groups/{group_id}/join-code/visibility | 현재그룹장·동일예상값·visible_to_members:strict bool |
| POST /v1/group-join-codes/preview | {code} 정규화/유효성·그룹최소요약/members revision/code ID·revision. 추측방지횟수제한 |
| POST /v1/group-join-codes/join | 코드+본인캐릭터선택·group/members/code/limits/usage예상값,즉시확정 |

목록limit기본20/최대50,cursor최대2048자. 정렬created_at내림차순+UUID내림차순. cursor는path/actor/filter/limit·현재관계revision/논리만료상태에묶어변조·다른scope400,변경후409 CURSOR_STALE다. 마지막null. 일반멤버는타인의신청·차단명단/회원전역UUID를보지못한다.

## 입력·출력

CharacterSelection은 registration_id/character_id + expected_registration_version/expected_ownership_revision/expected_roster_revision/expected_lifecycle_revision이다. 그룹생성과같은strict integer>=1. 가입신청은선택과expected_group_revision,초대수락은선택과expected_relation_revision/expected_group_revision/expected_members_revision/expected_limits_revision/expected_usage_revision을받는다. 신청승인은신청당시선택과현재권위상태를재검사하며다른캐릭터로조용히대체하지않는다.

초대입력은target_character_id/expected_target_ownership_revision/expected_target_lifecycle_revision/expected_group_revision/expected_membership_revision이다. 검색결과가현재소유변경으로낡으면거부하고원래사용자와새이름/새소유자를혼동하지않는다.

Relation은relation_id/subject_id/kind/state/revision/group(공개GroupSummary)/members_revision/display/created_at/expires_at/ended_at/application_count/permissions(accept,approve,reject,cancel,block)다. target/issuer의전역user UUID·계정UUID/키·개인설정은없다. 상태는pending/accepted/rejected/cancelled/expired/blocked/joined_by_code다. 시간은UTC RFC3339,nullable필드는명시적으로null이다. permissions는현재역할과논리상태의행위자허용안내이며정원/최종선택검사를대체하지않는다.

코드응답은code_id|null/revision/active/visible_to_members/code|null/created_at|null/regenerate_available_at|null이다. 없는코드는revision1·activefalse·code_id/code/times null. 폐기후마지막코드ID/revision/시각은재생성CAS·쿨타임안내용이며원문은null이다. preview는공개GroupSummary+members_revision/code_id/code_revision만준다. 초대수락/코드가입성공은G1 GroupDetail이며신청승인은accepted상태의Relation이다. 승인자에게타회원의my_membership을노출하지않고본인그룹GET/멤버목록으로현재상태를확인한다.

## 관계·원자성·이력

- 초대/신청은DB 생성시각부터24시간. 정확히expires_at부터만료다. GET은쓰지않고논리만료를계산한다. 새요청을만들때과거expired/pending을동일transaction에서종료한다. 발신membership종료초대도논리cancelled이며G3종료명령에서같은원칙으로정리한다.
- 같은group+appuser 활성관계1개. 초대/신청충돌은409 GROUP_RELATION_EXISTS로기존요청GET/목록으로안내하고새관계/누적수증가는없다. 신청거절/만료후재신청대기없음. 재신청은새relation UUID·누적신청수+1이다. 코드가입/초대는신청수를늘리지않는다.
- 그룹범위subject는표시·누적수·차단revision을보존한다. 차단된앱사용자는부계정/다른캐릭터/코드/그룹장직접초대로우회하지못한다. 해제는과거pending을살리지않는다.
- pending은자리예약이아니다. 최종수락/승인/코드가입은현재actor역할·대상앱회원활성·등록/소유/claim/lifecycle/활동·그룹정원/개인가입수·버전을같은변경락/transaction에서검사한다. 정원부족등실패는pending을보존한다. expiry/code·쿨타임은최종DB 시각도검사하고경계넘으면전체rollback한다.
- membership확정+그룹members revision+directory/사용량head+pending종료+성공ACK는원자commit이다. 후속재가입을위해기존전체이력unique를현재membership부분unique로바꾸고새membership UUID를생성한다. 종료membership/시각/표시를덮지않는다. 기존자료삭제나이관은없다.
- 코드원문은DB평문/멱등result/로그/URL에남기지않고HMAC검색digest·암호화원문을보존한다. 현재권한이있는조회만복호화한다. 생성/재생성ACK도DB에는메타데이터만저장하고원문은현재권한으로복호화해복구한다. 폐기/재생성후원코드의신규가입은거절하되완료ACK는현재membership확인후과거성공반환이며새가입을하지않는다.

## 오류·검증

기존error envelope/no-store/401 Bearer·멱등lease/generation/409 Retry-After2를재사용한다. 400 INVALID_REQUEST,403 GROUP_JOIN_BLOCKED/GROUP_LEADER_REQUIRED/GROUP_MEMBERSHIP_REQUIRED/GROUP_RELATION_FORBIDDEN,404 GROUP_RELATION_NOT_FOUND/GROUP_JOIN_SUBJECT_NOT_FOUND/GROUP_TARGET_UNAVAILABLE/GROUP_JOIN_CODE_INVALID,409 GROUP_RELATION_EXISTS/RELATION_NOT_PENDING/ALREADY_GROUP_MEMBER/GROUP_CAPACITY_REACHED/GROUP_MEMBERSHIP_LIMIT_REACHED/REVISION_CONFLICT/POLICY_CONTEXT_CHANGED/GROUP_CODE_ALREADY_ACTIVE/GROUP_CODE_REGENERATION_COOLDOWN,503 GROUP_CODE_UNAVAILABLE/SERVICE_UNAVAILABLE 등으로연결한다. 코드재생성가능시각은현재권한의code GET에서조회한다. 한도/차단원문을에러에추가하지않는다.

격리PostgreSQL에서권한위조/부계정중복·만료경계/발신자탈퇴·신청누적/차단우회·마지막자리/동시승인·code재생성/공개/폐기·원문보관·rollback/replay/현재권한·cursor/GET쓰기0·기존G1/L0/주간회귀를검증한다. 실제앱연결/실기기·운영완료와구분해구현SHA/push/로컬적용/미확인항목을회신한다.

사용자후속답변으로코드공개OFF의사용여부확인도해소됐다. 초대권한/코드조회·공개/10분쿨타임에추가제품결정대기는없다.


## 최종 입력·응답 예시

신청입력(가상UUID/버전):
```json
{"registration_id":"00000000-0000-4000-8000-000000000001","character_id":"00000000-0000-4000-8000-000000000002","expected_registration_version":1,"expected_ownership_revision":1,"expected_roster_revision":1,"expected_lifecycle_revision":1,"expected_group_revision":1}
```
신청승인/취소는 `{"expected_relation_revision":1,"expected_group_revision":1,"expected_members_revision":1}`. 거절은동일본문과선택strict bool `block_future`(기본false)다. 초대수락은이3개와CharacterSelection·expected_limits_revision/expected_usage_revision을모두필수로받는다. 신청승인은신청당시의선택/버전을검사하고사용자가다시고르지않은다른캐릭터로바꾸지않는다.

코드없는상태의현재코드GET예시:
```json
{"code_id":null,"revision":1,"active":false,"visible_to_members":false,"code":null,"created_at":null,"regenerate_available_at":null}
```
코드생성요청은 `{"expected_group_revision":1,"expected_membership_revision":1,"expected_code_id":null,"expected_code_revision":1,"visible_to_members":false}`. 코드응답의code는권한있을때만생성된6자리문자열이며비공개일반멤버/폐기상태에는null이다. 생성은201,나머지코드명령은200이다. 재생성은같은예상ID/revision·group/membership버전으로직전공개설정을보존하며새ID/문자열을생성한다. 재생성/폐기/visibility명령·생성완료ACK복구는현재그룹장권한을요구한다.

개별Relation의created_at/expires_at/ended_at는UTC이고만료전pending은ended_at=null이다. 논리만료시ended_at=expires_at,탈퇴한발신자의논리cancelled는아직물리종료전이면null일수있다. GET은해당종료를쓰기/갱신하지않는다. permissions는현재역할/관계행위허용이며최종정원/활동/계정변경을미리허가하지않는다.

코드입력은trim·대문자화후6자리문자집합검사,실제생성은영문/숫자를각각최소1개포함한다. provider/키호출없음. 코드preview/join은인증회원20회/분·직접접속host60회/분제한(현단일프로세스auth limiter재사용),검색은회원30회/분으로저장자료추측을제한한다. 429 RATE_LIMITED/Retry-After60이다. 서버가프록시헤더IP를신뢰하지않으며다중프로세스운영전제한기저장소공유는운영후속이다.

물리구조: group_join_subjects/relations/codes3테이블과group_memberships의현재행부분unique. subject/relation/초대발신membership의같은그룹복합FK·요청종류/선택제약을둔다. 원문은별도목적키로HMAC검색/AES-GCM보관하고과거key_id/이력을유지해원ACK복구를지원한다. 요청본문의rawcode대신해결된code UUID를멱등digest에넣어코드평문/사전추측본문을result에남기지않는다.
