# 다음 실행

2026-10-24 / 기능 작업 `feat/raid-recruitment`, 문서 작업 `docs/document-organization`.

## Flutter 다음 실행

- **검색 연결:** [#24](https://github.com/heo0328/lostparty-backend/issues/24)의 Flutter 전체6의0d6d960b commit/push·검색 캐시/최대1회 CURSOR_STALE 회복·126mock 보고를 수신했다. 전체7에서 생성자 본인 검색제외 실제정상을 보고했고 추가참가자 검색/탈퇴 재노출·전체 인수는 미확인이다. [Backend 개발 반영 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690), [현재 검색 설명](../features/recruitment/search/README.md).
- **탈퇴·해산 UI/기록:** [#25](https://github.com/heo0328/lostparty-backend/issues/25)의 Flutter A 전용 명령/ACK에 이어 [전체9번째 Flutter · B 메뉴/성공 처리](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6372783376) 0487788a commit/push·295mock, [전체10번째 Flutter · C 명시 조회 프로필/본인 기록](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6373322164) 0c5ae941 commit/push·413mock/최종 분석0 보고를 수신했다. 수치는 각 보고 범위이며 합산/Backend 독립 재현하지 않는다. B/C 구현 대기는 해소됐으며 다음은 #24 검색 후속과 정상 로그인 개발API·실회원/기기 인수다. 해당 #25 구간의 추가 요청은 없고 별도 신청 검증/후보조회 요청은 아래 #26을 따른다.
- **실제 인수:** 정상 로그인으로 게시된 새 명령·검색·자기 기록의 직접 영향을 확인하고 해당 Issue에 회신한다. 합성/mock 통과와 실회원 HTTP·기기 인수는 구분한다. 기존 계약 재수용이나 이미 확인한 전체 시험 반복 대기는 아니다.

## Backend 다음 실행

**#26 기존 신청 구성검사 보완 구현·격리 검증 완료 / 후보조회 계약 검토 대기.** 원본 #13 전체142/143 요청은 [#26](https://github.com/heo0328/lostparty-backend/issues/26)에 한 주제로 연결하고 [전체145번째 Backend 요청 회신/후속연결](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6381088415)을 게시했다. [#26 전체1번째 Backend · 구현/검증·후보계약 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381161170) 전문·순번 확인 완료. 구현 source `6e0063c7c5a3ff88612bbe1c9b01f50b7408ce2a` / feat/raid-recruitment commit·push·원격 SHA 일치 확인, 고유25PASS(신규16/기존9)·source235Python/기본116·두주차176 계약 전체 일치·기존 component/DTO 보존/2description변경이다.

- **다음 Flutter:** [닫힌 후보조회 제안1](https://github.com/heo0328/lostparty-backend/blob/6e0063c7c5a3ff88612bbe1c9b01f50b7408ce2a/docs/APPLICATION_CHARACTER_CANDIDATES_PROPOSAL.md)의 역할별 Permission·scope/snapshot/cursor·원후보0/필터후0/오류·비동기 격리의 구체 소비차이를 #26에 회신한다. 후보 제외는 사용자 확정 레벨/구성/동일T 레이드 개인·파티완료/다른방 실제참가4기준이며 전투력/한도 등은 기존 선택 후 context 안내다.
- **다음 Backend:** 회신 차이를 반영해 신규 endpoint/DTO를 합의하고 후보읽기를 구현한다. 신규 GET은 미합의/미구현·실행176계약에 없으며 임의 구현하지 않는다. pending 구성검사/정원 보완은 완료했지만 실제 개발서버에는 미반영이다.
- **실제 개발:** 기존 API67322372…/DB0031 유지·API/DB healthy/health200 읽기 확인, 교체/이행·실회원쓰기/키변경 없음. 합성 tmpfs DB/runner/internal network 정리 완료. 새 구성검사 실제 반영은 별도 승인 후, 정상로그인/실회원·기기 인수는 반영 뒤다.
- **최근 수신:** #24 전체6 Flutter0d6d960b의 검색회복 연결/126mock, 전체7 생성자 검색제외 실제정상·추가참가자 미확인, #13 전체144 Flutter63b77872 신청카드 기본상세 수정/117mock 보고수신. 최초 승인오류 원인은 code/request_id 없어 미확정이다. 이번 요청은 #26에 직접 대응하며 독립 인수/미완료를 폐기하지 않는다.

문서 브랜치를 보존하고 기존 기능 브랜치는 별도 작업트리 `/tmp/lostparty-application-work`에서 이어갔다. 코드/실행 계약을 문서 브랜치에 merge/cherry-pick하지 않았다. 문서 브랜치의 이번 수신 기록은 로컬 커밋만 남긴다.

사용자 지정 테스트용 인증 설정은 실제 장비 인증 성공과 구분한다. 다음 사용자 확인이 필요하면 앱 목록 새로고침·활동/대표 선택이며 비공개 실행 근거는 DEV_LOG에 보존한다. 자료/키/DB초기화·개발 fixture 재적용은 수행하지 않는다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 문서 작업 마감·다음 채팅

[전체 기능 안내](../README.md)와 [원문/섹션 대응표](../engineering/documentation/README.md)를 기준으로 문서를 관리한다. 문서 정리 브랜치에서 시범·전체 통합을 로컬 커밋으로 마감하며 push·PR·병합은 수행하지 않는다. 원격 게시/통합은 별도 지시 범위다. 기능 작업으로 돌아갈 때는 위 #24 연결·#25 정상 로그인 실인수와 Backend 재현 차이 대응을 이어가며 현재 설명에 작업단계 문서를 다시 누적하지 않는다.
