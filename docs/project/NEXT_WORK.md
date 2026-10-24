# 다음 실행

2026-10-24

- **작업 구간명:** 모집 신청·캐릭터 변경 통합 자격 보완(#26).
- **현재 작업 내용:** 통합 후보조회 공통 자격 설계·보완 계약2·closed schema/예시 작성과 정적 검증을 완료했다. Flutter 전체6의 계약2 소비검토·성공/실패UX 확정을 수신했다. 확정범위 공통검증·변경원자성·일괄읽기 구현/격리45PASS를 완료했고 다음은 Flutter 신청·변경 통합연결/Backend 직접차이 대응이다. 실제 개발 반영은 별도다.
- **브랜치·작업 위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 문서 정리·현황/회신 기록과 기존 신청검사 보완을 같은 이력으로 통합했다. 문서 정리는 완료된 내부 구간이며 별도 진행 브랜치로 후속을 쌓지 않는다.
- **직전 완료 구간:** 브랜치 흐름 통합·작업 기록 제1원칙 복구. 통합ebadab8 push/원격일치 확인, 문서 브랜치/임시 작업트리 정리 완료·양쪽 이력 보존. 다음 기능 설계는 위 #26 구간으로 명확히 구분한다.

## Flutter 다음 실행

- **검색 연결:** [#24](https://github.com/heo0328/lostparty-backend/issues/24)의 Flutter 전체6의0d6d960b commit/push·검색 캐시/최대1회 CURSOR_STALE 회복·126mock 보고를 수신했다. 전체7에서 생성자 본인 검색제외 실제정상을 보고했고 추가참가자 검색/탈퇴 재노출·전체 인수는 미확인이다. [Backend 개발 반영 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690), [현재 검색 설명](../features/recruitment/search/README.md).
- **탈퇴·해산 UI/기록:** [#25](https://github.com/heo0328/lostparty-backend/issues/25)의 Flutter A 전용 명령/ACK에 이어 [전체9번째 Flutter · B 메뉴/성공 처리](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6372783376) 0487788a commit/push·295mock, [전체10번째 Flutter · C 명시 조회 프로필/본인 기록](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6373322164) 0c5ae941 commit/push·413mock/최종 분석0 보고를 수신했다. 수치는 각 보고 범위이며 합산/Backend 독립 재현하지 않는다. B/C 구현 대기는 해소됐으며 다음은 #24 검색 후속과 정상 로그인 개발API·실회원/기기 인수다. 해당 #25 구간의 추가 요청은 없고 별도 신청 검증/후보조회 요청은 아래 #26을 따른다.
- **실제 인수:** 정상 로그인으로 게시된 새 명령·검색·자기 기록의 직접 영향을 확인하고 해당 Issue에 회신한다. 합성/mock 통과와 실회원 HTTP·기기 인수는 구분한다. 기존 계약 재수용이나 이미 확인한 전체 시험 반복 대기는 아니다.

## #26 현재 구간 완료·다음 담당

[전체8번째 Flutter · 수동시험 분량/구현범위 해석정정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382315586)/문서8112a2bb push 보고수신. 1~5는 사용자 디바이스 시험 분량만 나눈 것이다. 신청·변경 두intent를 함께 연결하고 생성/상세·일정·완료/해산·다른T 직접 영향을 보호한다. 기존45PASS는 Backend 합성검증이며 전체 UI/UX 연결/기기 인수 완료를 뜻하지 않는다. 같은 정책 재수용/추가시험 결과 회신은 요청하지 않아 수신 확인 댓글은 쓰지 않는다.

계약2의 **공통 자격/배치·기존 명령 연결·일괄 후보조회 구현·격리검증 완료**, 실제 개발 반영은 미진행이다. [실행 소비 계약2](../features/recruitment/participation/candidate-contract.md)·[구현/검증 경계](../features/recruitment/participation/eligibility-design.md)·[집계](../features/recruitment/participation/validation/eligibility-results.json). 고유45PASS(신규19/기존26, 최종소스 분할10+8+27), 후보이미지 소스239파일/177·기본116 계약 전체/기존DTO 보존, 별도0031 제한LOGIN factory·health200/인증2건 확인이다. 실제 합성Bearer 검증과 정상 실회원/기기 인수를 구분한다.

- **다음 Flutter:** 게시된 source/177계약으로 신청·캐릭터변경 두intent의 후보reader·전페이지/역할/빈화면/확인·원명령·갱신을 함께 연결·직접 검증한다. 생성/상세·일정/완료·해산·C/N의 직접 영향도 함께 보호한다. 1~5는 사용자 수동시험 분량/순서만 구분하며 다른 구간의 구현·필요회귀를 미루는 기준이 아니다. 현재 새endpoint 실서버/실회원 시험이나 기존 전체시험 반복은 요청하지 않는다.
- **다음 Backend:** 네이티브의 재현 가능한 직접 소비차이에 대응한다. 실제 개발 API 반영은 별도 승인 구간이며 현재 API176/DB0031·기존 이미지 그대로다. migration/운영·실회원 자료 변경은 하지 않았다.
- **보존:** 지원4직업/역할별성공본·임의TTL/경고차단 없음, 정확한 교체Assignment/lease만 자기제외·원파티우선/반대파티 명시동의, 확인 뒤 변경 거절·실패 rollback/다른T 보존, 승인 자격실패pending유지·원pending/24hACK/거절·철회/IF-001이다.
- **검증 주의:** 기존25PASS/작성21벡터·중간예비35PASS는 이번45건과 합산하지 않는다. 합성 테스트DB/키·factory만 사용했고 운영/실제개발 DB·키를 사용하지 않았다. 게시SHA/회신링크는 아래 마감 기록을 따른다.

구현 source `484ca1719e21b01a59da75b62a1d3b1568ada2c3` / feat/raid-recruitment commit·push·원격 SHA 일치 확인 후 [#26 전체7번째 Backend · 계약2 구현/검증 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382258395) 게시·전문/실제 전체 순번을 재조회했다. 다음 담당 Flutter 신청·변경 통합연결·직접 자동검증/Backend 재현차이 대응이다. 실제 개발API67322372…/176·DB0031 healthy/health200·기존이미지 미교체를 읽기 확인했고 시험용 runner/DB/internal network/API probe는 정리해 기존API/DB만 남겼다. 실회원/기기·개발반영/운영은 별도 미완료다.

같은 모집 브랜치와 본 프로젝트 경로에서 코드·계약·검증·기록을 함께 관리한다. 문서 정리/코드 분리는 반복하지 않는다.

사용자 지정 테스트용 인증 설정은 실제 장비 인증 성공과 구분한다. 다음 사용자 확인이 필요하면 앱 목록 새로고침·활동/대표 선택이며 비공개 실행 근거는 DEV_LOG에 보존한다. 자료/키/DB초기화·개발 fixture 재적용은 수행하지 않는다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

[전체 기능 안내](../README.md)와 [문서 대응표](../engineering/documentation/README.md)의 정리 결과를 현재 모집 브랜치에서 사용한다. 다음 실행은 #26 전체3/4의 확정 범위와 검증 차이를 바탕으로 전체6 계약2·UX 확정에 따른 구현 완료 source/177계약으로 Flutter 신청·변경 통합연결과 Backend 직접 차이 대응을 이어가는 것이다. 문서 파일 편집/협업 수신이라는 이유로 다른 브랜치로 전환하지 않는다. 새 API 합의·구현·개발 반영 상태는 위 구분을 유지한다.
