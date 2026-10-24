# 다음 실행

2026-10-24

- **작업 구간명:** 모집 신청·캐릭터 변경 통합 자격 보완(#26).
- **현재 작업 내용:** 통합 후보조회 공통 자격 설계·보완 계약2·closed schema/예시 작성과 정적 검증을 완료했다. 현재는 계약 검토 제안·미합의/미구현이며 다음 Flutter 소비차이 검토/Backend 차이 반영이다.
- **브랜치·작업 위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 문서 정리·현황/회신 기록과 기존 신청검사 보완을 같은 이력으로 통합했다. 문서 정리는 완료된 내부 구간이며 별도 진행 브랜치로 후속을 쌓지 않는다.
- **직전 완료 구간:** 브랜치 흐름 통합·작업 기록 제1원칙 복구. 통합ebadab8 push/원격일치 확인, 문서 브랜치/임시 작업트리 정리 완료·양쪽 이력 보존. 다음 기능 설계는 위 #26 구간으로 명확히 구분한다.

## Flutter 다음 실행

- **검색 연결:** [#24](https://github.com/heo0328/lostparty-backend/issues/24)의 Flutter 전체6의0d6d960b commit/push·검색 캐시/최대1회 CURSOR_STALE 회복·126mock 보고를 수신했다. 전체7에서 생성자 본인 검색제외 실제정상을 보고했고 추가참가자 검색/탈퇴 재노출·전체 인수는 미확인이다. [Backend 개발 반영 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690), [현재 검색 설명](../features/recruitment/search/README.md).
- **탈퇴·해산 UI/기록:** [#25](https://github.com/heo0328/lostparty-backend/issues/25)의 Flutter A 전용 명령/ACK에 이어 [전체9번째 Flutter · B 메뉴/성공 처리](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6372783376) 0487788a commit/push·295mock, [전체10번째 Flutter · C 명시 조회 프로필/본인 기록](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6373322164) 0c5ae941 commit/push·413mock/최종 분석0 보고를 수신했다. 수치는 각 보고 범위이며 합산/Backend 독립 재현하지 않는다. B/C 구현 대기는 해소됐으며 다음은 #24 검색 후속과 정상 로그인 개발API·실회원/기기 인수다. 해당 #25 구간의 추가 요청은 없고 별도 신청 검증/후보조회 요청은 아래 #26을 따른다.
- **실제 인수:** 정상 로그인으로 게시된 새 명령·검색·자기 기록의 직접 영향을 확인하고 해당 Issue에 회신한다. 합성/mock 통과와 실회원 HTTP·기기 인수는 구분한다. 기존 계약 재수용이나 이미 확인한 전체 시험 반복 대기는 아니다.

## Backend 다음 실행

**#26 최신요구 — 신청·캐릭터변경 통합 자격/후보계약 Backend 보완 차례.** 원본 #13 전체142/143 요청은 [#26](https://github.com/heo0328/lostparty-backend/issues/26)에 한 주제로 연결하고 [전체145번째 Backend 요청 회신/후속연결](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6381088415)을 게시했다. [#26 전체1번째 Backend · 구현/검증·후보계약 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381161170) 전문·순번 확인 완료. 구현 source `6e0063c7c5a3ff88612bbe1c9b01f50b7408ce2a` / feat/raid-recruitment commit·push·원격 SHA 일치 확인, 고유25PASS(신규16/기존9)·source235Python/기본116·두주차176 계약 전체 일치·기존 component/DTO 보존/2description변경이다.

- **최신 수신 — [전체3번째 Flutter · 사용자 확정 신청/캐릭터변경 통합 자격](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381254676):** 신청과 변경 선택목록·context/실제POST·승인을 같은 정책으로 검증한다. 선택T 묶음 전체 레벨·선택역할 전투력·동일raid 개인/파티완료·다른방 실제참가·4인별 동일딜러직업/딜러3+서포터1 구성을 모두 검사한다. **기존 전투력은 후보제외 밖/신청 전용 범위는 이 최신 요구로 대체됐다.** 원래 구성검사25PASS는 이전 구간 근거이고 통합 후보/변경 구현 완료가 아니다.
- **역할/구성:** 일반직업 dealer전용·바드/발키리/도화가/홀리나이트 양역할 정책과 eligible count를 일치시킨다. 같은직업이어도 dealer/support가 다르면 가능,8인은 각4인파티에서 검사해 반대파티 유효배치를 보존한다. 역할 무시한 공격대 전체 class총량 제한을 만들지 않는다.
- **변경 자기제외:** 본인의 교체대상 참가/자리·해당 교체대상 점유만 제외한 가상 구성으로 평가한다. 같은room 점유 전체 무시 금지, 다른방 점유/완료 차단, 실패/경쟁 시 기존캐릭터 참가·예약/다른T 보존이다.
[#26 전체4번째 Backend · 최신범위 수용/기존 검증 차이 회신](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381295804) 게시·전문/실제 순번 확인 완료. 다음 담당 Backend 보완 제안2(schema/예시) 작성·정적검증·게시 완료→구체 소비차이 해소·합의→구현이며, 이번 댓글 자체는 새 DTO 최종합의가 아니다.

- **현재 설계:** [통합 자격 설계](../features/recruitment/participation/eligibility-design.md)에서 필요에 따라 공통판정→문맥/쓰기→후보읽기→직접시험/인계로 작업을 분류했다. [보완 계약2](../features/recruitment/participation/candidate-contract.md)는 신규 admission-character-candidates GET의 apply/change_character·서버도출actor·지원역할/ROLE_NOT_SUPPORTED·역할별 전투력/보존 성공본·제외집계·snapshot/페이지를 닫았다. 8인 변경은 원파티 우선→반대파티, 정확한 교체Assignment/lease만 자기제외하는 설계다. 기존쓰기DTO/원ACK 유지, 실행176/DB0031은 미변경이다.
설계 source `77be3a955cb8e3a91c5a2cf212c45d622e03aba0` commit/push·원격 SHA 일치 확인 뒤 [#26 전체5번째 Backend · 통합 자격 기획/설계·보완 계약2](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381680561) 게시·전문/전체 순번을 재조회했다. 다음 담당 Flutter 구체 소비차이 검토, Backend 차이 반영/합의 후 구현이며 계약 확정·새 API 실행/실인수 완료가 아니다.

- **정적 검증:** 작성 예시21개/잘못된 응답16개·snapshot 혼합 거절. 실제 evaluator/HTTP·DB 검증이 아니며 기존25PASS와 합산하지 않는다. 기본 실행 OpenAPI에 신규 GET을 추가하지 않았다.
- **다음 Flutter:** 보완 제안2의 intent/actor·역할/전투력/집계/페이지와 8인변경·사유 우선순위의 구체 소비차이를 검토한다. 기존 전체시험/실서버 인수 요청은 아니다.
- **다음 Backend:** 제안의 소비차이 반영/합의 후 공통검증/변경원자성→후보GET→직접회귀·실행계약 검증/정확 source 게시를 수행한다. 계약2는 아직 미합의이므로 새 runtime API/역할제한을 구현하지 않는다.
- **실제 개발:** 기존 API67322372…/DB0031 유지·API/DB healthy/health200 읽기 확인, 교체/이행·실회원쓰기/키변경 없음. 합성 tmpfs DB/runner/internal network 정리 완료. 새 구성검사 실제 반영은 별도 승인 후, 정상로그인/실회원·기기 인수는 반영 뒤다.
- **최근 수신:** #24 전체6 Flutter0d6d960b의 검색회복 연결/126mock, 전체7 생성자 검색제외 실제정상·추가참가자 미확인, #13 전체144 Flutter63b77872 신청카드 기본상세 수정/117mock 보고수신. 최초 승인오류 원인은 code/request_id 없어 미확정이다. 이번 요청은 #26에 직접 대응하며 독립 인수/미완료를 폐기하지 않는다.

문서 정리 브랜치에 모집 현황/회신을 계속 쌓고 기능 구현은 임시 작업트리에서 진행한 분리는 잘못된 작업 흐름이었다. 사용자 지시로 기존 모집 브랜치에 문서 정리/최신 기록을 이력 보존 병합하고 본 프로젝트의 checkout을 모집 브랜치로 복귀했다. 이전 분리/미병합 기록은 DEV_LOG의 당시 이력이며 현재 실행 지침이 아니다.

사용자 지정 테스트용 인증 설정은 실제 장비 인증 성공과 구분한다. 다음 사용자 확인이 필요하면 앱 목록 새로고침·활동/대표 선택이며 비공개 실행 근거는 DEV_LOG에 보존한다. 자료/키/DB초기화·개발 fixture 재적용은 수행하지 않는다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

[전체 기능 안내](../README.md)와 [문서 대응표](../engineering/documentation/README.md)의 정리 결과를 현재 모집 브랜치에서 사용한다. 다음 실행은 #26 전체3/4의 확정 범위와 검증 차이를 바탕으로 작성한 보완 계약2의 소비차이를 반영·합의한 뒤 구현하는 것이다. 문서 파일 편집/협업 수신이라는 이유로 다른 브랜치로 전환하지 않는다. 새 API 합의·구현·개발 반영 상태는 위 구분을 유지한다.
