# 다음 실행

2026-10-24 / 기능 작업 `feat/raid-recruitment`, 문서 작업 `docs/document-organization`.

## Flutter 다음 실행

- **검색 연결:** [#24](https://github.com/heo0328/lostparty-backend/issues/24)의 게시 source15e143a·실행176경로 계약으로 검색 캐시/실제T 참가 제외·탈퇴 후 재노출·cursor 회복을 연결하고 직접 영향 범위의 결과를 회신한다. [Backend 개발 반영 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690), [현재 검색 설명](../features/recruitment/search/README.md).
- **탈퇴·해산 UI/기록:** [#25](https://github.com/heo0328/lostparty-backend/issues/25) Flutter A 전용 context/원명령·ACK는6968f47a commit/push·고유177mock/분석0 보고를 수신했다. Backend 독립 재현은 아니다. [A 결과와 미완료 B/C](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371981415). 실제 상세 버튼은 구명령이며 다음 B에서 메뉴·확인·선택T 성공이탈/반대T화면유지·빈effects 관계알림, C에서 profile/본인 옛기록 Router를 연결한다. A 완료를 새 정책 UI 전체 완료로 표시하지 않는다.
- **실제 인수:** 정상 로그인으로 게시된 새 명령·검색·자기 기록의 직접 영향을 확인하고 해당 Issue에 회신한다. 합성/mock 통과와 실회원 HTTP·기기 인수는 구분한다. 기존 계약 재수용이나 이미 확인한 전체 시험 반복 대기는 아니다.

## Backend 다음 실행

새 Backend 차단/수정 요청은 없다. Flutter/사용자의 재현 가능한 계약·동작 차이에 해당 기능 범위로 대응한다. 현재 마지막 개발 전환 근거는 source15e143a/반영920cc059·API176/DB0031이며 [전환·보존 기록](../engineering/operations/README.md)과 [#25 Backend 개발 반영](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996)을 따른다. 이 문서 정리에서 실제 컨테이너/HTTP/DB를 재확인한 상태가 아니다.

사용자 지정 테스트용 인증 설정은 실제 장비 인증 성공과 구분한다. 다음 사용자 확인이 필요하면 앱 목록 새로고침·활동/대표 선택이며 비공개 실행 근거는 DEV_LOG에 보존한다. 자료/키/DB초기화·개발 fixture 재적용은 수행하지 않는다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 문서 작업 마감·다음 채팅

[전체 기능 안내](../README.md)와 [원문/섹션 대응표](../engineering/documentation/README.md)를 기준으로 문서를 관리한다. 문서 정리 브랜치에서 시범·전체 통합을 로컬 커밋으로 마감하며 push·PR·병합은 수행하지 않는다. 원격 게시/통합은 별도 지시 범위다. 기능 작업으로 돌아갈 때는 위 Flutter B/C·#24 연결/실인수와 Backend 재현 차이 대응을 이어가며 현재 설명에 작업단계 문서를 다시 누적하지 않는다.
