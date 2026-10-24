# 다음 실행

2026-10-24

- **작업 구간명:** 모집 신청 표시·본인 승인 대기 상태 보완(#26).
- **작업 내용:** 검증된API/worker 이미지 교체·자료 보존/실행 검증 완료. 가입 소수항목 인수 보고를 수신했다. 신청목록/본인pending 상세 [표시 계약 제안1](../features/recruitment/participation/application-display-proposal.md)·closed schema/작성22예시를 준비했다. 다음은 게시/Flutter 소비차이 확인이며 합의 전 API는 변경하지 않는다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 코드·계약·문서·인계를 같은 이력에 유지한다.
- **실제 개발:** 구현source484ca1719e21b01a59da75b62a1d3b1568ada2c3/이미지fdd256ea·177경로·DB0031, API/DB healthy. migration 없음·기존108표/780행·키·설정/볼륨 보존. [반영/검증](../engineering/operations/eligibility-rollout.md)·[집계](../engineering/operations/records/eligibility-rollout.json).

[#26 전체10번째 Backend · 실제 개발 반영/자료보존 검증](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6383315604) 게시·댓글 전문/실제 전체 순번 확인 완료. 반영 근거0096319b027c1da9d2ba0b7cf3667171489c5d9d commit·push·원격 일치 확인. 다음 담당 Flutter 정상로그인 소수항목 인수, Backend 직접차이 대응이다.

## #26 최신 회신 · 다음 Backend 계약 설계

[전체11번째 Flutter · 가입 소수 인수 통과/일괄 표시 계약 보완 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384482003) 수신. 정상 로그인 앱에서 후보·허용역할, 신청 성공/목록 반영, 공대장 수락/양쪽 참가·인원·계정 갱신3항목과 신청카드→일반상세 진입이 정상이라는 사용자 보고다. Backend 독립 재현이 아니며 변경/반대파티·C/N 전체 인수로 확대하지 않는다. Flutter 카드디자인 c85715c58558cef93d2b839c427446291b609dbe commit/push·analyze0/관련56PASS 보고, 카드 모양은 사용자 확인 대기다.

**현재 Backend:** 신청 목록/일반 상세의 읽기 계약 제안1을 작성·정적 검증했다. 사용자 실행 범위 확인에서 계약 문서 작성·이슈 제안을 허용받았고, API/실행 OpenAPI 구현은 네이티브 합의 이후다. (1) 공대장 신청목록 한 번 조회/페이지에 선택역할의 마지막성공 전투력·현재분석오류/미확인을 일괄 투영하되 오류와 승인불가 자격을 구분한다. (2) 선택room/실제T/현세대의 본인 pending 상태 최소 투영으로 신청버튼 대신 ‘공대장의 승인 대기중입니다.’를 표시할 수 있게 한다. 만료/철회 후 최신 신청가능 여부·수락 후 참가/기존변경 진입, session/권한 격리·시점/nullable·기존DTO 호환을 닫아 제안한다. 카드별 추가GET/provider/자동갱신·상세별 전체 내신청 조회·오래된 로컬성공 힌트는 사용하지 않는다. 기존 판정/원pending·ACK/거절·철회는 유지한다.

이미 신청한 방의 상세 재진입 후 캐릭터 선택에 일반오류가 표시됐다는 관찰은 HTTP/code 미확인이다. 서버 자격버그로 단정하지 않는다. 신청/참가 중 신청버튼 숨김과 pending 안내는 사용자 요구이며 아직 새 읽기계약/구현에 반영되지 않았다. 신청목록 진입/갱신 정책·실시간동기화/웹소켓/알림은 사용자 지시로 별도 후속이다. 다음 Flutter는 계약 수신 후 정확필드 연결·직접경계 검증이며 같은정책 재수용/전체시험 반복 요청은 없다.

## 다음 Flutter · 소수 항목 정상 로그인 인수

[#26 전체9번째 Flutter 통합연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382646003)의 f89c009f push·신청/변경 두intent 통합·493PASS/분석0은 자체보고이며 Backend 독립 재현이 아니다. 전체9 당시 새 Backend 보완요청은 없었으며, 최신 전체11의 표시계약 요청은 위 항목을 따른다. [실행 계약2](../features/recruitment/participation/candidate-contract.md)를 실제 개발서버에서 사용할 수 있다.

1. 정상 로그인한 앱에서 대상 방/T의 후보·허용 역할과 원후보0/필터후0/조회오류 표시를 확인한다.
2. 가능한 캐릭터/역할로 신청·공대장 수락과 성공 후 화면 갱신을 확인한다. 실패는 구체 사유/pending 유지와 원ACK 보존을 구분한다.
3. 변경/반대파티 명시동의 및 생성/상세·일정·완료/해산·C/N 직접 영향도 계속 추적하되 사용자에게는 소수항목씩 나눠 요청한다. 1~5는 수동시험 분량일 뿐 구현/회귀 제외 기준이 아니다.

차이가 발생하면 #26에 재현 구간과 개인정보를 제거한 오류/상태를 회신한다. Backend는 직접 차이에 대응한다. 같은 정책 재수용·이미 확인한 전체 시험 반복은 요청하지 않는다. 전체11의 가입 소수3항목 사용자 인수 보고는 수신했으며 변경·주차교차/전체 실기기 인수는 미완료다.

## 검증 구분·협업 기준

- Backend 격리 고유45PASS(신규19/직접회귀26), Flutter493PASS 자체보고, 실제 반영 HTTP8건·OpenAPI177/116 전체일치는 각각 다른 근거다. 작성21예시·과거시험을 합산하지 않는다.
- #26 [전체6 계약2/UX수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381816954)·[전체7 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382258395)·[전체8 수동시험분량 정정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382315586)을 보존한다. Issue OPEN, 완료와 인수를 구분한다.
- #24 검색 후속/추가참가자 탈퇴 재노출, #25 탈퇴·해산 A/B/C 정상 로그인 인수도 직접 영향만 확인한다. [추적표](ISSUE_TRACKER.md)의 별도 담당/미완료를 유지한다.
- 지원역할·마지막성공 power·정확한 교체Assignment/lease 자기제외·원파티우선/명시이동동의·승인실패pending·24h ACK/거절·철회·IF-001을 보존한다.
- 사용자 지정 테스트 인증 설정은 실제 장비 인증과 구분하며 fixture 재적용/자료·키·DB 초기화는 하지 않는다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

같은 모집 브랜치에서 #26 표시 계약 제안1 게시 후 Flutter의 새프로필/표시·본인상태 소비차이를 확인한다. 합의 전 DTO/API를 변경하지 않으며 일반오류 원인은 code 미확인으로 보존한다. 실제 개발177 반영은 완료했으며 dev/main 통합·운영 배포는 별도 미완료다. 문서 편집/협업 기록이라는 이유로 브랜치를 분리하지 않는다.
