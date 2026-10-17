# LostParty Backend 프로젝트 지도

기준일 2026-10-17. 다음 실행은 [NEXT_WORK](NEXT_WORK.md), 완료·검증·장애·Git 이력은 [DEV_LOG](DEV_LOG.md)가 기준이다. 아래는 현재 기능 상태와 기준 링크이며 과거 구현 문서의 당시 미완료/브랜치 상태와 구분한다.

## 기준 상태

현재 Backend #8 작업 구간은 [PR #9](https://github.com/heo0328/lostparty-backend/pull/9)/병합ea1384d로 dev에 통합했다. 최종 문서 기록을 포함해 main/dev는 같은 HEAD로 동기화하며 완료 작업 브랜치는 로컬·원격 삭제했다. [110번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228957999)과 DEV_LOG가 최종 SHA/정리 기준이다. 당시 #8 구현/계약 `19c2dcc`는 기존 로컬 Docker/포트8000·DB0010에 반영됐고 관련 격리483PASS/전체OpenAPI 일치를 확인했다. 해당 통합은 코드·실행환경/자료·키/flag를 변경하지 않았다. 현재 레이드 작업은 feat/raid-services에서 이어가며 로컬API의 #10/#11과 신규 주간테이블0011을 반영했다. 기존 자료/키/flag는 유지한다.

| 영역 | 현재 상태·기준 |
|---|---|
| 실행·협업 | Python3.12/FastAPI/PostgreSQL17/Docker Compose. [README](../../README.md), [개발 흐름](../DEVELOPMENT_WORKFLOW.md), [API 협업](../API_COLLABORATION.md). 공식 채널은 [Backend Issues](https://github.com/heo0328/lostparty-backend/issues), Flutter 로컬 소스 접근/수정 없음 |
| API 원본 | [openapi/openapi.yaml](../../openapi/openapi.yaml). app.openapi()와 전체 비교. 공개paths/DTO·정책/오류를 함께 검토 |
| Google 인증·세션 #2 | 6 API·세션/복구 구현·초기범위 완료. [인증 개발](../AUTH_DEVELOPMENT.md), [후속 AUTH-F01~F06](../ISSUE_2_FOLLOWUP.md). 탈퇴/약관·전체release/운영 인수는 별도 |
| 원정대 등록·복원 #3/#4 | 로그인 회원의 서버 등록/목록·개인키·명령복구 연결 완료, 등록/이름/메인/삭제/중복/version 정책 유지. [계정 API](../ISSUE_3_DEVELOPMENT.md), [등록 연동](../ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md) |
| 전투력·기본 권한 #5/#8 | 캐시/POST 갱신 구현. 미인증·소유상실 상세/power 차단/기존수치 비노출, 원본 자료는 보존. [전투력](../ISSUE_5_DEVELOPMENT.md), [기본 접근](../ISSUE_8_BASIC_ACCESS_DEVELOPMENT.md) |
| 회원 설정 #6·개인키 #7 | 서버 설정/회원별 암호화 키·개인 호출/복원·키version fencing 완료, #1~#7 CLOSED. [회원 설정](../ISSUE_6_MEMBER_SETTINGS.md), [개인키](../ISSUE_7_DEVELOPMENT.md) |
| 생명주기·현재/이력 #8 | UUID/NameClaim/의심·사용차단/V2 현재/퇴역이력·내부정리 구현. live 누락은suspect이며 자동퇴역/claim해제는 비활성. [L1 개발](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md) |
| 대표·활동 #8 | 대표전용 GET/PUT·cooldown제거·기존관리의 명시 전체저장/대표선정, 최신115번째는1700을최초기본선택만적용·수동활동/대표하한해제로정정. 수동자격레벨검사제거·활동20/회귀244PASS·d33f873 push/8000반영/실행계약일치완료·[119번째 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230483893)·[구간설계](../ISSUE_8_MANUAL_ACTIVITY_POLICY_PLAN.md)/[118번째 설계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230431817)·[117번째 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230374459). 부적격보고/선택보존. [대표 계약](../ISSUE_8_REPRESENTATIVE_CONTRACT_DRAFT.md), [활동](../ISSUE_8_ACTIVITY_SELECTION_DEVELOPMENT.md) |
| 역할·개인설정/표시 P1/P2 | 서버 역할요약/개인설정/원정대표시 복원·소유수명/version/명령격리. [역할](../ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md), [개인표시](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md) |
| 본인 원정대 목록 갱신 #8 | 현재소유등록의 정상API목록 기준 추가/누락·현재비퇴역claim 재등장,404조회기준최대3개 대체·실패시소유보존. GET은DB만조회. [구현](../ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md) |
| 장비 소유 인증 #8 | 서버siblings/Armory·6부위/1~3해제·10분/대상·시각/최종만료rollback·실행이력·진단·4장비분류호환. [장비](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [이력](../ISSUE_8_VERIFICATION_HISTORY_DEVELOPMENT.md), [대상/원명령](../ISSUE_8_VERIFICATION_TARGET_DEVELOPMENT.md) |
| 현재 소유자/재등록 #8 | 본인유효소유 start/pending confirm은409 ALREADY_VERIFIED,타회원/소유상실도전·완료replay유지. 같은회원 삭제후등록POST201 owned 재연결·소유/ID/감사유지·활동/대표자동복원없음. [현재정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md), [105번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800) |
| 실제 확인 | [98번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217275533) 사용자실제1회인증/서버verified·현재소유·감사1개일치. [108번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228832537) 새기기동일회원목록/인증상태·표시정상보고. 전체캐릭터/활동/자동상세·분쟁인수와구분 |
| Flutter 완료·후속 | #8 123번째/#11 여섯번째 최신1628PASS/분석0·활동우선/max3병렬profile복원·역할/이름/주간표시복구보고. #11네번째는사용자실제manual true반영성공, 정정/다른기기/수정UI·실측속도는별도. 새변경은feature/scoped-account-cache 기준5eef0d2 미커밋/미push/dev미반영 |
| 신규 분야별 요청 | [114번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229923232): #10 카탈로그/주차 P0 → #11 주간·#12 그룹 기초 P1 → #13 모집/파티 P2. 본문 검토 완료. #10은feat/raid-services의d7f762f로push완료·공개카탈로그/주차GET 구현·31PASS/실행OpenAPI 일치/로컬HTTP 확인. [두 번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6230019531), Flutter연결보고는위행·실기기대기. #11 첫 구간은 아래 행, #12 G1 내부기초는아래행·HTTP미연결, #13 명세/구현미착수. [#10 안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md). 상세 다음 실행은NEXT_WORK 참조 |
| 주간 원장 #11 | 본인 최대50캐릭터 배치GET/현재주차 manual 완료·정정PUT과 난이도 공유권리/분리근거·점유 가드 구현. [첫 계약](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230283275), [개발 안내](../ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md). 주간51+카탈로그31+모델/migration1=83PASS·실행OpenAPI 일치·로컬0011/health/비인증401 확인. 구현/계약bce6133 push·[두 번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230329942) 완료. Flutter개인체크연결은위행·실기기대기. 점유 중 영향확인/명시실행·실제파티연결은 후속 |
| 그룹 G1 #12 | [첫 명세](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232074318)·[G1 안내](../ISSUE_12_GROUP_G1_SPEC.md)·[내부기초](../ISSUE_12_GROUP_G1_FOUNDATION.md). 그룹/회원/디렉터리3모델·0012파일·내부생성/회원조회/이름수정과권한/CAS/멱등/원자성구현·관련118PASS. HTTP/router/OpenAPI연결없음·전체기존계약불변. 조건은필수정책주입으로분리. 최신활동선택필수·그룹/대표이름검색과계정별기본정원15/가입5/모집10·초과상태/회복공통계약은설계반영·구현전. e5e97c8 push·[두 번째 Backend 내부구현 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232311355)완료. 0012격리검증만·개발DB0011유지, G2/G3후속 |
| 신규 정책/조사 | [#8 124번째Backend](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6232557892): 기존로그GET139회200이나duration없어요청별지연분리불가. #8 122번째신규/첫1700자동추가·수동제외영속계약미설계. [#12 여섯번째Backend](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232576104): 계정별한도/초과방제한·회복명세는 [#12일곱번째](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232669446)·[계약안](../ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)게시/검토·구현전. #13 i/현재방관계는점유/완료와분리·개인완료기존API유지 |
| 남은 별도 기능 | 타회원소유이전/분쟁·24시간방어/통지·자동소멸확정/퇴역·프로세스종료후미확정명령영속복구는 미완료/보류. 모집/파티/그룹은 신규 #10~#13 요청으로 분리하며 아직 미구현. Apple/Discord·WebSocket은 별도 |
| 자료·운영 | 현재개발자료/키유지·베타직전초기화는별도사용자지시. 새8001 채택/기초재인수·Firebase이관/삭제·이름기반자료병합없음. Lightsail 운영배포는예정/별도범위 |

상세 합의는 Issue #8의 최신댓글과 현재정책 문서가 우선이다. 과거90번째의본인재인증허용은102번째정책과19c2dcc 구현으로 대체됐다. 완료 구간의 통합과 실제환경/운영 전체인수를 혼동하지 않으며 현재 레이드 후속은feat/raid-services에서 진행한다.


## 최신 공통기초/통계 구간

[#12 아홉 번째](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572)로 제한 영향범위 확정/질문 해소. 개인초과는 직접 참가방에만 차원별 적용하고 기존그룹운영은유지, 그룹자체정원초과만 해당그룹 모든그룹전용방 제한이다. 위 과거 광범위상속/검토대기 설명을 대체한다. [L0 내부기초](../ISSUE_12_MEMBER_LIMITS_FOUNDATION.md)는 한도/사용량head/감사·기본읽기·그룹집계·G1생성head원자갱신 구현, 관련137PASS. HTTP/실제방제한 미연결,0013격리검증만·개발DB0011유지. 다음은G1 HTTP/정책연결이다. [#13 일곱 번째 통계요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는 [별도 선행 설계](../ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)이며 구현/실기기 완료와 구분한다.

구현/문서fcbb840 작업브랜치push·원격확인, [#12 11번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232977320)·[#13 8번째 Backend 통계제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232977464). Backend다음G1작업가능/Flutter통계검토, 개발DB0011·HTTP기존유지.
