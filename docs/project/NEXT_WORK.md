# 현재 작업과 다음 실행

기준일 2026-10-17. 현재 사용하던 로컬 Docker/포트8000·개발자료로 개발을 계속한다. 기본 앱 실행·로그인·키·등록/갱신·인증 완료를 유지하며 새 환경·초기 설정·기본 기능 재인수로 되돌리지 않는다.

## 현재 완료 구간과 통합

- Backend #8의 대표/활동 정책, 캐릭터 생명주기·현재/이력 조회, 역할 요약·개인 설정/표시, 인증 실행 이력·서버 장비 증거, 본인 목록 갱신/조회 기준 복구, 인증 대상 선택, 장비 분류 호환, 현재 소유자 차단·같은 회원 재등록 연결까지 이번 구간 완료다.
- 최신 구현/계약은 `19c2dcc33630078fa0d88a1dd60e11857a44472b`. [105번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800), [현재 소유자 정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md)이 기준이다. 현재 본인 유효인증의 start/pending confirm은409 ALREADY_VERIFIED, 타회원/소유상실 도전은 허용·장비 확인 후 소유 연결 보류, 완료된 원명령 ACK/현재GET은 유지한다. 같은 회원의 삭제 후 재등록은 확인 가능한 기존 소유에 장비 재인증 없이 연결한다.
- 최종 관련 격리 PostgreSQL/모의HTTP **483PASS**와 실행 OpenAPI 일치가 검증 기준이다. 이번 문서·통합 작업은 기능 코드를 변경하지 않으며 동일 코드의 테스트를 반복하지 않는다.
- [98번째 실제1회 인증 성공](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217275533)은 사용자 결과와 서버verified/현재소유/감사1개를 대조했다. 새 정책의 모든 기기 경합/삭제재등록·분쟁 인수까지 확인한 결과는 아니다.
- **통합/정리 완료:** [PR #9](https://github.com/heo0328/lostparty-backend/pull/9) 병합 `ea1384d`와 후행 문서 기록을 dev/main의 동일 HEAD로 동기화·push했다. 완료 브랜치 `feat/representative-selection`은 로컬·원격 삭제했고 main/dev만 유지한다. [110번째 Backend 통합 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228957999)에 최종 원격 SHA `860c84a`·정리 상태를 기록했다. 구현/검증 기준은19c2dcc이며 통합·후행 기록은 문서만 변경한다.

## Flutter 완료와 남은 후속

본문 제외 댓글 순번은 Backend 작업 단계 번호가 아니다.

| 댓글 | 작성 측·단계 | 상태 |
|---|---|---|
| [106번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228427796) | Flutter 서버ALREADY/재등록201 owned 소비 | 전체1590PASS·분석0 보고, pending 실제상태/ACK복구·새등록ID·unconfigured 정상처리 |
| [107번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228564592) | Flutter 상태/숫자 표시 | 최종전체1591PASS·분석0 보고. 정수부/쉼표는 표시만 변경·원본 소수/자격/정렬 보존 |
| [108번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228832537) | 사용자 새 기기 확인 수신 | 같은 회원의 서버 원정대 목록·인증 상태와 표시 정상. 전체 캐릭터/활동·역할·자동상세 복원 인수와 구분 |
| [109번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228853681) | Flutter dev 통합·후속 분석 | 기능209ce85/dev0a11b71 push/원격일치 보고. 기본flag OFF의 관리 진입/회원 캐릭터 로컬 복원 공백 확인 |
| [111번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229534730) | Flutter 회원 주목록·로컬 복원/관리 진입 | 기존 계약으로 구현·1596PASS 보고. 자동 flag false 유지, 서버 저장 자료 복원과 provider 자동 실행 분리 |
| [112번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229647060) | Flutter 실제 UI 회귀 수정 | 표시 인원수 취소 오류 재현·수정, 기존 카드/하단 체크 영역 복구. 최신 전체1598PASS·분석0 보고, 수정 후 실기기 재확인 전 |

**최신 담당은 Backend — 신규 분야별 명세 검토/작성**이다. [114번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229923232)으로 아래 이슈가 등록됐다. 111~113번째의 추가 Backend 요청 없음은 당시 계정 UX 범위에 한정하며 신규 요청 대기와 구분한다. 네 이슈의 본문을 확인했다. #10과 #11 첫 구간은 아래와 같이 구현·검증했고 #12 G1은 명세 게시·내부기초구현/검증·HTTP미연결, #13은 명세/구현 전이다.

| 순서 | 이슈·분야 | 먼저 진행할 범위 | 분리할 미확정/후속 |
|---|---|---|---|
| P0 | [#10 카탈로그·서버 주차](https://github.com/heo0328/lostparty-backend/issues/10) | 공개GET /v1/raid-catalog·/v1/raid-cycle 구현·31PASS/실행OpenAPI 일치/로컬HTTP 확인 | 초기 앱 자료를 최신 게임 패치 사실로 간주하지 않음 |
| P1 | [#11 주간 상태](https://github.com/heo0328/lostparty-backend/issues/11) | 원장·본인 배치 조회·비점유 개인 완료/정정 구현, 관련 총83PASS | 점유 중 완료는 영향 확인·파티 원자 연결, 전체 완료 권한 미확정 |
| P1 | [#12 그룹](https://github.com/heo0328/lostparty-backend/issues/12) | [G1 명세 게시](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232074318)·내부기초118PASS/HTTP미연결. G2 초대/신청/코드·권한은 후속 | 그룹당/회원당50 제한 미확정, 해산의 활성 모집 검사는 파티와 연결 |
| P2 | [#13 모집·파티](https://github.com/heo0328/lostparty-backend/issues/13) | 공통 계약 참조해 R1 조회/생성·R2 신청/승인·즉시가입부터 명세 | 전체 완료 권한·종료시간null·확장 승인정책은 해당 동작만 분리 |

- **현재 작업 브랜치 `feat/raid-services`**: [#10 첫 번째 Backend 명세](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6229990139), [개발 안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md). 관련31PASS·기존 계약 보존·실행OpenAPI 전체 일치·로컬 HTTP 두 조회/API·DB health를 확인했다. 카탈로그는원본2026.08.20/5raid·13difficulty, 외부API/DB 호출 없는 공개 읽기다. 구현/계약 `d7f762f`를 작업 브랜치로push·원격확인 후 [#10 두 번째 Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6230019531)를 게시했다. dev/main 병합은 수행하지 않았다.
- **#11 첫 구간 구현·검증 완료**: [첫 번째 Backend 계약](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230283275), [주간 안내](../ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md). 본인 최대50캐릭터 배치GET/현재주차 manual 완료·정정PUT, 난이도 공유 주간 원장과 내부 점유 가드를 구현했다. 주간51+카탈로그31+모델/migration1 =83PASS/34.57초, 실행OpenAPI 전체 일치. 실제 로컬에서는 새 경로의 비인증401·기존 카탈로그/주차200·health와 신규테이블만 추가한0011 적용을 확인했다. 실제 회원 데이터에 완료 쓰기/Flutter 연동 시험은 수행하지 않았다. 구현/계약 `bce6133`을push·원격확인 후 [#11 두 번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230329942)로 회신했다. 후행문서는 같은 브랜치로 게시하며 dev/main 미병합이다.
- **#8 수동 활동/대표 레벨 정책 구현 완료**: [115번째 정책](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230281148)·[118번째 구간 설계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230431817), [설계/결과](../ISSUE_8_MANUAL_ACTIVITY_POLICY_PLAN.md). 공통수동자격은lifecycle/claim만검사하고, 저레벨저장·대표/no-op·ineligible/갱신판정을 함께 보완했다. 초기기본선택1700·레이드/전투력의별도기준·소유/CAS/멱등은 유지한다. 기존needs_reconfiguration은다음명시저장으로정상화하며DB보정은없다. 활동20PASS/직접회귀244PASS를확인하고 구현/계약d33f873을push·원격확인·로컬8000반영·전체OpenAPI일치/health·DB0011유지를확인했다. [119번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230483893)완료, Flutter실제저장확인대기. dev/main미병합이다.
- **#12 G1 내부 선행 구현·검증 완료, HTTP미연결**: [명세](../ISSUE_12_GROUP_G1_SPEC.md)·[기초구현](../ISSUE_12_GROUP_G1_FOUNDATION.md). 그룹/회원/디렉터리3모델·0012파일·내부생성/회원조회/이름수정·소유/권한/CAS/멱등/원자성을구현하고관련118PASS·기존OpenAPI전체불변을확인했다. 공개인증/활동선택/최종한계값은정책hook필수주입·HTTP미연결로분리했다. 0012는격리DB에서만검증했고개발DB는0011·기존API유지다. 같은feat/raid-services로묶어게시·#12결과를인계한다.
- **다음Backend는#12최신회신검토와G1 HTTP adapter·목록/cursor·OpenAPI연결**이다. Flutter는공개GET인증·생성활동선택/DTO소비충돌을#12로회신한다. 50/50미확정한계값은독립기초의대기사유로삼지않는다. 아직네이티브가호출할그룹API/실기기확인대상은없다. G2/G3·실제모집연계는후속이다.
- 각 분야의 최종 경로/DTO·응답/오류 예시와 확정/미확정 범위를 해당 이슈에 먼저 제안하고 합의된 단위로 구현·검증·게시한다. 전체 화면 UX를 기다리거나 #8의 분쟁/자동퇴역 전체를 선행조건으로 삼지 않는다.  #10 명세/구현·Backend 검증과 Flutter 실제 연동 완료를 구분한다.
- [113번째 Flutter UX 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6229801409): 최신 사용자 승인으로 최초unconfigured·현재 소유·완전한canonical 목록에서만 공통1700 유효 후보 전체를 기본 선택하고 최고레벨 대표를 저장한다. 기존configured/needs_reconfiguration·사용자 선택은 유지하며 후보0은 쓰지 않는다. 과거의 전체 자동 선택/저장 금지 및111번째의 복원 쓰기0 설명은 이 최초 설정에 한해 대체된다. 최신115번째에 따라1700은 이 최초 기본 선택 기준일 뿐이며 수동 활동/대표 선택에는 레벨 하한을 두지 않는다. 서버 레벨 차단은119번째로수정/반영했고120번째Flutter가계약일치를확인했다. 개인 수동rank는 자동 생성하지 않는다.
- **최신 Flutter 결과**: [#8 120번째·수동 정책 인계 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230534018)으로 게시코드/계약일치·서버선행대기해소를보고했다. [#10 세 번째·카탈로그/서버주차 연결](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6230533662), [#11 세 번째·주간GET/개인완료·정정 연결](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230533862)은최종전체1622PASS/분석0 보고이며모의HTTP/실제controller검증이다. 새변경은feature/scoped-account-cache 기준HEAD5eef0d2·미커밋/미push/dev/main미반영이다.
- 다음 사용자/Flutter 확인은실제저레벨수동선택·대표저장/재진입과주간체크·해제/다른기기완료복원이다. 실제회원HTTP쓰기/실기기/지연시간은미확인이다. 주간완료는서버원장, 표시레이드선택preference는회원/환경별현재기기의secure store이며다른기기복원으로보지않는다. #11의원key/body영속복구는주간명령에한정하고기존모든명령의영속복구완료로확대하지않는다. 추가Backend수정/계약충돌요청은없고#12G1명세는독립진행가능하다.

## 남은 별도 범위와 실행 원칙

- 타회원 분쟁·소유권 이전/24시간 수동 방어·자동 소멸확정/퇴역은 별도 보류다. 현재 타인 챌린지/장비 제어 확인을 소유 이전 완료로 보지 않는다.
- 앱 프로세스 종료로 원 key/body가 소실된 미확정명령의 영속복구는 미제공이다. 앱 수명 내 동일명령 복구와 구분하며 새 journal/API를 임의 추가하지 않는다.
- Issue #8은 후속 추적을 위해 열린 상태를 유지한다. 현재 Backend 구간 완료가 Flutter 후속·Issue 전체·운영 완료를 뜻하지 않는다.
- 현재 레이드 범위는 feat/raid-services에서 이어간다. 다른 범위가 필요하면 최신 dev에서 목적별 작업 브랜치를 만들고 해당 Issue의 최신 합의를 확인한다.
- 현재 DB는 신규 주간 테이블만 추가한0011이며 기존 개발자료/키를 유지한다. 사용자 지시의 베타 직전 시점에만 DB 내용 초기화를 별도 수행한다. Firebase/기기자료 삭제·이름 기반 병합·이관, 별도8001 채택·백업/복원 마이그레이션은 하지 않는다.
- Lightsail 운영 배포는 별도다. 이전 Git 통합에서는 서버/DB를 변경하지 않았다. 이번 #10/#11은 로컬API를 반영했고 #11의0011 신규테이블만 추가했다. 개발DB 볼륨/기존 업무 자료·키는 보존했다. 상세 검증/장애/결정은 [DEV_LOG](DEV_LOG.md), 기능별 기준은 [AI_CONTEXT](AI_CONTEXT.md)를 따른다.
