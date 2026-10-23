# 비활성 보존 기능

## IF-001 — 이번주 미완료 종료·같은 주차 재개

2026-10-24 / 사용자 최종 결정 전달: [#13 전체139번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6370006371), Flutter `ddf4bfd0` commit/push 보고.

활성 사용자 기능에서 `close_weekly`와 같은 주차 `weekly_resume`를 제외한다. 단일/다일 일정 모두 앱의 신규 진입·preview·신규 명령·`include_resume_display=true` opt-in을 비활성화했다는 보고이며 Backend에서 독립 재현한 결과는 아니다. 일반 detail/plan·일정 제안/응답·완료·개인완료후탈퇴/완료정정, 다음주 함께하기/다음주 `reopen`은 유지한다. #25 `recover_leadership`은 별도 기능이며 복구 UX는 제품 승인 전 제안이다.

1차는 비활성 보존이다. 기존 endpoint·서버 권한·DTO/reader·stopped/재개제안/완료·감사 이력은 삭제하거나 자동 변환하지 않는다. 구버전 및 기존 pending의 원 method/path/body/key/token·원 효과와 최대24h 원 ACK 복구를 유지한다. 서버 이력이 있다는 이유로 앱 진입을 재활성화하지 않는다. 새 조회 profile도 retained/stopped 자료의 표시를 허용하되 비활성 기능의 앱 버튼 노출 근거로 삼지 않는다.

이 결정은 DB 변경/자료 삭제·endpoint 폐기·기존 pending 차단 지시가 아니다. Flutter 보고119 mock PASS/분석0과 실제 서버·기기 인수를 구분한다.
