# 모집·일정 Backend 통합 체크포인트 — 2026-10-27

## 기록 목적과 완료 경계

현재까지 `feat/raid-recruitment`에서 누적한 구현·계약·직접 검증·개발 서버 반영·네이티브 인계를 하나의 통합 기준으로 보존한다. 사용자는 후속 확인·수정 가능성을 유지하면서 문서를 정리해 `dev`에 병합하고 `main`도 같은 커밋으로 맞추도록 승인했다.

현재 승인된 Backend 기능 구간은 구현·검증·게시·개발 API 반영·인계까지 완료했다. 전체 모집의 실회원·기기·성능 인수와 AWS 운영 배포는 별도로 남는다. 이 체크포인트가 열린 이슈의 종료나 남은 요구의 폐기를 뜻하지 않는다.

정리 시작 시 기준은 모집 브랜치 `a1d124e16f0cc26349ebe60702618812a7887f9a`, 원격 dev `ce3064f779206684bcd4babf5751a94dd30f5f3a`, 원격 main `77a1fe53875ddbe1a972361c90468106815c6f5b`였다. dev는 모집 브랜치의 조상이고 main은 dev의 조상이었다. 통합 전 모집 쪽에 누적된 커밋은179개였다. 기존 이력을 squash/rebase/force push하지 않는다.

## 현재 기능과 서버 책임

| 영역 | 구현된 동작·보존 기준 | 상세 원본 |
|---|---|---|
| C/N 모집 수명 | 실제 target_cycle_key·generation별 참가/리더/일정/완료를 분리한다. N→C 전환은 같은 식별자를 유지하며 새 N·참가를 자동 생성하지 않는다. | [주차 관리](weekly-cycles/README.md), [계약](weekly-cycles/contract.md) |
| 검색·캐릭터 필터 | 선택 T의 실제 본인 참가 방을 SQL 정렬·페이지 전에 제외한다. 그룹OR/회원AND/캐릭터OR, 정렬·정확 잔여 자리·권한과 조건에 결합된 cursor를 사용한다. | [검색](search/README.md) |
| 생성·설정·편성 | 소유·역할·입장레벨·주간 점유·정원·한도·권한을 context와 최종 쓰기에서 검사한다. C/N 생성은 전부 성공 또는 롤백이며 공통 설정과 주차별 설정/리더를 구분한다. | [생성·설정](creation-and-settings/README.md) |
| 신청·가입·승인·변경 | 공통 자격 evaluator와 실제 저장자료를 사용한다. pending은 참가·예약·한도를 소비하지 않고 승인 시 최신 자격을 검사한다. 실패 승인에서 pending을 임의 종료하지 않는다. | [참가](participation/README.md), [후보 계약](participation/candidate-contract.md) |
| 즉시가입 후보 | 기존 후보 GET에 intent=join을 추가했다. direct_join만 허용하고 actor=null, 모드 변경409·자격/역할/페이지/집계를 유지한다. 선택 뒤 context/POST에서 다시 검사한다. | [join 구현](participation/join-candidates-implementation.md) |
| 일정·동의·예약 | 개인표와 실제 T/세대의 제출 복사표를 구분한다. 자동조율은 실제 전원과 표·예약·출발 하한을 사용한다. 직접 제안은 세션별 동의/정족수와 원자 적용을 보존한다. | [일정](scheduling/README.md) |
| 베타 기본 출발 | 실제 참가와 개인표 복사·기본 약속 예약을 원자 저장한다. 더 이른 자동확정·30분 기한 기본확정·지연 시 needs_review와 명시 제안 복구를 구분한다. GET은 확정·저장하지 않는다. | [베타 구현](weekly-cycles/beta-implementation.md) |
| 식별·신청 문구 | 실제 T 참가자에게만 번호/5자리 비밀번호를 제공한다. 신청 메모 snapshot·본인 계정 프리셋 최대5개·CAS/원ACK를 유지하며 공개/기록 권한을 넓히지 않는다. | [베타 계약](weekly-cycles/beta-contract-wire.md) |
| 문자·목록 보완 | 메모/프리셋에 출력 ASCII 기호 전체를 허용한다. 종료 관계에 선택 주차 CM이 없는 목록500을 해결하고 content=null 기록 경계를 보존했다. | [기기 차이 조사](weekly-cycles/device-feedback-investigation.md) |
| 활성방 한도 | 현재 서버 C/N의 유효한 실제 참가 방 ID 합집합을 두 목록·한도·명령이 공유한다. 같은 방은1개, 과거/관계전용은 제외, 유효한 현재 review는 포함한다. 기존 관계 재참가·동시 마지막자리·영향회원 usage revision을 검사한다. | [한도·안내 구현](weekly-cycles/active-usage-and-wait-implementation.md) |
| 조율 대기 안내 | 베타 상세/plan의 include_coordination_wait=true에서만 waiting_members/no_earlier_candidate/pending/unavailable/not_applicable을 반환한다. 부족 인원만 양수이며 기본 응답/null 기록/기존 reader를 유지한다. | [선택 안내 계약](weekly-cycles/active-room-and-wait-proposal.md) |
| 검색의 분 정밀도 | GET/POST 검색 범위는 UTC 정수분·시작 포함/끝 제외다. 반올림 없이 페이지 전 필터와 정확한 조건 cursor를 유지한다. | [검색 분 구현](weekly-cycles/search-minute-precision.md) |
| 명시 출발의 분 정밀도 | 베타 생성/CN개방·실제 베타 세션 제안/수락/재평가/needs_review 복구만 정수분을 허용한다. 자동후보/개인표/진행시간/구 대안은5분,18:03의 기한은17:33이다. | [명시 분 구현](weekly-cycles/explicit-minute-departures.md) |
| 완료·기록·정정 | 본인/전체 완료·정정과 과거 참가 복원을 분리한다. 보관/종료 기록은 자기 귀속 anchor와 reader 권한으로 읽으며 완료·예약 해제 이력은 삭제하지 않는다. | [완료·기록](completion-and-records/README.md) |
| 탈퇴·추방·해산·승계 | 개인 완료 후T탈퇴·선택/양T 추방·일반 탈퇴/모두 탈퇴·본인 리더 주차 해산은 각자의 context/효과/ACK를 유지한다. 다른 주차와 완료 이력을 보존하고 명시 공대장 복구 경계를 구분한다. | [관계 정리](membership-actions/README.md), [계약](membership-actions/contract.md) |

기본 원자성은 기존 쓰기 잠금·권한·CAS·최종 시각 재검사·실패 롤백·원요청 멱등 응답에 있다. 화면의 C/N 이름이나 오래된 목록을 현재 명령 권한으로 사용하지 않는다. 성공 ACK 뒤 조회 실패는 성공을 취소하거나 새 쓰기를 자동 실행할 이유가 아니다.

## 의미 있는 구현 구간과 이력

아래 SHA는 각 구간의 대표 구현이다. 관련 문서·시험·인계·반영 기록은 동일 목적 브랜치에 누적했고 개별 채팅마다 이력을 재작성하지 않았다. 전체 상세 이력은 [DEV_LOG](../../project/DEV_LOG.md)에 보존한다.

| 구간 | 대표 구현 | 결과와 추적 |
|---|---|---|
| 모집 기반·조회·HTTP·활성화 준비 | `9664fb4`, `e74d850`, `9fb2058`, `a0a515c` | 내부 기반·입장 context·후보 HTTP와 readiness/활성화 경계 |
| 통합 모집·원천 저장·개인표·주간 점유 | `fdf2f58`, `fbf1f2f`, `1a007eb`, `d25c26b`, `841503d`, `66244da` | 기존 자료 보존을 고려한 구조·명령/일정·주간 상태 연결 |
| C/N·주차 수명·리더 | `917123e`, `13b655e` | W1/W2/W3의 실제 주차·세대·참가/승계 |
| 제출·명시 동의·일정 제안 | `6d2b301`, `88583a9` | W4의 복사표·예약·투표/정족수·세션 원자 적용 |
| 관리·그룹 후보·가입 전 표시 | `babb25b`, `8085e90`, `0afd879`, `07c2b67` | 관리 명령·전환 준비·권한 범위 후보·opt-in 표시 |
| 완료 정정·기록·비활성 보존 | `8bbcfc8`, `15e143a` | 완료 근거 정정/보관과 IF-001의 구 자료·원ACK 보존 |
| 개인완료 탈퇴·양주차 추방·일반 관계 정리 | `0eed67c`, `c606619` | #22~25 구현·개발 인계, 기존 명령과 새 원자 명령 구분 |
| 자격 후보·신청 분석/레벨 표시 | `484ca17`, `06ea4b2`, `f471e31` | #26 공통 자격·선택 후보·분석/본인 pending·레벨 출처 |
| 개발 기반 개선 통합 | `87c2a0e` | 격리 검증·해시 의존성 고정·개인정보 제외 JSON 로깅 통합 |
| 베타 기본 출발·메모·프리셋 | `d95e382` | wire2/profile1·DB0032·단일 약속/조기확정·기한 처리 |
| 문자 정책·종료 목록 | `0fd43f9` | 출력 ASCII 전체와 CM 없는 종료 관계 목록500 보완 |
| 즉시가입 후보 | `690f36f` | join intent/actor=null·전용 후보와 기존 context/POST |
| 활성방 한도·조율 안내 | `1800160` | 공통 활성 SQL/거래·usage revision·선택 대기 안내 |
| 검색 정수분 | `a358a1a` | 18:03~20:17 같은 범위를 그대로 검색 |
| 명시 출발 정수분 | `420e057` | 생성/개방/제안/수락까지 원분 보존·자동5분 유지 |

중간에 구현했던 이번주 미완료 종료·같은 주차 weekly_resume는 [IF-001](completion-and-records/inactive-features.md)에 따라 앱 활성 기능에서 제외했다. 과거 구현 커밋의 존재를 현재 활성 제품 요구로 해석하지 않는다. 구 endpoint·기록·원 pending/ACK와 다음주 개방 경로는 보존한다.

## 계약과 공개 범위

- 실제 개발 API는 [two-cycle OpenAPI](../../../openapi/two-cycle.openapi.yaml)의178경로/199operation, DB0032를 사용한다. 기본0023 앱은 [기본 OpenAPI](../../../openapi/openapi.yaml)의116경로/133operation으로 따로 보존한다.
- 베타 opt-in은 `contract_profile=beta-recruitment-1`, 계약 버전은 `beta-recruitment-wire-2`다. application-display/membership-actions reader와 조율 안내의 선택 확장을 구분한다. 원ACK·기존 reader·생략/false·beta_schedule=null·record content=null 경계를 유지한다.
- 신청 메모/번호·비밀번호/개인표/예약은 기존 권한과 실제 T·세대에 귀속한다. GET에서 복구·동의·자동확정을 실행하거나 public/검색/쓰기ACK에 비공개 자료를 넓히지 않는다.
- 저장 문자 정책은 `hangul-printable-ascii-1`이다. UTC 정수분 출발과 5분 자동탐색·개인표·진행시간을 구분하며 초/소수초를 반올림하지 않는다.
- 최신 [완결 계약 예시](weekly-cycles/proposals/beta-recruitment-v2.wire-examples.json)는130개이고 원ACK32개 operation 보존을 검증했다. 예시는 합성 구조 자료이며 실제 회원 성공 응답의 증거가 아니다.

## 검증 근거와 재사용 범위

| 구간 | 확인한 근거 | 구분 |
|---|---|---|
| 후보/표시·아이템레벨 | [후보 계약](participation/candidate-contract.md), [신청 표시](participation/application-display-proposal.md), [아이템레벨](participation/application-item-level-proposal.md) | 각 구간의 격리·계약 시험 및 Native 자체 보고를 구분 |
| 베타 구현 | [베타 구현/격리 검증](weekly-cycles/beta-implementation.md) | 당시 베타22/기존105 결과와 실제0032 전환 기록은 별도 |
| 문자·종료 목록 | [개발 반영](../../engineering/operations/device-feedback-rollout.md) | 직접7·읽기 서비스12·실제HTTP6은 서로 다른 증거 |
| join 후보 | [개발 반영](../../engineering/operations/join-candidates-rollout.md) | 직접6·실자료 후보/목록·HTTP6, 정상회원 가입/기기와 구분 |
| 한도·조율 안내 | [개발 반영](../../engineering/operations/active-usage-wait-rollout.md) | 고유18·실자료 사용3/목록 일치·상세/plan8·HTTP6 |
| 검색 정수분 | [개발 반영](../../engineering/operations/search-minute-rollout.md) | 고유6·실자료 READONLY 검색·HTTP9 |
| 명시 출발 정수분 | [개발 반영](../../engineering/operations/explicit-minute-rollout.md) | 고유17·배포 순수 검사·실자료 READONLY 검색·HTTP9 |

각 구간의 시험은 중첩되므로 합산한 ‘전체 통과 수’를 만들지 않는다. 통과한 같은 업무 소스의 결과는 재사용하며 새 실패·미확인 위험 없이 전체 회귀·DB 복원 리허설을 반복하지 않는다. 초기 시험 자료의 오류와 수정 후 재검증은 해당 구간 원문에 남겼다.

이번 통합은 문서 갱신과 기존 커밋의 이력 보존 병합이다. 업무 코드·고정 패키지·OpenAPI·실행 설정이 최신 검증 소스420e057과 동일한지 Git으로 대조하고 문서/링크·동결 원문·diff 검사를 수행한다. 이 이유만으로 새 DB/서버/기기 시험을 반복하지 않는다.

## 개발 서버와 Git 통합의 구분

현재 개발 API 실행 소스는 `420e0570feb0c7f4be82dca8ee132e30000540f0`, 이미지 `sha256:cd581ac04aa8bb5d429af25bf5553d26bd117d4f382244216416eddc024bfa39`, 마지막 반영 기록은 `a1d124e16f0cc26349ebe60702618812a7887f9a`다. DB는 `0032_beta_recruitment`다. [실행 집계](../../engineering/operations/records/explicit-minute-rollout.json)를 따른다.

최신 API 반영은 DB 컨테이너/이미지/볼륨·자료·환경과 API의 키/command/포트/보안/로그를 보존했다. 실제 자료 변경·삭제·초기화·미확인 회원 명령 재실행은 하지 않았다. 새 분 자료나 처리된 명령과 구 코드의 호환이 불명확하면 자료를 유지한 전진 수정이다.

검증 경로는 [격리 실행](../../engineering/development/isolated-verification.md), 의존성은 [해시 고정](../../engineering/development/dependency-locking.md), 로그 확인은 [로깅](../../engineering/operations/logging.md)을 따른다. 라이브러리 업데이트와 전체 검증은 별도 변경 위험이 있을 때 수행한다.

이번 dev/main 통합은 Git 기준을 맞추는 작업이다. 실행 API 이미지를 새로 빌드·교체하거나 DB migration·AWS 배포를 실행하지 않는다. 새 Git HEAD가 실행 이미지의 소스 SHA로 자동 바뀌는 것은 아니다.

## Native 수신·미완료·다음 담당

공식 협업은 [Issue13](https://github.com/heo0328/lostparty-backend/issues/13)과 관련 #22~26이다. 상세 수정/기기 보고와 Backend 실행 증거를 구분한다.

- [전체173 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6414804154): join 후보·조율 안내·서버 사용량 연결 보고. 사용량을 C/N 카드 길이로 재계산하지 않는다.
- [전체174~175 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6418614101): 후보/참가·조율/그래프·승계·주차 독립과 완료 후 목록 복귀/갱신의 사용자 기기 통과 보고. 최초 수정 실패와 실제 push 진입 가드 정정 이력을 보존한다.
- [전체176 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6420198698): 기본 기한 처리·수동 완료 해제·문구 공유의 기기 통과, picker/편성409 처리·내 계정 연결 수정은 직접 시험과 후속 기기를 구분했다.
- [전체179 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6422070028): 명시 출발 정수분 정책 수용/구현 착수. [전체180 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6422693611): 구현·개발 반영·직접영향 인계 완료.
- [전체181 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6422980400): 해산 확인창 최초 조회의 build 중 알림 예외를 Native에서 재현/수정하고bd7e0492를 게시했다. 새 Backend 요청은 없다. 실제 제보의 중복 쓰기는 요청 횟수 자료가 없어 확정하지 않는다. 분 제안 판정을 실제 BetaSchedule.session_id로 맞추는 Native 후속도 별도로 남겼다.

| 남은 항목 | 다음 담당·완료 조건 |
|---|---|
| 분 단위 생성/개방·제안/수락 | Flutter가 실제 베타 세션 판정을 맞추고 일반 앱 연결·직접 기기 결과를 회신한다. Backend는 구체 차이에 대응한다. |
| 검색 비5분 범위 | Backend 반영은 수신 확인됐다. Native 실제 검색 기기 결과는 아직 미확인이다. |
| 해산 확인창 수정·기타 직접 영향 | Flutter가 수정 후 기기 로그/직접 영향과 추방·해산 권한 경계를 관리한다. 통과한 전체 목록을 재요청하지 않는다. |
| 원ACK 실제 동일 키 대조 | 실제 원자료가 있을 때 Native/Backend가 대상·method/path/body/key·당시 주차를 대조한다. 원자료가 없는 복구 배너는 기존 자동검증 근거를 유지하며 강제 기기 과제로 만들지 않는다. |
| 전체 기기·성능·실회원 인수 | 사용자/Flutter가 별도 인수 범위를 관리한다. 부분 기기 통과나 합성 시험을 전체 인수로 확대하지 않는다. |
| 운영 배포 | AWS 환경·배포/보안/관측·인수는 별도 승인 작업이다. dev/main 정렬로 운영 완료를 표시하지 않는다. |

개발 자료는 오픈베타 시작 시 폐기할 예정이라는 사용자 정책을 유지한다. 이를 위해 새 기능마다 기존 임시 자료를 살리는 변환/이중 운영 통로를 만들지 않는다. 테이블 구조 변경을 위한 migration과 저장 자료 이전을 구분하며 실제 초기화/삭제는 대상·영향이 명시된 별도 승인 없이는 실행하지 않는다.

## Git 통합 실행 기록

현재는 문서 정리·검증을 마친 뒤 모집 브랜치 게시→dev PR 병합→main fast-forward/동일 시점 push를 진행하는 구간이다. 정확한 문서 SHA·PR·병합 SHA·push 및 브랜치 정리 결과는 완료 후 이 절에 누적한다. 활동 선택의 미완료 로컬 작업은 이번 모집 통합에 포함하지 않는다.
