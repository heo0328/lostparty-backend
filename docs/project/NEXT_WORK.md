# 다음 실행

2026-10-19. 완료 G3 구간을 [PR #20](https://github.com/heo0328/lostparty-backend/pull/20)의 **bb144e0**로 dev에 통합·원격 확인했다. main은77a1fe5로 유지한다. feat/group-management는 로컬·원격에서 정리했고 기존332a8ab/349fb79는 dev 이력과 모집 브랜치에 보존했다. [#16 전체6번째 Backend 통합 결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673).

## 다음 작업 — 기존 모집 브랜치에서 #13 F3

- 기존 **feat/raid-recruitment**의 c41fd03까지 F1/F2-A/F2-B 구현·검증·문서가 로컬 커밋되어 있다. 미push/원격추적없음이며 이번 G3 PR에는 포함하지 않았다. 새 브랜치를 다시 만들거나 기존 모집 커밋을 재작성하지 않는다. dev 통합 기록을 merge로 반영한 뒤 해당 브랜치에서 이어간다.
- [#13 전체15번째 Backend F2-B](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260695606): 후보 HTTP18동작/격리101PASS, main router·원본OpenAPI·개발DB/이미지에는 미반영이다. 다음은 F3 최종계약·DB0017+0018/사용량source·앱/원본OpenAPI·개발이미지의 일관된 반영·검증이다. 원격 게시 확인 전 신규 API 소비 테스트를 요청하지 않는다.
- [#13 전체16번째 Flutter 접수](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260778487): 후보보고 접수/실서버 인수 아님. #15 D1~D4 dev반영·마감, 분쟁 실기기 인수는 사용자 판단 보류다. 현재 Flutter 우선은 로그인 후 내 계정 화면 재구성 결함 대응 문서화이며 기능 수정/실기기 성공으로 확대하지 않는다.
- Q1 미정·주차초과 일정/Q2 최소전투력 수치·근거/Q3 그룹탈퇴 후 방관계는 미확정이다. 초기 공개/유한회차 부분집합을 영구 정책으로 확정하거나 미지원 분기를 임의 활성화하지 않는다.

## G3 완료 구간과 미완료 후속

관리 조회·그룹장 이전·일반 탈퇴는 Backend/dev 통합 완료다. 통합 직전 G3 내부/HTTP45PASS/37.95초 및 실행OpenAPI일치, 기존148PASS와 중복이다. 신규 개발회원 쓰기/Flutter 연결/실기기·운영 인수는 별도다.

조건부 해산은 실제 활성 그룹모집 원본 검사 후 #16에서 이어간다. #13 공개방 후보는 그룹방 source 완료가 아니므로 disband의 GROUP_RECRUITMENT_STATE_UNAVAILABLE을 유지한다. 추방·대표 변경·실제방 후처리도 후속이며 #16은 열린 상태다. 후속 착수 시 최신 dev에서 그룹 목적 브랜치를 만들되 지금은 새 브랜치를 만들지 않는다.

개발 API8000/DB0016·자료/키는 그대로다. main 통합·운영 배포·DB 초기화/이관·자료 삭제는 수행하지 않았다. 이번에 사용한 격리 테스트DB만 중지했다. [기능지도](AI_CONTEXT.md)·[추적표](ISSUE_TRACKER.md)·[이력](DEV_LOG.md)을 함께 확인한다.
