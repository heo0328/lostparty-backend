# 다음 실행

2026-10-24 / **feat/raid-recruitment** / [#13](https://github.com/heo0328/lostparty-backend/issues/13), [#22](https://github.com/heo0328/lostparty-backend/issues/22), [#23](https://github.com/heo0328/lostparty-backend/issues/23) OPEN.

## 현재 — #24/#25 개발 API·DB0031 반영 완료

2026-10-24 사용자 진행 지시에 따라 실제 개발 서버를176경로·DB0031로 반영했다. 구현 source `15e143aeb9f3105a1b8a5816051e0e837726892c` / feat/raid-recruitment, [실행 결과/보존 근거](../ISSUE_24_25_DEVELOPMENT_ROLLOUT.md). 비공개 백업 복원 리허설·제한 LOGIN readiness·실제 이행·API/worker 교체 후 기존105개 업무 표의 모든 행/열/기록 시각·키·시퀀스 보존을 확인했다.106→108표603행, API/DB 두 컨테이너 healthy·DB 재생성 없음. 새 검색과 메뉴/명령·opt-in reader가 실제 개발 API에 반영됐다.

- 다음 Flutter: 구현 인계 source/176계약으로 직접 연결·자동 검증을 마치고, 정상 로그인으로 선택T 검색·새 메뉴/명령·profile/본인 종료 기록을 확인해 #24/#25에 회신한다. 실회원 HTTP/기기 인수는 미확인이며 기존 전체 시험 반복이나 계약 재수용을 요구하지 않는다.
- 다음 Backend: 네이티브의 재현 가능한 계약/동작 차이에 대응한다. [#24 전체5번째 Backend · 개발 반영 완료](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690)·[#25 전체7번째 Backend · 개발 반영 완료](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996) 게시·전문/실제 전체 순번 확인 완료. 다음 담당 Flutter, 직접 연결·정상 로그인 인수 대기다. 원본 #13 전체140 IF-001 회신 유지·추가 정책 수용 대기 없음.
- 실제 이번 검증:176/116 OpenAPI 전체 일치, health200·공개 C/N 검색2·새 경로 인증 거절4/no-store. 고유38 합성 시험은 직전 구현 근거이고 실제 회원 명령 성공으로 표시하지 않는다. 임시 복원/runner/network 정리 완료.
- IF-001 앱 비활성·기존 endpoint/권한/자료/원 pending/24h ACK 보존, 복구 UX는 미승인 제안. #13/#22/#23/#24/#25 OPEN·dev/main 병합/AWS 운영 배포/자료 삭제 없음.

아래는 이전 구간 기록이며 현재 실행/다음 담당은 위 기준이 우선한다.

## 개발 테스트 자료 보조 작업

사용자 지정 미인증 등록 원정대1건을 직접 요청에 따라 테스트용 verified/owned로 설정하고 커밋 후13캐릭터·감사 이력을 읽기 검증했다. 실제 장비 인증 성공과 구분한다. 활동/대표는 미설정이며 다음 사용자 확인은 앱의 원정대 목록 새로고침·활동/대표 선택이다. 개인정보 없는 실행/비공개 백업 근거는 [DEV_LOG](DEV_LOG.md)의 2026-10-24 테스트 인증 항목을 따른다. #24/#25 다음 담당/미완료 범위는 그대로다.

## 기존 인계·별도 후속

- 완료정정/보관 소비8bbcfc8: [Backend129](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360251618)·[개발안내](../ISSUE_13_COMPLETION_CORRECTION_DEVELOPMENT.md). 본인 manual/party 완료근거 정정과 실제 완료 기록/참가 복원은 구분한다. Flutter A/B 연결결과는133/134번째로 수신했고 실제인수는 별도이며 기존 pending/원ACK를 새명령에 강제 캐스팅하지 않는다.
- F6-C 소비2940824: [Backend121](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356827586), [Flutter122](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6357361150) 연결/mock 보고수신. F1~F6 전체 정상회원·기기 인수/성능과 모집관리 pending 앱종료 후 영속복구는 미완료다. 과거 시험/보고 상세는 [DEV_LOG](DEV_LOG.md)를 따른다.
- #19 통계, #17 생명주기, #18 활동정책 등 독립후속은 [추적표](ISSUE_TRACKER.md)를 따른다. 이번구간으로 범위를 확대하지 않는다.
- Issue21은 내용전달/문서정리로 종료했고 추가회신·수용대기가 없다. 승인된 후속에 [품질/UX 기준](../DEVELOPMENT_QUALITY_AND_UX_STANDARD.md)을 적용한다. 릴리즈/안정 확인 후 배포main/태그 기준의 별도 최적화 검토시점 안내는 남아 있다.
- 재기동은 compose.yaml+compose.two-cycle.yaml/two-cycle factory/DB0031이다. 기본0023앱·구worker 혼용, 과거snapshot 덮어쓰기/초기화, dev/main merge·운영배포는 이번 범위가 아니다.
