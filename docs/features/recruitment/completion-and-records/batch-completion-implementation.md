# Issue47 v3 공개 API·원자 명령 구현

2026-11-10 / `feat/raid-batch-completion`·기준084a6af 위 로컬 변경. [Native 전체6번째 수용](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6761376813)과 사용자 구현 지시에 따른다. [v3 계약](batch-completion-wire-v3.md)을 구현했으며 코드 게시·실제 개발 서버 지원·Native 연결/기기는 별도 상태다. 미커밋·미push이므로 신규 고정 Git SHA는 없다.

[전체7번째 Backend 구현/검증 결과](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6762507528)로 회신하고 전체 댓글7개/게시 본문 일치를 확인했다. 최종 고유123PASS(신규/내부24+기존99)·도구63PASS, 최종 전체 계약/HTTP 대조와 앱288파일 바이트 일치 확인이다.

## 변경 동작과 책임

공통 `/v2/raid-rooms/{room_id}` 아래 GET batch-completion-context / POST batch-completions, GET batch-personal-completion-departure-context / POST batch-personal-completion-departures를 제공한다. 완료 context와 POST는 같은 snapshot 계산으로 선택 집합·정책/권한·활성 효과·이력 proof·revision·예상 state/리더를 결합한다. 실제T·현재 세대·각 선택 round 전체를 검사하며 실행 불가에는 token을 발급하지 않는다.

공대는 선택 round 활성 참가 전원을 party 완료하고 미선택 활성 참가를 보존한다. 개인은 선택한 본인 활성 참가를 manual 완료하고 미선택을 취소한 뒤 해당 주차에서 탈퇴한다. 자동 후계자·마지막1인 완료/취소 종료는 기존 의미를 유지한다. 기존 완료 원장 시각/원천·다음T/타인·지속 소속은 보존한다. 그룹 후계자 자격·정책과 비공개 조회 권한을 기존 서버 규칙으로 검사한다.

활성 효과만 정확한 ID/전체 레이드 표시와 5/40 제한에 사용한다. 과거 완료는 종료된 참가·다른 캐릭터·비현재 round까지 독립 집계하며 레이드별 건수/해시를 제공한다. 쓰기 후 새 완료 ID를 제외한 proof와 원 context proof가 같아야 한다. 과거 이력의 수나 현재 캐릭터와의 차이만으로 정상 명령을 거절하지 않는다.

`cycles.execute`가 하나의 명령 트랜잭션·원ACK·최종 주차/시각 검사를 소유한다. 새 operation은 batch-complete/batch-depart이며 기존 단건 operation/body/key/query/ACK는 유지한다. 첫 쓰기 전 전체 scope·권한·CAS·token·정확한 원장/점유/예약을 검증하고, 점유/예약·일정/참가·멤버/세대 상태·승계·감사와 ACK를 함께 저장한다. 중간/ACK 저장/최종 검사 실패는 업무와 성공 ACK 전체를 rollback한다. 기존 사전 시각 reconcile 효과는 그 트랜잭션과 구분한다.

업무 구현은 `app/raid_rooms/outcomes/batch_completion.py`, 활성/이력 읽기는 같은 폴더의 batch_snapshot.py, 새 DTO는 schemas/batch_completion_schemas.py에 둔다. 신규 모델 이름은 Batch 접두사로 기존 component ID 충돌을 피했다. batch scope의 target 식별자/revision은 non-null이다. 기존 qualification/selection에는 optional active_rows만 추가해 현재 활성 자료에 같은 자격 검사를 적용하며 기존 호출자의 기본 경로는 유지한다.

## 계약·검증 근거

두 전체 계약은 기본125경로/142동작, two-cycle192경로/213동작이다. 기본 계약 객체/파일은 그대로이며 two-cycle은 기존188경로/209동작과 기존 component 전부를 보존하고4경로·22개 Batch schema만 추가했다. participation_profile 지원/선언은65→69동작으로 함께 갱신했다. 정확한 hash·선택 시험·실행 시간·실패 정정·미실행 항목은 [검증 집계](batch-completion-verification.json)를 따른다.

새 시험은 실제 FastAPI HTTP·격리 PostgreSQL 합성 자료로 수행한다. 전체 효과 표시/권한·scope/body 위조/profile, 공대 부분/전체·개인4가지 탈퇴, 누적 이력의 실제 완료,8인×5개 전체/부분, 신규끼리 및 기존 단건/캐릭터 교체/탈퇴 경합, 중간 쓰기·ACK 저장·토큰/주차 최종 rollback·원ACK를 검증한다.8인×5개는 합성 카탈로그/출처 상태의 엔진 경계이며 기존 묶음 생성 정책의 인원 한도를 확대하지 않는다.

프로젝트 전체 회귀를 새로 실행한 것은 아니다. 이번 선택 회귀의 통과를 과거 전체1921PASS/기존2FAIL이나 실제 dev/운영·회원/기기 인수로 확대하지 않는다. 기존 경고의 무관한 일괄 정리는 하지 않았다.

## 게시·실행 지원과 다음 담당

신규 코드/시험/계약/문서는 미커밋·미push이다. 기준084a6af는 이번 구현 커밋이 아니며 원격 OpenAPI가 신규 계약으로 갱신됐다고 안내하지 않는다. 로컬 파일 hash와 검증 이미지 소스 일치는 Git SHA와 별도 증거다.

실제 dev API/DB0036·운영을 교체하지 않았고 migration·새 환경/키·자료 쓰기/삭제·태그/운영/APK 배포·merge·Issue 종료는 하지 않았다. 테스트는 고유 임시 프로젝트/tmpfs DB만 사용했다. 새 API의 실제 서버 지원은 미반영 상태다.

다음 Backend는 사용자 게시/실제 로컬 반영 지시 범위에서 source commit/push·원격 확인·API만 반영/보존 확인·실행 계약 대조 결과를 인계한다. Native는 합의된 v3에 따라 기능 연결을 담당하며 소비할 코드/계약 게시와 실제 서버 지원을 구분한다. 미게시/미반영 코드를 원격에서 시험하도록 요청하거나 같은 계약 수용/정상 기기 시험을 반복 요청하지 않는다.
