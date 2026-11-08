# Issue17 Backend 잔여 범위 감사

2026-11-08 / 사용자 요청: Issue를 확인해 Native 대기 외 Backend 미완료가 있는지 확인. 기준 구현4c37c2b·문서7aea6b7·실제 로컬 image4ac36fdb/DB0036이다. 기존 배포 소스를 변경하지 않고 읽기 대조와 격리 진단만 수행했다.

## 결론

Native 전체20번째는 추가 Backend 변경/반복 시험 요청·제품 미결정이 없다고 회신했다. 그러나 합의한 주차 전환의 전체 완료 경계는 Backend에 별도로 남아 있다. 앞선 ‘Backend 추가 코드/시험 대기 없음’ 판정을 이 경계에 한해 정정한다. 구현/계약 게시·로컬 반영 자체와 기존7PASS 결과는 유지하며, 이를 전체 후속 경계 완료로 확대하지 않는다.

## 확인한 공백

### 전체 완료 후 완료 이력을 다음주 선택으로 사용하는 fallback

- 근거: [Backend 전체8번째 합의](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719925630)의 active0이면 현재 선택 없음·완료 이력을 신규 자격 근거로 사용하지 않음·다음주 신규 발급은 대상 주차에 명시된 선택 검증 원칙.
- 코드: `existing_participation.selection`은 `chosen_rows = active or owned[-1:]`, `cycle_lifecycle.qualify`도 `selected_rows=active or owned[-1:]`로 완료 이력을 현재 선택으로 반환한다. `cycle_lifecycle.source`가 이를 다음주 opening/continuation에 전달하고, 두 prepare는 명시 cid가 없으면 이 선택을 유지한다.
- 격리 재현: 두 항목 중 index1을 옛 캐릭터로 완료→index0의 남은 참가만 새 캐릭터로 교체→index0 완료. `roster_participation.member`는 active=[]·current_character=null·옛/새 두 완료P를 반환하지만 `life.source(...,validate=True)`의 selected는 옛 완료 캐릭터가 된다.
- 진단 실행: `lostparty-check-5cff42a6ffd3`,1건/34.70초, 관찰 assertion 통과. 이것은 **원치 않는 fallback의 재현 성공**이며 정상 동작 회귀 통과가 아니다. 일회용 진단 fixture는 확인 후 제거했고 재현 단계/결과를 여기 기록한다. 기존 Starlette 경고1건, 격리 컨테이너/네트워크 정리 완료.
- 한계: 이 감사는 source 선택과 opening/continuation의 정적 연결을 확인했다. 신규 다음주 가입까지 실제 실행하거나 이미 가입된 다음주 자료를 변경한 것은 아니다. 명시 새 선택에 대한 현재 소유/활동/주간 점유 재검증은 기존 코드에 있다. 즉 신규 자격 검사를 우회했다는 결론은 아니다.
- 남은 Backend: 현재 참가/관리 권한의 증거와 다음주 신규 선택을 분리하고, active0의 완료 이력을 자동 선택하지 않는 경계를 보완한다. 기존 정상 완료 후 개설/참가 동작 영향은 Native와 오류/nullable 입력 차이만 협의한다. 새 제품 정책을 임의 결정하거나 기록을 삭제하지 않는다.

### 부분 완료 교체 뒤 실제 후속 명령 회귀 근거 보강

현재 공개 시험은 혼합 M/P 교체 뒤 qualify·worker·재조회·추가 완료·원ACK/기록과 메뉴 권한까지 확인했다. 누락 참가자의 일정/공대장/탈퇴 시험은 별도로 있지만 **옛 완료P+새 activeM 상태에서 일정 제출/확인·실제 탈퇴/승계·다음주 신규 발급을 끝까지 수행한 시험**과 같지 않다. Native 전체7번째가 요청한 후속 경계를 Backend에서 직접 확인할 수 있으므로 Native 화면을 기다릴 필요가 없다. 공백 보완과 직접 영향만 검증하고 기존 정상 시험/전체 Flutter 시험을 반복 요청하지 않는다.

## 독립적으로 구분할 미완료

- main/dev 병합·운영 배포: 미실행, 사용자 별도 지시 대상. Native 대기 때문에 못한 기능 구현이 아니다.
- 로컬 실자료의 방 상세/쓰기 인수: 당시 참가 방0으로 미실행. 격리 HTTP 근거는 유지하며 임의 실회원 쓰기나 자료 복구로 대체하지 않는다.
- 완전 소멸/퇴역 확정·대표404 대체·실자료 정리와 옛 소유 이전(#15): 원 Issue 이관/후속 근거를 보존한다. 현재 합의는 정상 소유 목록의 ‘누락 관찰/기존 참가 보존’이며 이것을 영구삭제/개명 확정 기능 완료로 표시하지 않는다. 이번 감사에서 미합의 자동 처리를 착수하지 않는다.
- Native 신규 DTO/실연결·화면/Penpot·기기: Native 담당·사용자 지시 범위. Backend 위 공백은 이 대기와 분리한다.

권장 다음 순서: Backend 전체 완료 source/다음주 선택 경계 보완과 오류/입력 소비 차이 협의→혼합 M/P 후속 명령 격리 검증→결과 인계. 이번은 감사이며 앱 소스/실서버/DB/키 변경·commit/push/merge·배포·Issue 종료는 하지 않았다.


공식 결과 회신: [#17 전체21번째 Backend 감사](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721435909). 감사 문서는 로컬 미커밋·미push이며 별도 게시 지시 전 유지한다.


## Native 후속 수신 — 전체22번째

[Native 선처리 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721977533): Backend 두 항목 보완·직접 검증과 결과 소비 대조 전까지 Native 기능 구현을 시작하지 않는다. active0에서 명시 선택 없는 prepare/후속 명령의 기대 결과 및 명시한 유효 캐릭터의 정상 경계까지 확인한다. 혼합M/P의 일정 제출/확인·실제 탈퇴/책임자 승계·다음주 발급, 완료P Snapshot/기록·주차 권한 보존을 명령 끝까지 검증한다. 계약 차이는 실제 응답/OpenAPI 영향으로 제시하고, 소스·게시·로컬 실행/DB·Native 인수를 분리해 회신한다. 다음 담당 Backend이며 이번 수신 확인에서는 구현/추가 시험을 하지 않았다.


## 사용자 진행 지시 후 보완 중

- `existing_participation.selection`은 실제 참가/세대/assignment 연결을 검증한 뒤 active만 현재 선택으로 반환한다. active0이면 None이다. `cycle_lifecycle.qualify`는 해당 이력의 권한 증거를 반환하고 과거 캐릭터의 신규 자격으로 대신하지 않는다. 관리 권한·참가 이력을 지우지 않는다.
- 초기 혼합M/P 실제 일정 제출/확인·탈퇴/자동승계·다음주 참가4건은 30479fafd378에서76.05초 PASS. 완료 후 현재선택 없음/관리권한과 실패후 rollback 직접시험을 추가했다. rollback의 시험 변수 참조 오류는 시험만 수정했고 b133bb500356에서1건30.33초 PASS다. 실행별 고유 사례/중복 여부는 검증 집계에 보존한다.
- 기본125경로142동작·two-cycle188경로209동작의 전체 생성 OpenAPI 일치는 fba794e5ed4c에서 PASS다. 공개 오류 계약은 아직 변경하지 않았다.
- 사용자에게 전체 완료 뒤 명시 캐릭터 없는 경우 selection=null·permission.allowed=false·reason=CHARACTER_SELECTION_REQUIRED, 유효 명시 선택은 정상 진행하는 계약을 제안해 확인 대기다. 이 공개 소비 경계는 승인 후 prepare/최종 명령과 HTTP까지 보완하며 아직 완료가 아니다.
- 앱2파일과 시험/문서만 로컬 변경했다. 실행 dev/운영 서버·DB·환경/키 변경·commit/push/merge는 하지 않았다. 소스 변경을 기존 image4ac36fdb에서 실행 중이라고 표시하지 않는다.

### 미선택 계약의 사용자 설명 범위

사용자는 오류 계약 질문이 ‘다음주까지 이미 참가한 캐릭터가 소실되고 이번주를 완료한 상황’을 뜻하는지 확인했다. 이에 대상은 이번주 모두 완료 후 **아직 참가하지 않은 다음주에 신규 참가·개설하는 경우**이며, 완료P에서 자동 선택하는 문제는 소실 없이도 발생한다고 설명했다. 이미 참가한 N은 기존 자리/기록을 유지하고 누락 경고·수동 교체를 적용하며 C 완료 때문에 N을 새 선택 상태로 바꾸지 않는다. 좁힌 범위의 미선택 nullable/오류 계약을 다시 확인 요청했으며, 질문에 대한 설명을 계약 승인으로 처리하지 않는다.


## 후속 완료 — 사용자 범위 승인·로컬 구현/검증

사용자가 앞서 설명한 신규 N 범위로 진행을 승인했다. [최종 보완·응답/계약 차이·실행별 검증·미반영 경계](roster-participation-followup.md)에 따라 두 감사 공백의 로컬 보완을 완료했다. 앞선 미선택 오류 계약 답변/prepare 미완료는 당시 진행 기록이며 현재 대기가 아니다. 다음은 Native 소비 대조이며 새 보완의 원격 게시/실제 dev 반영·기기 인수는 별도다.
