# 다음 실행

## 현재 작업 범위 — 공통 기반만 유지, 모집 조건 협의 후 반영

2026-10-19 사용자 정정: 모집 조건 수정·추가를 네이티브와 협의 중이므로 최대한 큰 틀의 기본적인 부분만 구현한다. [#13 전체20번째 Backend 범위 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6264202734). 앞선 최초 공개·현재주차 유한일정·문턱없음 실제지원안의 승인이 아니며, 사용자 답변 대기/같은 선택 재질문을 다음 작업으로 두지 않는다.

기본 관계/식별·snapshot/revision·권한별 조회·원자성/경합·중복요청 ACK 복구·사용량·DB 보존/앱 역할 검증·후보 정지/정리는 이미 구현했다. 세부 일정·전투력·그룹·구성/승인 등 조건 의존 후보는 변경 가능한 초안으로 유지한다. 새 정책 추가·최종OpenAPI/main/실제usage 연결·개발DB/이미지 활성화는 협의 결과 후 대조·설계해서 진행한다. 구현량을 늘리기 위한 추가 추상화나 중복 검증은 하지 않는다. 이슈 전체/Flutter 적용 완료가 아니다.

다음 입력은 사용자·Flutter 협의 결과의 #13 반영이다. Backend는 새 합의가 오면 기존 feat/raid-recruitment의 후보 조건·DTO·DB 제약을 먼저 대조하고 영향 범위만 수정·검증한다. 아래 실제활성화/지원범위 답변대기 기록은 정정 전 이력이다.

[F3 설계·근거 답변 — #13 전체18번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263341047). 독립 F3-A 준비와 사용자 결정/실제 활성화·계약 고정을 구분하며 신규 시험 요청은 없다.

2026-10-19. 현재 브랜치는 **feat/raid-recruitment**다. 완료 G3는 [PR20](https://github.com/heo0328/lostparty-backend/pull/20) bb144e0/dev 후행기록 ce3064f까지 원격 반영했고 feat/group-management는 로컬/원격 정리했다. main77a1fe5는 유지한다. [#16 전체6번째 Backend 통합결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673). 기존 모집 c41fd03/F1·F2 커밋을 보존하고 dev를 merge했으며 모집 자체는 미push/원격추적없음이다. 기능코드·원본OpenAPI·개발서버/DB는 이번 통합에서 변경하지 않았다.

## 준비 완료 — 독립 F3-A 내부 기반

[공유 사용량·DB 준비/권한 검사·참가 정지 제어](../ISSUE_13_F3_PREPARATION.md)를 **a0a515c 로컬커밋·미push**, 격리144PASS/42.77초로 확인했다. [#13 전체19번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263654624). 현재 사용량 GET은 unavailable/후보 router·main lifespan에는 새 기반 미연결이며 OpenAPI/Compose·개발 서버/DB는 그대로다. 독립 준비 완료와 F3 실제 활성화/계약 고정을 구분한다.

## 추가 완료 — F3-B 독립 보존·앱 역할 시험

`06a530f` 로컬커밋·미push. [준비 기록 F3-B](../ISSUE_13_F3_PREPARATION.md)의 일회용 DB/실제 LOGIN 제한 role로0016→0017→0018 migration·기존 합성자료/시각 보존·legacy 신청NULL/거절·새 신청/승인/조회/탈퇴/종료·사용량 해제를 확인했다. 관련 preparation 포함25PASS/9.88초다. 개발DB/서버·원본계약은 미변경, 새 이슈 댓글/Flutter 시험 요청은 없다. 실제 개발 앱 계정/자료·최신이미지 인수는 별도다.

## 추가 완료 — 후보 HTTP 정지 제어 연결

`ffa3575` 로컬커밋·미push. [준비 기록](../ISSUE_13_F3_PREPARATION.md)에 후보 create/apply/join/approve wrapper와 context/approve permissions 연결을 기록했다. 기존 원ACK/조회/거절/철회/탈퇴/이전/종료·내부 실사용량은 유지하며 관련97PASS/31.73초다. 실제 main·usage GET·최종계약·개발서버/DB는미연결이다. [#13 본문](https://github.com/heo0328/lostparty-backend/issues/13) 상단에현재상태를반영했고추가댓글은없다(전체19개).

## 바로 다음 — #13 F3 최종 계약·개발 반영 준비

[F3 활성화 설계](../ISSUE_13_F3_ACTIVATION_DESIGN.md)를 작성했다. 다음 실행은 **최초 지원범위 답변 후 공유 usage·main startup/router·최종OpenAPI 연결**이다. 사용자에게 공개모집·현재주차 안 확정 시작/종료·문턱없음의 최초실제지원 여부를 질문했고 답변 대기다. #13전체17번째에서 필요한 사용자결정으로 남겼으므로 미응답으로 실제활성화하지 않는다. 내부기반/독립migration시험·후보policy/context/permissions 연결은 완료했다. 설계 중 확인한 [전체17번째 Flutter 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263303080)는 최초 지원범위·전투력 입력/수치·그룹탈퇴 제한/정리공개를 사용자 결정으로 분리했다. 독립 원본/격리작업은 가능하되 실제 활성화/계약 고정에 직접 필요한 결정을 먼저 확인한다. 이후 격리검증→개발 전환 준비→0017/0018·앱 반영→최신 이미지 계약 검증/게시·인계 순서다. 설계 이후 내부 준비 기반만 구현·격리검증했으며 OpenAPI/DB·서버는 변경하지 않았다. admissions=false여도 실제 사용량/원ACK·조회·정리는 유지하는 계획이고 신규 source를0/unavailable로 감추지 않는다.

F2-B 후보 HTTP18동작은 **9fb2058 로컬 커밋·미push**, 격리 PostgreSQL/HTTP **101 PASS/35.00초**(HTTP43+F2-A23+F1 32+시각3)다. [F2-B 안내](../ISSUE_13_F2_HTTP.md)·[#13 전체15번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260695606). main 앱/router·원본OpenAPI·개발DB0016/이미지/API8000은 미반영이며 다음 Backend F3다. 서버/DB는 healthy, /health 200을 확인했다. Q1~Q3 미정/Flutter 현재 결함 대응 우선은 유지한다.

이전 F2-A 구현 e74d850/기록5f4cb85의58PASS는 이번101PASS와 중복이다. [F2-A 안내](../ISSUE_13_F2_READS.md).

[F2 구현 설계](../ISSUE_13_F2_IMPLEMENTATION_DESIGN.md)를 작성했다. 순서는 F2-A 조회/권한별 응답·참가조건/정책 → F2-B 격리 HTTP 검증 → F3 DB0017+0018/앱/최종 계약의 동시 반영·게시 인계다. F3 전에는 후보 라우터를 개발 앱에 선노출하지 않는다. Q1~Q3와 초기 지원 부분집합은 제안/미정 경계를 유지한다.

F1 내부room/회차/membership/slot/신청·head·공통한도/weekly·최소회복과0017파일을작성했다. [F1 구현안내](../ISSUE_13_F1_FOUNDATION.md)·[#13 전체13번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259515470). 관련회귀233PASS/107.48초·추가시험뒤최종F1/시각35PASS/14.99초(중복)를확인했다. 단계는내부구현검증이며새모집HTTP/실행OpenAPI·개발DB적용/원격게시/Flutter연결이아니다. F1 코드/migration/시험은9664fb4 및 F2-A e74d850 로컬커밋·문서는후행커밋으로기록하며모두미push,개발DB0016/raid_rooms없음·API8000/원본계약유지다.

1. [상세초안](../ISSUE_13_R1_R2_CONTRACT_DRAFT.md)·[#13 전체12번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259336924)의경로/DTO·권한별projection/페이지·admission-context·정책adapter는F2-A에서내부구현했다. 후보router의strict입력/헤더·인증/HTTP응답은F2-B에서검증했다. 다음은최종지원표/계약과DB·source·main 앱반영을동일검증구간으로맞추는F3다. 내부반환값을그대로Flutter계약으로인계하지않는다.
2. F1은생성/참가·신청·승인에명시policy가필수다. Q1종료불명/주차넘는일정, Q2역할별최소전투력근거, Q3그룹탈퇴후room잔류·회복/조회는미정이다. 회신없음을승인으로해석하지않고그룹adapter/미정일정/전투력문턱분기는활성화하지않는다. 내부기반은공개방/유한단일회차를검증한것으로영구제품정책/요구폐기가아니다.
3. F3에서는후보OpenAPI를기존main 앱의422제거/공통헤더가공과동일하게맞추고새지원범위·응답/기존카탈로그·그룹·주간·bootstrap호환성을확인한다. 새제품결정이필요하면그동작만분리한다. Flutter는현재로그인후화면결함대응우선이며Q1~Q3의정책승인/모집인수는미완료다.
4. F3 기존API/DB반영은별도실행구간이다. 0017/0018파일을개발DB에적용하지않았다. 실제HTTP검증구간완료→commit/push·원격확인→필요한신규소비인계순서를유지한다. 내부시험만으로구현API/Flutter·실기기/운영완료로표시하지않는다.

현재검증명령/범위·실제미실행은F1안내/DEV_LOG를따른다. 구간설정·계약·현재코드전체는feat/raid-recruitment에보존한다. G3 기준은 dev 통합을 반영했으므로 이후 모집 PR에는 모집 변경만 포함하는지 확인한다. 브랜치 분리 뒤 사용자 요청으로 F1 구현과 설계·진행 문서를 구분해 로컬 커밋했다. 모집 코드는 미push/dev 미통합이며 이번에는 dev의 G3 기준만 merge로 반영했다.

## 회신 반영과 별도 후속

- #16 [전체6번째 Backend](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673): 완료 G3 dev통합/원격확인·완료브랜치정리. 통합전 G3 45PASS/실행OpenAPI일치(기존148PASS와중복). 조건부해산/추방/대표변경·Flutter연결/실기기는후속이며이슈는열린상태다.
- #12 [전체17번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6259124455): G1/G2 인계 접수/연결 미완료. 앱 최초조회 추가·기초 반복시험 요청 없음.
- #15/Flutter 현재: [#13 전체16번째 Flutter 보고](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260778487)에서 D1~D4 dev반영·마감/분쟁실기기사용자보류를확인했다. 이는 당시 우선 보고였으며 #13 전체17번째는 해당 수정을 별도 마감하고 계약 검토로 전환했다고 정정했다. F2-A/F2-B 보고는 접수만이며 Q1~Q3 정책승인/Flutter연동·실서버인수가 아니다.
- #17 [전체1번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6259126286): 공급API의 소멸근거/한계·suspect해소/재등장/대표404·최소ID/revision계약 검토가 독립 후순위다. HTTP200/시간경과만으로소멸확정·보류해제/삭제하지 않는다.
- #18 [전체1번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6259126990): 첫관측/첫1700·명시제외 영속정책/DTO·동시성 초안이 후순위다. 도입이전 미선택 일괄활성화·GET쓰기를 하지 않는다. 수동1700미만 선택/대표를 보존한다.
- #19 [전체1번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/19#issuecomment-6259127594): type최초고정·함께집계조건/해산OFF·평균분모·그룹조회권한은 미확정이다. R1/R2 실제원천 보존을 막지 않으며 집계/마감worker·통계HTTP는 이번 제외다.

R3확장관리/R4완료·반복·공개전환/다중동의·정족수/일정불명확인·고급이동은 별도 구간이다. G3조건부해산은 실제활성그룹모집 원본과 transaction 검사 후 연결한다. V2실제파티영향 adapter 미연결의 PARTY_IMPACT_REVIEW_REQUIRED는 유지한다. 없는원본을0건으로치환하지않고 개인manual을방결과로만들지않는다. 기능이 독립적으로커지면 착수전에별도주제로분리·상호링크한다.

## 유지할 실행 기준

기존 로컬Docker/API8000·DB0016·자료/키를 사용한다. 회원 기본그룹정원15/개인가입5/개인모집10·정확한도기존정상이 기준이며 실제방제한은 [한도 계약](../ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)과 #13전체6번째를 따른다. 네트워크실패/이름으로UUID·소유/과거설정·자리를이어붙이지않는다. 미확정통계정책/자동퇴역·운영삭제를이번에추가하지않는다.

새환경/자료이관·DB초기화/볼륨삭제·기존Firebase/기기자료삭제·키변경·운영배포/main통합은없다. [이슈추적표](ISSUE_TRACKER.md), [기능지도](AI_CONTEXT.md), [검증/결정이력](DEV_LOG.md)을 함께 확인한다.
