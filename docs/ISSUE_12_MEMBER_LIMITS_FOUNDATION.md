# 계정별 한도 L0 내부기초

2026-10-17. 기준: [최신 제한 계약](ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md), [#12 아홉 번째 확정](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572). 기존 `feat/raid-services`의 그룹 기초를 이어간다.

- `app/member_limits/models.py`와 migration `0013_member_usage_limits`: 계정별 한도·사용량revision head·변경 감사3테이블. 기본15/5/10, PostgreSQL 정수0이상, 감사는 계정+한도revision unique다. 기존회원 일괄보정/자료복사/삭제는 없다. downgrade는 자료삭제 대신 거부한다.
- `service.get(principal)`: 현재 세션을 기존 authorize로 확인한 RR 내부 조회. 행이 없어도 기본값/revision1을 반환하고 쓰지 않는다. 가입그룹수는 현재 membership과 미종료group을 실제 집계한다. 아직 없는 모집 원장은 null/unavailable로 구별한다. HTTP GET을 제공한 것은 아니다.
- `record_group_membership_change`: 기존 전역 game-mutations 락을 사용하며 관계 변경과 같은transaction에서 기본행/usage head를 만든다. 기존 G1 내부 생성에 연결했다. replay/이름수정/GET은 사용량revision을 올리지 않는다. G2/G3의 실제 종료/재가입 명령은 후속 연결이 필요하다.
- `change_limits`: 서버내부 호출경계. 명시적인 신뢰 서버 권한검사callback을 필수로 받고 같은 전역락/대상user lock·CAS·감사로 처리한다. 기본 무권한 허용·공개운영자API·일반회원 한도PUT·CLI를 만들지 않았다. 실제 권한서비스/운영도구 연결은 미구현이다. 테스트만 명시적 test authority를 사용한다.
- 실제 한도변경만 limits_revision/감사를 올리고 no-op는 보존한다. 한도감소가 기존 그룹/회원관계를 삭제하지 않는다. 가입그룹 초과는 조회의 원인으로 표시하며 기존 그룹 운영을 막지 않는다.

L0는 저장·조회·버전·권한경계다. 현재 G1 생성은 기존의 필수policy 주입을 유지하며 최종 활동선택/한도증가 guard/예상revision HTTP 연결은 G1 다음 구간이다. 실제 레이드 방의 초과 제한/회복 명령과 통계집계는 구현하지 않았다. 확정된 원인별 영향은 계약에서 따르며 과거 광범위 상속안을 구현하지 않는다.

검증은 격리 PostgreSQL에만0013을 적용한다. 개발DB는0011·기존 포트8000/API를 유지한다. 새 이미지를 빌드했어도 실행 컨테이너 반영/개발DB 적용을 뜻하지 않는다. OpenAPI는 기존 전체 객체 불변을 확인한다. 세부 PASS·오류 수정/커밋·게시 링크는 DEV_LOG/NEXT_WORK의 해당 구간을 따른다.

다음: 본인한도GET·생성시 현재활동/한도/CAS·공개/회원목록/검색/cursor·OpenAPI를 G1 단위로 완성한 뒤 로컬반영/Flutter 연동 인계한다. 주간 통계는 [별도 선행 설계](ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)로 진행한다.
