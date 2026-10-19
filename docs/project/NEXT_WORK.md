# 다음 실행

2026-10-19. 현재 모집 작업 브랜치는 **`feat/raid-recruitment`**다. G3의 `feat/group-management`/원격 HEAD `349fb79`에서 로컬 분기했으며 아직 원격 브랜치/추적 설정이 없다. 기존 G3 브랜치와 커밋은 그대로 보존했다. G3 구현/계약 `332a8ab` 및 후행 문서는 게시 완료·main/dev 미병합이며, 새 모집 브랜치가 그 기준을 상속한 것을 G3 통합 완료로 해석하지 않는다. F1 내부코드/0017파일/시험은 `9664fb4`로 로컬 커밋했고 구간설정·상세명세·F2 설계 및 진행 기록은 후행 문서 커밋으로 구분한다. 모두 미push다. 개발 API/DB는 이번에 변경하지 않았다.

## 바로 다음 — #13 F2 지원범위·HTTP 연결

[F2 구현 설계](../ISSUE_13_F2_IMPLEMENTATION_DESIGN.md)를 작성했다. 순서는 F2-A 조회/권한별 응답·참가조건/정책 → F2-B 격리 HTTP 검증 → F3 DB/앱/최종 계약의 동시 반영·게시 인계다. F3 전에는 후보 라우터를 개발 앱에 선노출하지 않는다. Q1~Q3와 초기 지원 부분집합은 제안/미정 경계를 유지한다.

F1 내부room/회차/membership/slot/신청·head·공통한도/weekly·최소회복과0017파일을작성했다. [F1 구현안내](../ISSUE_13_F1_FOUNDATION.md)·[#13 전체13번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259515470). 관련회귀233PASS/107.48초·추가시험뒤최종F1/시각35PASS/14.99초(중복)를확인했다. 단계는내부구현검증이며새모집HTTP/실행OpenAPI·개발DB적용/원격게시/Flutter연결이아니다. F1 코드/migration/시험은9664fb4 로컬커밋·문서는후행커밋으로기록하며모두미push,개발DB0016/raid_rooms없음·API8000/원본계약유지다.

1. [상세초안](../ISSUE_13_R1_R2_CONTRACT_DRAFT.md)·[#13 전체12번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259336924)의경로/DTO·권한별projection/페이지·admission-context·정책adapter를확정된지원범위로HTTP/OpenAPI에연결한다. 내부반환값을그대로Flutter계약으로인계하지않는다.
2. F1은생성/참가·신청·승인에명시policy가필수다. Q1종료불명/주차넘는일정, Q2역할별최소전투력근거, Q3그룹탈퇴후room잔류·회복/조회는미정이다. 회신없음을승인으로해석하지않고그룹adapter/미정일정/전투력문턱분기는활성화하지않는다. 내부기반은공개방/유한단일회차를검증한것으로영구제품정책/요구폐기가아니다.
3. F2에서는정책지문·권한순서/정보공개·실제소유/활동/한도/주간·동시성회귀를확인하고미정분기에직접의존하지않는단위를진행한다. 새제품결정이필요하면그동작만분리한다. Flutter는현재#15우선유지/Q1~Q3의기존소비충돌만확인한다.
4. F3 기존API/DB반영은별도실행구간이다. 이번0017파일을개발DB에적용하지않았다. 실제HTTP검증구간완료→commit/push·원격확인→필요한신규소비인계순서를유지한다. 내부시험만으로구현API/Flutter·실기기/운영완료로표시하지않는다.

현재검증명령/범위·실제미실행은F1안내/DEV_LOG를따른다. 구간설정·계약·현재코드전체는feat/raid-recruitment에보존한다. 이후 게시/통합 시 G3 기반과 모집 변경의 범위를 구분한다. 브랜치 분리 뒤 사용자 요청으로 F1 구현과 설계·진행 문서를 구분해 로컬 커밋했다. push/merge는 없다.

## 회신 반영과 별도 후속

- #16 [전체5번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6259125692): G3 최소ACK/관리GET에 문서상 차단 충돌 없음. G3 Backend148PASS/실행OpenAPI일치·API8000반영/DB0016유지·게시인계완료. Flutter 연결/실기기·main/dev통합은 별도다. [개발 안내](../ISSUE_16_GROUP_G3_DEVELOPMENT.md).
- #12 [전체17번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6259124455): G1/G2 인계 접수/연결 미완료. 앱 최초조회 추가·기초 반복시험 요청 없음.
- #15 [전체3번째 Flutter D2](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6259074435): 내부 연결174고유테스트/분석0보고·미커밋/미push, 기존UI V1. 다음D3인증UI→D4상단/최종영향검증, 추가Backend요청없음. 해당 우선작업을 유지한다.
- #17 [전체1번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6259126286): 공급API의 소멸근거/한계·suspect해소/재등장/대표404·최소ID/revision계약 검토가 독립 후순위다. HTTP200/시간경과만으로소멸확정·보류해제/삭제하지 않는다.
- #18 [전체1번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6259126990): 첫관측/첫1700·명시제외 영속정책/DTO·동시성 초안이 후순위다. 도입이전 미선택 일괄활성화·GET쓰기를 하지 않는다. 수동1700미만 선택/대표를 보존한다.
- #19 [전체1번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/19#issuecomment-6259127594): type최초고정·함께집계조건/해산OFF·평균분모·그룹조회권한은 미확정이다. R1/R2 실제원천 보존을 막지 않으며 집계/마감worker·통계HTTP는 이번 제외다.

R3확장관리/R4완료·반복·공개전환/다중동의·정족수/일정불명확인·고급이동은 별도 구간이다. G3조건부해산은 실제활성그룹모집 원본과 transaction 검사 후 연결한다. V2실제파티영향 adapter 미연결의 PARTY_IMPACT_REVIEW_REQUIRED는 유지한다. 없는원본을0건으로치환하지않고 개인manual을방결과로만들지않는다. 기능이 독립적으로커지면 착수전에별도주제로분리·상호링크한다.

## 유지할 실행 기준

기존 로컬Docker/API8000·DB0016·자료/키를 사용한다. 회원 기본그룹정원15/개인가입5/개인모집10·정확한도기존정상이 기준이며 실제방제한은 [한도 계약](../ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)과 #13전체6번째를 따른다. 네트워크실패/이름으로UUID·소유/과거설정·자리를이어붙이지않는다. 미확정통계정책/자동퇴역·운영삭제를이번에추가하지않는다.

새환경/자료이관·DB초기화/볼륨삭제·기존Firebase/기기자료삭제·키변경·운영배포/merge는없다. [이슈추적표](ISSUE_TRACKER.md), [기능지도](AI_CONTEXT.md), [검증/결정이력](DEV_LOG.md)을 함께 확인한다.
