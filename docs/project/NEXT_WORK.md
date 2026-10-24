# 다음 실행

2026-10-24

- **작업 구간명:** 모집 신청·캐릭터 변경 통합 자격 개발 반영(#26).
- **작업 내용:** 검증된API/worker 이미지 교체·자료 보존/실행 검증 완료. 다음은 정상 로그인 앱 수동 인수와 직접 차이 대응이다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 코드·계약·문서·인계를 같은 이력에 유지한다.
- **실제 개발:** 구현source484ca1719e21b01a59da75b62a1d3b1568ada2c3/이미지fdd256ea·177경로·DB0031, API/DB healthy. migration 없음·기존108표/780행·키·설정/볼륨 보존. [반영/검증](../engineering/operations/eligibility-rollout.md)·[집계](../engineering/operations/records/eligibility-rollout.json).

[#26 전체10번째 Backend · 실제 개발 반영/자료보존 검증](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6383315604) 게시·댓글 전문/실제 전체 순번 확인 완료. 반영 근거0096319b027c1da9d2ba0b7cf3667171489c5d9d commit·push·원격 일치 확인. 다음 담당 Flutter 정상로그인 소수항목 인수, Backend 직접차이 대응이다.

## 다음 Flutter · 소수 항목 정상 로그인 인수

[#26 전체9번째 Flutter 통합연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382646003)의 f89c009f push·신청/변경 두intent 통합·493PASS/분석0은 자체보고이며 Backend 독립 재현이 아니다. 새 Backend 보완요청은 없다. [실행 계약2](../features/recruitment/participation/candidate-contract.md)를 실제 개발서버에서 사용할 수 있다.

1. 정상 로그인한 앱에서 대상 방/T의 후보·허용 역할과 원후보0/필터후0/조회오류 표시를 확인한다.
2. 가능한 캐릭터/역할로 신청·공대장 수락과 성공 후 화면 갱신을 확인한다. 실패는 구체 사유/pending 유지와 원ACK 보존을 구분한다.
3. 변경/반대파티 명시동의 및 생성/상세·일정·완료/해산·C/N 직접 영향도 계속 추적하되 사용자에게는 소수항목씩 나눠 요청한다. 1~5는 수동시험 분량일 뿐 구현/회귀 제외 기준이 아니다.

차이가 발생하면 #26에 재현 구간과 개인정보를 제거한 오류/상태를 회신한다. Backend는 직접 차이에 대응한다. 같은 정책 재수용·이미 확인한 전체 시험 반복은 요청하지 않는다. 정상 로그인 실회원 명령·실기기 인수는 아직 미확인이다.

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

같은 모집 브랜치에서 #26 정상 로그인·실기기 인수 회신을 확인하고 직접 차이에 대응한다. 실제 개발177 반영은 완료했으며 dev/main 통합·운영 배포는 별도 미완료다. 문서 편집/협업 기록이라는 이유로 브랜치를 분리하지 않는다.
