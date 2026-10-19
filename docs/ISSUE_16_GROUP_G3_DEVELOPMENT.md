# G3 그룹 관리 구현·인계

2026-10-19 / Backend / `feat/group-management` / [Issue16](https://github.com/heo0328/lostparty-backend/issues/16).

구현·계약 SHA `332a8ab9697ca1a8e0d2ebcc147169c54ce9161c`, push·원격 SHA 일치 확인 완료. [전체4번째 Backend — 구현·검증·게시 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6258994902). dev는 [PR20](https://github.com/heo0328/lostparty-backend/pull/20)의 bb144e0로 통합·원격 확인했고 main은 미통합이다. 완료 feat/group-management는 로컬/원격 정리했으며 [전체6번째 Backend 통합 결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673)와 후행 문서 커밋을 기능 계약 SHA와 구분한다.

## 제공 범위

[명세](ISSUE_16_GROUP_G3_SPEC.md)와 [실행 계약](../openapi/openapi.yaml)의 관리 GET `/v1/groups/{group_id}/management`, 그룹장 이전 POST `/v1/groups/{group_id}/leadership-transfer`, 일반 탈퇴 POST `/v1/groups/{group_id}/leave`를 제공한다. 기존 G1/G2 경로·DTO·정책 객체는 그대로다. 소비 합의를 추정한 것이 아니라 원본 #12에서 Backend에 맡긴 경로/DTO 설계와 사용자 G3 착수·계속 진행 승인 범위로 구현했다. 이전 기록에서 소비 확인을 전체 구현의 선행조건으로 둔 부분은 정정한다.

그룹장은 현재 유효 멤버에게 즉시 이전하고 일반 멤버로 남는다. 새 그룹장 유효 정원이 현재 인원을 수용해야 한다. 그룹 대표 기록·코드/쿨타임·가입 수는 보존하고 현재 역할 권한은 즉시 바뀐다. 일반 탈퇴는 과거 membership을 보존하며 발신 pending 초대만 cancelled/expired로 종료하고 본인 사용량·group/member/directory revision을 함께 갱신한다. 캐릭터 과거 소유/활동 상실을 본인 관계 정리의 거부 사유로 삼지 않는다.

두 명령은 group/member CAS와 최소 ACK·멱등 lease/generation을 사용한다. 같은 key/body의 과거 ACK는 탈퇴/재가입 뒤에도 복구하며 새 membership을 종료시키거나 이전 권한을 복원하지 않는다. 현재 세션/회원 상태는 계속 검사한다. ACK 뒤 현재 상태는 GET으로 확인한다. POST 성공·revision/head/발신 초대 종료/ACK 저장은 한 transaction이며 실패하면 전부 rollback한다.

조건부 해산·추방·대표 변경 쓰기와 실제 방 후처리는 제공하지 않는다. 활성 모집 원본을 0건으로 가정하지 않고 관리 GET의 disband 불가 reason으로 안내한다. 해산은 #13 원본 후속이며 #16을 기능 전체 완료로 닫지 않는다.

## 실행 검증

- 최신 API 이미지 반영 후 격리 PostgreSQL/모의 Google 인증 기반 HTTP **148 PASS / 55.73초**. G3 내부23개+HTTP22개, 기존 G1/G2·그룹 기반·회원 한도103개다. 이전126/19 결과와 중복 합산하지 않는다. 기존 Starlette/AnyIO deprecation 경고1개.
- 첫 실행147 PASS/1 FAIL은 테스트 이미지에 없는 git 명령으로 이전 계약을 읽은 시험 구성 문제였다. 호스트에서 이전 path/DTO 전체 불변을 비교하고, 이미지에 계약 파일을 포함해 전체 실행 계약과 비교하도록 수정한 최종 이미지에서148 PASS다.
- 역할·타 그룹/종료/비활성 대상·정원 미달/정확한도·개인초과 회복·캐릭터 자격 상실, 양쪽 revision/대표/코드 보존, 발신 초대 종료/사용량, 재가입 원ACK/세션 철회/24h만료/멱등 lease를 검증했다. 동시 이전·탈퇴와 초대수락·ACK실패rollback·cursor무효화·GET SQL쓰기0·strict 입력/헤더/query·401/Bearer/no-store도 포함한다.
- `docker compose up -d --build --wait --wait-timeout 180`으로 기존 개발 API8000에 반영했다. `python3 scripts/check_openapi.py`는 전체 일치 PASS다. 기존 path와 component schema 전체가 변경 전 계약과 같은 것도 확인했다.
- 실제 로컬 HTTP health200, 신규3동작의 인증 없는401/ACCESS_INVALID·Bearer·no-store 확인. 실제 개발 회원의 이전/탈퇴 쓰기는 실행하지 않았다.
- DB는 전후 `0016_record_timestamps`이며 migration/기존자료 초기화·키 변경은 없다. 격리 테스트 DB만 종료한다. 운영 배포가 아니다.

재현 명령(테스트 DB는 개발 DB와 별도):

```bash
docker compose -f compose.test.yaml up -d --wait test-db
docker compose -f compose.test.yaml build tests
docker compose -f compose.test.yaml run --rm tests pytest -q -p no:cacheprovider tests/test_group_management_http.py tests/test_group_management.py tests/test_group_admissions.py tests/test_groups_http.py tests/test_group_foundation.py tests/test_member_limits.py
python3 scripts/check_openapi.py
```

전체 Backend 테스트·실provider·Flutter 연결·실기기는 이번 검증 범위가 아니다. Flutter 기존 V2 우선 작업을 중단시키지 않으며, 그룹 연결 구간에서 신규 관리 GET/최소 ACK·동일 key/body 복구와 현재 GET 재조회만 연계한다. 구현 SHA·push 상태와 결과 회신 링크는 Issue16 및 NEXT_WORK/DEV_LOG를 따른다.
