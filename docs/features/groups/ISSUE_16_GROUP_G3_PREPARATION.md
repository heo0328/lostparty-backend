# 그룹 G3 작업 준비

2026-10-18. 담당 Backend / 작업 브랜치 `feat/group-management` / 준비 기준 `49cd8cc1f706893ff5d53fa426d2af1d95ed018d`. 이 문서는 구현 전 범위·의존성 점검이며 확정 API 계약이 아니다.

## 확인한 요구와 현재 상태

- [Issue16 본문](https://github.com/heo0328/lostparty-backend/issues/16)과 전체 댓글 0개, 원본 [Issue12 본문](https://github.com/heo0328/lostparty-backend/issues/12)과 전체 댓글 16개를 조회했다. #12 최신은 [전체16번째 Backend 주제 분리](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6249414405)이며 새 계약 정정은 없다.
- [G1 개발 안내](ISSUE_12_GROUP_G1_DEVELOPMENT.md), [G2 명세](ISSUE_12_GROUP_G2_SPEC.md), [회원 한도 계약](ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)과 현재 구현을 기준으로 이어간다. G1/G2 Flutter 연결은 #12의 별도 후속이다.
- 기존 API8000·DB0016에서 개발을 계속한다. 준비 단계에서는 기능 코드·OpenAPI·DB·서버 설정을 변경하지 않았다.

## 다음 명세의 우선 범위

| 동작 | 확정된 제품 규칙 | 명세에서 구체화할 내용 |
|---|---|---|
| 그룹장 이전 | 현재 유효 멤버에게 즉시 이전. 상대 수락·대기·쿨다운 없음. 이전자는 일반 멤버로 남음 | 대상 membership 검증, 자기 자신/타 그룹/종료 관계 거절, CAS·원자 변경·원성공 응답 복구 |
| 일반 멤버 탈퇴 | 현재 본인 membership 종료. 그룹장은 이전 또는 조건부 해산 선행 | 종료 ACK, 본인 가입 수 회복, 발신 초대 종료, 재가입과 과거 명령의 분리 |
| 조건부 해산 | 본인 1인·pending 없음·실제 활성 그룹전용 모집 없음 등 원본 검사 | 현재 모집 원본 부재를 0건으로 처리하지 않는 거절 경계. 모집 연계 허용은 #13 원본 후속 |

멤버 권한과 캐릭터 소유/활동 자격을 구분한다. 기존 캐릭터의 소유 상실이나 활동 해제로 이전·본인 관계 정리를 차단하지 않는다. 이전 후에도 그룹 대표 기록은 유지하며 기존 대표 자격 계산으로 `needs_update`를 제공한다.

그룹 정원은 새 그룹장의 유효 한도로 다시 평가하며 현재 인원을 수용해야 한다(기존 한도 계약 6절). 초과 상황에서도 조회·탈퇴·이전 등 회복 경로를 유지하는 기존 정책을 따른다. 가입 수가 늘지 않는 이전에 신규 가입 한도를 적용하지 않는다. 대상 회원 활성 상태·한도 변경과 이전의 경쟁도 최종 transaction에서 다룬다.

## 현재 코드와 연결 지점

| 파일 | 현재 근거와 다음 검토 |
|---|---|
| `app/groups/models.py` | 그룹장 기준은 `leader_membership_id` 하나다. 같은 그룹 membership 복합 FK, 종료 시각, 현재 membership 부분 unique가 있다. 이중 role 저장이나 이력 덮어쓰기를 추가하지 않는다 |
| `app/groups/service.py` | 현재 그룹/멤버 검증·대표 상태·directory revision을 재사용한다. 그룹장 이전 전후 대표 snapshot은 유지한다 |
| `app/groups/http_service.py`, `schemas.py`, `router.py` | 현재 GroupDetail·멤버 목록·정원·권한 응답과 명령 연결을 검토한다. G3 권한 필드 추가는 strict DTO 소비 영향을 명세에 먼저 제시한다 |
| `app/groups/admissions.py`, `admission_core.py` | 현재 역할/CAS·관계 종료·명령 실행 및 replay 검사를 재사용한다. 탈퇴한 발신자의 초대는 이미 논리 cancelled로 계산한다. 실제 탈퇴와 종료 기록을 원자적으로 연결할 범위를 정한다 |
| `app/member_limits/service.py` | 실제 가입 수는 현재 membership으로 계산한다. 탈퇴와 usage head 갱신을 같은 transaction에 넣고 재전송으로 중복 증가시키지 않는다 |
| `app/game_accounts/support.py` | 세션·현재 회원 검증, `game-mutations-v1` 쓰기 락, 멱등 lease/generation·성공 ACK를 재사용한다 |
| `tests/test_groups_http.py`, `test_group_admissions.py`, `test_group_foundation.py` | 현재 G1/G2 fixture와 권한·관계·경합 검증을 재사용할 후보다. G3 시험은 구현 단계에서 추가한다 |

기존 모델만으로 가능한 부분을 먼저 설계한다. migration 필요 여부는 최종 ACK/감사 저장 설계 후 판단하며, 준비 단계에서 새 테이블을 전제하지 않는다.

## 명세 작성 시 반드시 해결할 기술 경계

1. 쓰기 endpoint·strict 요청 DTO·200 응답 예시·필수 nullable·기존 오류 envelope를 제시한다. 새 경로·오류명은 아직 확정하지 않는다.
2. 그룹/멤버 목록 revision·행위자 및 대상 membership revision의 CAS를 정한다. 이전 시 두 역할과 그룹장 표시, 탈퇴 시 멤버 수·directory/usage head와 목록 cursor 변경을 원자 반영한다.
3. 기존 replay 검사는 현재 membership을 요구한다. **탈퇴 성공 뒤에는 이 조건을 그대로 쓰면 원성공 복구가 막힌다.** 세션/행위자·원래 종료 membership·원명령에 한정한 최소 ACK 복구를 설계하고 private 그룹 자료를 재노출하지 않는다. 재가입한 새 membership을 과거 탈퇴 재전송으로 종료시키지 않는다.
4. 이전 성공 ACK는 현재 그룹장 권한 증거가 아니다. 재전송 시 현재 역할과 원성공 기록의 차이를 명시하고 현재 상태는 GET으로 확인한다.
5. 동시 이전/탈퇴/가입/한도 변경·발신 초대 수락 경합, 다른 본문 멱등 충돌·응답 유실·부분 실패 rollback을 시험 대상으로 정한다.
6. 실방 원본 없이 해산을 허용하지 않는다. 미지원/원본 확인 불가를 안정적인 오류·행위 안내로 표현하는 안을 명세로 제시한다. GET에 정리 쓰기나 외부 게임 API 호출을 넣지 않는다.

## 분리해서 확인할 정책

추방 권한/대상·추방과 재가입/차단의 관계, 대표 변경 권한/선택 범위는 현재 요구만으로 상세 확정되지 않았다. 현재 그룹장의 즉시 이전·일반 탈퇴 명세를 막지 않으며, 기존 원문과 대조 후 필요한 질문만 #16에서 확인한다. 자동 차단·자동 대표 교체·새 회원 프로필을 임의 추가하지 않는다.

## 다음 실행과 완료 기준

다음 Backend 실행은 이 준비를 바탕으로 G3 명세안을 작성하여 #16에 게시하는 것이다. 구현 전 검토 요청과 구현 테스트 요청을 구분한다. 명세 게시 후 확정 요구에 해당하는 범위를 구현·표적 검증하고, 필요한 계약 합의를 반영한다. 구현 인계는 커밋·push·원격 확인 후 시행하며 기존 G1/G2 연결을 반복 시험하도록 요구하지 않는다.

이번 준비의 완료 기준은 요구 출처·변경 지점·기술 경계·정책 미확정·다음 담당이 기록되는 것이다. 현재는 준비 완료/상세 명세 미작성/서버 미구현이며 Flutter 답변 대기 상태가 아니다. 내부 준비만으로 변화 없는 Issue 댓글을 추가하지 않는다.


후행 상태: [G3 API 명세 제안](ISSUE_16_GROUP_G3_SPEC.md)을 작성했다. 상세 계약·게시 결과와 다음 담당은 NEXT_WORK/DEV_LOG를 따른다.
