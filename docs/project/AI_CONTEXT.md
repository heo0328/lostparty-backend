# LostParty Backend 프로젝트 지도

기준일 2026-10-17. 다음 실행은 [NEXT_WORK](NEXT_WORK.md), 완료·검증·장애·Git 이력은 [DEV_LOG](DEV_LOG.md)가 기준이다. 아래는 현재 기능 상태와 기준 링크이며 과거 구현 문서의 당시 미완료/브랜치 상태와 구분한다.

## 기준 상태

현재 Backend #8 작업 구간은 [PR #9](https://github.com/heo0328/lostparty-backend/pull/9)/병합ea1384d로 dev에 통합했다. 최종 문서 기록을 포함해 main/dev는 같은 HEAD로 동기화하며 완료 작업 브랜치는 로컬·원격 삭제했다. [110번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228957999)과 DEV_LOG가 최종 SHA/정리 기준이다. 최신 구현/계약 `19c2dcc`는 기존 로컬 Docker/포트8000·DB0010에 반영됐고 관련 격리483PASS/전체OpenAPI 일치를 확인했다. 이번 통합은 코드·실행환경/자료·키/flag를 변경하지 않는다.

| 영역 | 현재 상태·기준 |
|---|---|
| 실행·협업 | Python3.12/FastAPI/PostgreSQL17/Docker Compose. [README](../../README.md), [개발 흐름](../DEVELOPMENT_WORKFLOW.md), [API 협업](../API_COLLABORATION.md). 공식 채널은 [Backend Issues](https://github.com/heo0328/lostparty-backend/issues), Flutter 로컬 소스 접근/수정 없음 |
| API 원본 | [openapi/openapi.yaml](../../openapi/openapi.yaml). app.openapi()와 전체 비교. 공개paths/DTO·정책/오류를 함께 검토 |
| Google 인증·세션 #2 | 6 API·세션/복구 구현·초기범위 완료. [인증 개발](../AUTH_DEVELOPMENT.md), [후속 AUTH-F01~F06](../ISSUE_2_FOLLOWUP.md). 탈퇴/약관·전체release/운영 인수는 별도 |
| 원정대 등록·복원 #3/#4 | 로그인 회원의 서버 등록/목록·개인키·명령복구 연결 완료, 등록/이름/메인/삭제/중복/version 정책 유지. [계정 API](../ISSUE_3_DEVELOPMENT.md), [등록 연동](../ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md) |
| 전투력·기본 권한 #5/#8 | 캐시/POST 갱신 구현. 미인증·소유상실 상세/power 차단/기존수치 비노출, 원본 자료는 보존. [전투력](../ISSUE_5_DEVELOPMENT.md), [기본 접근](../ISSUE_8_BASIC_ACCESS_DEVELOPMENT.md) |
| 회원 설정 #6·개인키 #7 | 서버 설정/회원별 암호화 키·개인 호출/복원·키version fencing 완료, #1~#7 CLOSED. [회원 설정](../ISSUE_6_MEMBER_SETTINGS.md), [개인키](../ISSUE_7_DEVELOPMENT.md) |
| 생명주기·현재/이력 #8 | UUID/NameClaim/의심·사용차단/V2 현재/퇴역이력·내부정리 구현. live 누락은suspect이며 자동퇴역/claim해제는 비활성. [L1 개발](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md) |
| 대표·활동 #8 | 대표전용 GET/PUT·cooldown제거·기존관리의 명시 전체저장/대표선정, 활동공통1700/부적격보고/선택보존. [대표 계약](../ISSUE_8_REPRESENTATIVE_CONTRACT_DRAFT.md), [활동](../ISSUE_8_ACTIVITY_SELECTION_DEVELOPMENT.md) |
| 역할·개인설정/표시 P1/P2 | 서버 역할요약/개인설정/원정대표시 복원·소유수명/version/명령격리. [역할](../ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md), [개인표시](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md) |
| 본인 원정대 목록 갱신 #8 | 현재소유등록의 정상API목록 기준 추가/누락·현재비퇴역claim 재등장,404조회기준최대3개 대체·실패시소유보존. GET은DB만조회. [구현](../ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md) |
| 장비 소유 인증 #8 | 서버siblings/Armory·6부위/1~3해제·10분/대상·시각/최종만료rollback·실행이력·진단·4장비분류호환. [장비](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [이력](../ISSUE_8_VERIFICATION_HISTORY_DEVELOPMENT.md), [대상/원명령](../ISSUE_8_VERIFICATION_TARGET_DEVELOPMENT.md) |
| 현재 소유자/재등록 #8 | 본인유효소유 start/pending confirm은409 ALREADY_VERIFIED,타회원/소유상실도전·완료replay유지. 같은회원 삭제후등록POST201 owned 재연결·소유/ID/감사유지·활동/대표자동복원없음. [현재정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md), [105번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800) |
| 실제 확인 | [98번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217275533) 사용자실제1회인증/서버verified·현재소유·감사1개일치. [108번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228832537) 새기기동일회원목록/인증상태·표시정상보고. 전체캐릭터/활동/자동상세·분쟁인수와구분 |
| Flutter 완료·후속 | [109번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228853681) 이전 구간 기능209ce85/dev0a11b71 push보고. [111번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229534730) 회원 저장자료 로컬 복원/관리진입 구현, [112번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229647060) 취소 오류·카드 UI 회귀 수정 후 최신1598PASS/분석0 보고. 새 변경은feature/scoped-account-cache 기준5eef0d2·미커밋/미push/dev미반영, 수정 실기기 확인 대기. [113번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229801409) 최초unconfigured에 한한 유효후보 전체 기본선택/최고레벨 대표 저장으로 정정·최신1601PASS 보고. 계정UX 외 신규Backend 요청은 아래 별도 행 참조 |
| 신규 분야별 요청 | [114번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229923232): #10 카탈로그/주차 P0 → #11 주간·#12 그룹 기초 P1 → #13 모집/파티 P2. 본문 검토 완료. #10은feat/raid-services의d7f762f로push완료·공개카탈로그/주차GET 구현·31PASS/실행OpenAPI 일치/로컬HTTP 확인. [두 번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6230019531), Flutter연동대기. #11~#13 명세/구현 미착수. [#10 안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md). 상세 다음 실행은NEXT_WORK 참조 |
| 남은 별도 기능 | 타회원소유이전/분쟁·24시간방어/통지·자동소멸확정/퇴역·프로세스종료후미확정명령영속복구는 미완료/보류. 모집/파티/그룹은 신규 #10~#13 요청으로 분리하며 아직 미구현. Apple/Discord·WebSocket은 별도 |
| 자료·운영 | 현재개발자료/키유지·베타직전초기화는별도사용자지시. 새8001 채택/기초재인수·Firebase이관/삭제·이름기반자료병합없음. Lightsail 운영배포는예정/별도범위 |

상세 합의는 Issue #8의 최신댓글과 현재정책 문서가 우선이다. 과거90번째의본인재인증허용은102번째정책과19c2dcc 구현으로 대체됐다. 완료 구간의 통합과 실제환경/운영 전체인수를 혼동하지 않으며 다음 코드변경은 최신dev의 목적별 작업브랜치에서 진행한다.
