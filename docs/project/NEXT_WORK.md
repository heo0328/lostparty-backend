# 다음 실행

2026-10-24

- **작업 구간명:** 모집 신청 표시·본인 승인 대기 상태 보완(#26).
- **작업 내용:** 합의된 application-display-1 목록/일반상세 읽기 구현·격리28PASS 완료. 코드·계약·문서·인계를 같은 구간으로 관리한다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`.
- **소스/실제 개발 구분:** 소스후보177경로에 새프로필을 구현했다. 실제 개발은 기존 source484ca17/이미지fdd256ea·177경로/DB0031로 새프로필 미반영이다. 경로수만으로 계약/반영 완료를 판단하지 않는다. 실제서버 교체는별도승인이다.

[#26 전체14번째 Backend · 표시 읽기 구현/검증 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385227653) 게시·전문/실제전체순번 확인 완료. 구현source `06ea4b214591f475d422f4599ca10260cda83d08` / feat/raid-recruitment push·원격일치 확인. 다음Flutter 연결·직접검증/Backend 차이대응, 새프로필 실제개발미반영이다.

## 현재 구현과 다음 담당

[#26 전체13번째 Flutter 제안1 수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384902537) source f0c7665/Flutter84b132a2의 일반상세·프로필분리/목록3필드·본인4필드 소비가능을 기준으로 구현했다. [표시 계약/구현 경계](../features/recruitment/participation/application-display-proposal.md)·[실행검증집계](../features/recruitment/participation/validation/application-display-results.json).

- 목록은 같은read-only snapshot에서 페이지별4bulk조회로Character/Account/head/성공본을 적재하고 기존power_value를 사용한다. 저장display·현재분석/retained성공·head없음·소유연결불가/실제자료실패를 구분하며 전체승인판정을 새로계산하지 않는다.
- 상세는본인·room/실제T/현세대 유효pending우선→최신이력·만료경계읽기expired/GET쓰기0이다. accepted와현재참가는별개다. 기존참가→pending안내→기존신청조건을 따른다.
- 기본/membership-actions-1/본인신청목록·단건review/쓰기DTO/원ACK·거절·철회를 보존한다. 신규프로필만1MiB상한/413, cursor프로필·현세대격리와페이지별분석시점이다. DB조회예외의내부식별자가코드로노출되던기존변환을503 SERVICE_UNAVAILABLE로정정했다.
- **다음 Backend:** 구현소스 게시·인계 완료. 재현가능한 직접소비차이에대응한다.
- **다음 Flutter:** 구현 인계 후 카드전투력/현재분석·본인pending안내/버튼을연결하고 직접영향만검증한다. 실서버인수는정확한개발반영인계후 소수항목으로진행한다. 같은정책재수용/전체시험반복을요청하지않는다.

최종검증은 한호출 고유28PASS(신규17/명령8/membership프로필3,245.41초),기존경고1개다. 후보이미지d24d7cbd…/소스241파일·177/116전체계약·기존component보존,실제개발fdd256ea…미교체/healthy·시험환경정리확인이다. 합성실제Bearer를정상로그인실회원/기기성공으로확대하지않는다.

## 인수·후속 경계

- [전체11 Flutter](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384482003)의 기존후보/역할·신청/목록·수락/양쪽갱신3항목/카드일반상세 정상은사용자보고다. 새프로필·변경/반대파티/C/N 전체인수로확대하지않는다.
- [전체12 Backend 제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384757210)의작성22응답/음성15정적검증과실행시험은별개다. 이전Backend45·Flutter493·디자인56/분석0은각보고범위이며중복합산하지않는다.
- 신청목록진입/재조회시점·실시간/웹소켓/알림은별도후속이며이번에바꾸지않는다. 일반오류는HTTP/code미확인 관찰로보존한다. 이번read profile 구현을그원인수정완료로표시하지않는다.
- 원pending/24hACK·거절/철회·정확본인/T/세대·IF-001을보존한다. 1~5는사용자수동시험분량이며구현/필요회귀제외기준이아니다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

이슈26의 새프로필 구현인계/Flutter 연결회신과 실제 개발미반영을 구분한다. 같은모집브랜치에서 직접차이에대응한다. 실제서버교체/DB·실회원수정·dev/main/운영은별도승인범위다.
