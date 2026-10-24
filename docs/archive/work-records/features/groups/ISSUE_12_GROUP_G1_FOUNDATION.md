> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [discovery](../../../../features/groups/discovery/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 그룹 G1 내부 선행 구현

2026-10-17. [G1 명세](ISSUE_12_GROUP_G1_SPEC.md)·[첫 번째 Backend 명세 댓글](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232074318)이 기준이다. 사용자가 네이티브 회신 전 독립 구현 가능한 기초 작업을 승인했다. 작업 브랜치는 기존 `feat/raid-services`다.

## 구현 범위

- `app/groups/models.py`: groups, group_memberships, group_directory_head. group+user unique로 앱 회원당 그룹 자리1개를 보장한다. 그룹장의membership은 같은group을 참조하는 deferred composite FK로 확인한다. 별도role 열 없이 leader_membership_id에서 역할을 계산한다.
- `app/groups/commands.py`: 내부 strict 생성/이름수정 명령. 생성은 현재 등록/캐릭터 UUID와 예상 등록/소유/roster/lifecycle revision을 받는다. 이름은원문제어문자·줄구분자를거부하고trim후1~20자다. 생략은기본명, null은거부한다. 새 HTTP 계약으로 노출한 DTO는 아니다.
- `app/groups/service.py`: 현재 세션/소유/사용자격·CAS를 확인한 원자 생성, 회원 전용 내부 조회/이름 변경, 최소 표시 projection. 기존 reserve/commit_result·전역 게임 변경 락·lease/generation을 재사용한다. 네트워크/provider/개인키 접근은 없다.
- 그룹+생성자membership+directory revision+멱등성공은 하나의 transaction으로 commit하며 실패는 전부 rollback한다. 이름 변경은 현재group장/예상group/member revision을 확인하고 실제 변경만 revision을 올린다. 동일값도 권한/CAS를 먼저 확인한다.
- 내부 명령 scope는 `group-core-create`, `group-core-rename`이다. 성공 replay는 현재 session·group·active membership을 다시 확인하지만 과거 ACK를 현재role/permissions로 바꾸지 않는다. 실제 HTTP adapter의 최종 명령/응답 연결은 계약 검토 후 별도다.
- 대표의 canonical UUID와 당시에 확인한 표시 snapshot은 그룹에 별도 보존한다. 캐릭터 소유상실/사용불가 시needs_update지만 그룹membership·그룹장 권한을 자동 삭제하지 않는다. 사용자대표와 자동 동기화하지 않고 새이름/새ID에서 자료를 이어받지 않는다. projection은 앱user UUID·개인키·원정대 전체 정보를 포함하지 않는다.

## 미확정 정책을 분리한 방식

생성 내부 함수는 `policy=` 인자를 필수로 요구한다. 활동선택 필수 여부·제품 인원 제한 등을 검사하는 동기 DB 정책을 명시적으로 주입해야 하며 기본 무제한/비필수 정책을 제공하지 않는다. 이 hook은 정상 소유/등록/usable/revision 검사를 대체하지 않는다. 테스트에서만 명시적으로 허용하는 정책을 주입했다. callback은 허용 시None을 반환하고 거부 시 예외를 발생시키며 네트워크 호출을 하지 않는다.

공개 조회의 인증 여부, 활동선택 필수 조건, 50/50 제한값을 이 구현으로 확정하지 않았다. HTTP router를 만들거나 app.main에 연결하지 않았고 OpenAPI 원본도 변경하지 않았다. 공개검색/목록 cursor·HTTP DTO/오류 연결은 계약 검토 후 이어간다. G2 초대/신청/코드/차단, G3 이전/탈퇴/해산과 파티 연계도 미구현이다.

## DB·검증 상태

`0012_group_foundation`은 새3테이블/제약과 directory head1행만 생성한다. 기존자료 복사·초기화는 없다. **파일 작성과 격리PostgreSQL 적용/모델 일치 검증만 수행하며 개발DB에는 미적용**이다. 현재 개발DB0011·기존API를 유지한다. downgrade로 그룹자료를 폐기하지 않고 이후 API이미지 복구/자료보존과 수정migration을 사용한다.

관련 테스트는 내부 생성·그룹장동일그룹FK·회원유일성·정책필수주입·이름/기본명이상·각revision·소유/claim/생명주기·현재회원/private차단·정정/no-op/replay·동시경쟁·transaction rollback·표시snapshot/권한보존을 포함한다. 최종 관련118PASS/54.32초·기존Starlette/AnyIO경고1개다. 최초기초검증은30PASS/2FAIL이었고기존인증예외AuthError를하위GameError로잘못기대한테스트만수정했다. 최종실행은기초31개/모델일치1개와대표·주간회귀를포함한다. 구현SHA `e5e97c8a4db541ece7d37b9879f46fe0c88f20f2`을push·원격확인하고 [#12 두 번째 Backend 내부구현 회신](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232311355)으로인계했다. dev/main미병합이다. 테스트의 멤버추가/종료는 후속상태를 만든 fixture이며 G2/G3 실제명령 구현 결과로 보고하지 않는다.

## 다음 구간

최신 #12 회신을 확인하고 공개 인증·활동선택 조건/DTO 충돌을 정리한 뒤 G1 HTTP adapter·목록/cursor·OpenAPI와 개발DB 적용/실행반영을 진행한다. 50/50 최종값 미확정 때문에 나머지 기초를 대기하지 않는다. 현재 결과는 내부 선행 구현이며 Flutter가 호출 가능한 API 완료나 실기기 통과가 아니다.


## 최신 후속

위50/50·활동필수 여부의 미확정 설명은 당시 선행구현 경계다. 최신은 [G1 명세](ISSUE_12_GROUP_G1_SPEC.md)와 [공통한도 계약](ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)의 계정별기본15/5/10·현재활동선택필수·원인별제한이다. [L0 내부기초](ISSUE_12_MEMBER_LIMITS_FOUNDATION.md)에서 생성transaction의 사용량head 갱신을 연결했다. 최종 생성guard/HTTP는 다음 구간이며 과거 무제한 정책을 현재 확정으로 쓰지 않는다.
