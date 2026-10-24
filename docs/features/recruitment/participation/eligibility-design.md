# 신청·캐릭터 변경 통합 자격 설계

2026-10-24 / 작업 구간명: **모집 신청·캐릭터 변경 통합 자격 보완(#26)** / 브랜치 `feat/raid-recruitment`. 소비 검토/사용자 UX 확정에 따라 공통검증·변경원자성·신규 후보GET을 구현·격리 검증했다. 실제 개발 반영·실회원/기기 인수는 미완료다.

원본은 [#26 전체2번째 Flutter 역할 일치 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381216870), [전체3번째 Flutter 최신 사용자 확정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381254676), [전체4번째 Backend 기존 검증 차이 회신](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381295804)이다. 전투력 제외·신청 전용 제안1은 최신 범위로 대체한다.

[#26 전체6번째 Flutter · 보완 계약2 소비 검토/사용자 UX 확정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381816954)에서 공통 GET/intent·actor·역할/전투력·계수/페이지·사유우선순위를 소비 가능으로 확인했다. 문서e7bfe113 push 보고이며 Backend 독립 실행 검증은 아니다.8인 파티이동 확인·동의와 수락 자격실패 시 pending유지 UX도 확정됐다. 추가 예약/일정 영향이 발견되지 않으면 별도 사용자UX 결정을 기다리지 않고 확정범위 구현으로 진행한다.

## 작업 분류와 순서

| 구간 | 필요성과 작업 내용 | 완료 조건·다음 담당 |
|---|---|---|
| 1. 공통 판정 설계 | 신청/변경 후보·context·POST·승인에서 동일한 역할/레벨/전투력/완료·점유/구성을 사용 | 본 문서의 우선순위·자기제외·자료정책 명시. Backend 설계 |
| 2. 보완 계약2 | 문맥/권한·DTO·role 불가사유·전투력·계수/페이지·snapshot을 닫음 | [읽기·쓰기 계약](candidate-contract.md)·closed schema/예시 정적 검증, Flutter 구체 소비차이 검토 |
| 3. 공통검증 구현 | 기존 읽기 구성/레벨·주간 검사와 역할별 전투력 비교를 공통 평가로 연결 | 후보/context/신청/변경/승인 동등성·변경 원자성 직접시험. 계약 차이 해소 후 Backend |
| 4. 후보읽기 구현 | 한 본인 graph·target/주간/파티 snapshot을 bulk 조회해 역할별 필터/계수·페이지 제공 | 권한·비동기 scope·완전조회/실패·SQL 증가 검증·실행 OpenAPI 전체 비교 |
| 5. 게시·연결·실제 인수 | 검증구간 commit/push·원격 확인 후 소스/계약 인계 | Flutter reader·목록/역할·실제 UI 검증, 별도 개발 반영 승인 후 정상로그인/실회원·기기 인수 |

예시는 판정과 계약을 검증하는 자료다. 예시부터 기능/권한을 결정하지 않는다. 설계 이후 구현 구간에서 app/후보 OpenAPI를 함께 갱신했다. DB migration·실제 서버는 변경하지 않았고 기존25시험 반복이나 서버 반영 전 실회원 시험을 요청하지 않는다.

## 판정 책임과 재사용

라우터는 인증/입력·문맥, 공통 평가기는 현재 DB 증거에 대한 역할별 자격·유효 배치, 명령 서비스는 현재 권한/CAS·동의/기한·원자 쓰기/원ACK를 맡는다. 후보조회에서 게임키/외부 provider를 호출하거나 전투력·주간 원장을 갱신하지 않는다.

- 본인 source: 활성 등록→본인 verified Account→현재 Configuration/Activity→confirmed/active canonical Character/NameClaim을 재사용한다. 소유/활동·완전성 오류를 정상 후보0과 혼동하지 않는다. 본인 source 캐릭터별 식별자는 기존 UUID를 사용한다.
- 구성: 기존 `composition_slot`의 같은4인파티 dealer 직업중복/딜러3·서포터1·총4인 규칙을 재사용한다. confirmed active Assignment만 넣고 pending을 넣지 않는다. slot 반환은 예약이 아니다.
- 레벨/주간: 같은 catalog difficulty/Decimal 비교와 WeeklyState 완료·WeeklyOccupancy의 정확한 귀속을 재사용한다. 묶음 전체 item의 실제T/현세대·round를 평가한다. 이전T·다른raid·단순 pending은 점유로 세지 않는다.
- 전투력: `power_comparison`/RolePowerSuccess의 같은(user,character,ownership_revision,selected_role) 마지막 성공값과 해당 역할 최소값을 비교한다. 최신 head/성공본 버전·관측/저장시각·issues를 유지한다. 미래 구현은 bulk 적재 자료를 받는 순수 평가와 기존 DB wrapper를 공유해 캐릭터/역할당 재조회·외부 N회 context를 만들지 않는다.
- 전체쓰기 권한: 기존 그룹/회원한도·중복신청/참가·모집 상태·일정 선택/동의·마감·expected revision은 기존 context/POST에서 추가 검사한다. 후보가 있다는 사실이 이 모든 권한의 허용은 아니다. 이번 후보필터에 무관한 회원한도 등을 몰래 추가하지 않는다.

## 역할·전투력·불가사유

수용된 기존 제품정책을 서버와 일치시켜 구현했다. 일반직업은 dealer만, **바드·발키리·도화가·홀리나이트**는 dealer/support를 모두 평가한다. unsupported role은 `supported=false/allowed=false/reason=ROLE_NOT_SUPPORTED/comparison=null`. 이 code는 직업 구성 불가와 구분하며 신청/변경/승인 context·쓰기에도 동일 적용한다. 기존에 성공한 구 원명령의 원ACK는 현재 역할정책 재검사 전에 기존대로 복구한다. 과거 역할·참가/완료/분석·pending 자료를 삭제/변환하지 않는다.

역할별 원천 데이터 무결성을 먼저 확인한다. 문맥/권한/자료 오류는 전체 실패이며 역할 불가사유로 숨기지 않는다. 판정 가능한 역할의 대표 불가사유는 **역할미지원→묶음 레벨→역할 전투력→개인/파티완료→주간점유→정원/파티구성** 순서다. 묶음 item은 UUID순으로 안정 처리한다. 이 순서는 제안2의 명시적 우선순위로, 여러 조건이 동시에 실패할 때 기존 단일 경로와 첫 reason이 달라질 수 있으므로 합의·직접시험 대상이다. context/POST/승인은 같은 공통 결과를 사용한다.

전투력 정책은 다음과 같다. Decimal 정밀도를 보존하며 0/다른 역할/최댓값으로 대체하지 않는다.

| 상태 | 후보/명령의 제안 판정 | 응답 근거 |
|---|---|---|
| 역할 최소값 없음 | unrestricted: 이 조건 자체는 허용. 실제값 없음은 null 유지 | requirement=null, actual/state·관측시각 그대로 |
| 최소값 있음·성공값 없음 | missing: 불가/미확인, COMBAT_POWER_REQUIRED | actual=null·관측/성공version null, exclusion_summary.detail=missing |
| 성공값 < 최소값 | below: 불가, COMBAT_POWER_REQUIRED | 정확한 저장 actual/최소값, detail=below |
| 성공값 = 또는 > 최소값 | meets: 이 조건 자체는 허용 | 해당 역할 저장 성공값/버전/관측·저장시각 |
| 현재 head가 null/실패·성공본보다 새 버전 | 마지막 성공본으로 위 비교를 유지 | current_summary_version와 success_summary_version 차이·current/success issues 공개 |
| 오래된 관측·warning/error issues가 있는 성공본 | 현행 정책상 자동 만료/경고 일괄차단 없음. 같은 성공값으로 비교 | 저장된 시각과 issues를 그대로 보여줌. 오래됨을0/없음/갱신 성공으로 만들지 않음 |

임의 TTL·강제 freshness·경고에 따른 자격 차단은 현재 정책이 아니므로 신설하지 않는다. 저장 숫자/관측시각·참조가 깨졌으면 서비스/자료오류로 전체 실패하고 임의 통과·부분0건을 반환하지 않는다. 전투력 provenance는 현재 소유 revision의 저장 분석값이며 외부 provider가 인증한 값이라고 표시하지 않는다. 생명주기 변화에 따른 성공본 해석을 기존 비교와 다르게 추가 차단하지 않는다. 정책을 바꾸려면 별도 제품 결정과 후보/실제쓰기 공통 적용이 필요하다.

## 신청과 변경의 차이

신청은 현재 확정파티에 새 참가자를 가상 추가한다.4인은 파티1,8인은 파티1→2 순으로 유효 배치를 고른다. 이미 정원이 찼거나 모든 파티에 구성 불가면 제외한다. 대기신청은 서로 자리를 막지 않는다. 실제 신청은 pending만 만들며 승인 시 최신 자료·자리로 다시 검사한다. 기존 신청에 저장된 배치를 승인 시 임의 다른파티로 바꾸는 정책은 신설하지 않는다. 승인 가능한 현재 저장 배치가 없으면 기존과 같이 재검토/거절한다.

변경은 서버가 현재 회원의 target/현세대 participating CM과 정확히 대응하는 active Assignment 묶음을 도출한다. 요청에 다른 회원/과거CM/임의 Assignment를 받아 자기제외하지 않는다. 기존 캐릭터가 비활동/소유상실 상태라도 본인 CM 권한과 변경 대상이 검증되면 정상 복구 변경을 막는 추가 조건으로 사용하지 않는다. 새 후보는 현재 소유/활동·canonical 검사를 통과해야 한다.

1. 각 round에서 교체대상 **Assignment ID만** 가상 제거한다. membership 전체의 다른round/과거세대·다른회원·다른T를 빼지 않는다.
2. 후보의 WeeklyState/lease는 같은(user,candidate_character,raid,T)를 검사한다. lease.assignment_id가 검증된 교체대상 Assignment와 일치하고 room/item/round/character/owner·ledger active 관계가 맞을 때만 해당 점유를 자기제외한다. 다른방 또는 같은방의 다른 Assignment 점유는 차단한다. 개인/파티완료를 자기제외하지 않는다. 불일치는 WEEKLY_OCCUPANCY_CHANGED/관련 기존409로 전체 실패하고 자동수정하지 않는다.
3.4인은 자기제외한 파티에서 검사한다.8인은 **원파티 우선→반대파티**로 검사하는 보완안을 제안한다. 원파티에 가능하면 기존 slot을 유지하고, 반대파티가 유일하게 유효하면 그 파티의 빈 slot으로 변경한다. 현재 변경은 원파티 고정이므로 이 지점은 명시적 동작 보완/네이티브 합의 대상이다. 현재 지원 묶음4인 규칙도 유지한다.
4. 후보/context/실제쓰기 모두 같은 배치 선택기를 사용한다. 실제 context가 기존 targets.party_no를 제공하고 POST는 그 원본문과 기존 CAS·토큰·Assignment revision을 재사용한다. 후보읽기의 suggested 배치를 새 쓰기 권한으로 사용하지 않는다.
5. 모든 신규 자격/최종 기한을 다시 확인한 뒤 한 트랜잭션에서 기존 예약/참가 정리→새 배치/점유→동의/계획·감사 변경을 처리한다. 실패·동시성 충돌 시 전체 rollback해 기존 캐릭터/예약·반대T를 보존한다. 같은 캐릭터·역할 유지/역할 변경의 허용은 기존 명령 경계를 유지하며 후보목록에서 현재 캐릭터를 일괄 제거하지 않는다.

## 구현 영향과 검증 구간

| 구간 | 구현 영향 | 직접 검증 |
|---|---|---|
| 공통 역할/자격 | 역할정책·level/power/weekly/composition evaluator 공유, 기존 DB/조회 wrapper 연결 | unsupported/단·양역할·역할별 power null/경계/오래됨·warning/head실패/정밀도, 사유 우선순위 |
| 변경 가상 구성 | 정확 Assignment·lease 자기제외/8인 원파티 우선 배치 | 전체정원 상태 정상변경·원캐릭터 유지/역할전환·반대파티 허용/불가·다른방/같은방다른점유/완료 차단 |
| 명령/원자성 | 기존 tokens/CAS/원ACK·승인과 공유, 기존 POST shape 유지 | 후보→context/POST→승인 사이 변경·위조·경쟁, 두번째 item/감사/저장 실패 rollback·예약/반대T 보존 |
| 일괄 읽기 | 본인 source/두역할 성공본·주간·확정배치 bulk 적재/메모리판정·HMAC페이지 | 권한/교체actor·필터전 count·전페이지 동일 snapshot/중복/누락·cursor stale/타인범위·자료불완전 실패/SQL 횟수 |
| 소비/인계 | schema/예시/실행 OpenAPI/정확 source 연결 | Flutter 전페이지 취합후 기존 원정대/레벨순·대표/선호역할, 실패/로딩과0건·계정/환경/T/epoch 격리 |

DB migration은 추가하지 않았다. 기존 endpoint/쓰기 DTO를 보존하고 신규 읽기1경로를 후보 실행 OpenAPI에 반영해177경로이며 실제 개발서버도177경로로 교체했다. [개발 반영·자료 보존 검증](../../../engineering/operations/eligibility-rollout.md)을 따른다. 기존 source6e0063c/25PASS는 이전 구간 근거이며 이번 고유45PASS와 합산하지 않는다.


## 확정 성공·실패 UX와 추가 구현 경계

8인 변경은 확인창에 실제 이동할 파티를 표시하고 동의 후 캐릭터/배치를 함께 변경한다. 원파티 가능이면 기존자리 우선. 확인 뒤 actor/Assignments·배치/자격·일정동의 의미가 바뀌면 원동의로 다른배치를 실행하지 않고 POST 없이 확인을 갱신한다. context의 targets.party_no·교체actor/Assignment revision·동의 내용이 token과 쓰기 최종검사에 함께 묶여야 한다. 부분 변경·무동의 이동은 없다.

승인 시 전투력/완료·다른방참가·구성 등 자격실패는 신청 pending을 유지하고 공대장에게 정확한 불가사유를 표시한다. 참가/예약/점유 신규쓰기0, 기존 거절/본인철회 가능. 만료/이미처리/권한상실은 기존 오류로 구분하며 실패를 자동거절/철회·재신청강제로 바꾸지 않는다.

신청 ACK 뒤 시트닫기·원방상세 유지/내신청 갱신, 승인 ACK 뒤 참가/계정i·방인원/영향T 검색·목록 갱신, 거절/철회는 해당신청 갱신이다. 응답유실은 같은 원본문/key 재확인, 성공ACK 뒤 GET실패는 성공을 유지하고 조회만 재시도한다. 메모리pending을 앱종료 영속보장으로 확대하지 않는다. 변경 취소는 POST0이며 실패/경쟁은 기존 캐릭터/자리·예약·다른T 보존이다.

[전체8번째 Flutter · 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382315586)에 따라 1생성/2가입/3상세내부/4완료·해체/5주차분리는 사용자 수동시험 분량·순서만 뜻한다. 신청·변경 두intent의 자격/후보·확인/원명령·갱신을 함께 구현·연결하고 생성/상세·일정·완료/해산·C/N의 직접 영향 회귀도 함께 보호한다. 현재2가입이라고 다른 구간의 설계/구현·필요 회귀를 제외하거나 미루지 않는다. 사용자에게는 소수 항목씩만 요청하고 다른 묶음 직접 영향 재확인은 이유와 해당 항목을 제시한다. 무관한 기능확대·전체시험 반복 요청은 아니다. 구현 중 기존 예약/일정동의 범위를 넘는 영향이 발견되면 그 구체 차이만 먼저 같은Issue에 회신한다. 그 외 새 UX 질문/기존 전체시험 반복/서버반영 전 실기기 확인을 선행조건으로 추가하지 않는다.


## 구현·직접 검증 결과

공통 eligibility loader/순수판정·배치와 기존 명령 adapter를 연결했다. source/target/현세대·round 완전성, 후보/교체 원캐릭터의 ledger/lease/Assignment/round·가입시각을 읽기 검증한다. 전투력 projection은 기존 마지막성공 정책을 순수 함수로 공유한다. 신규 역할정책/사유 순서는 apply/change/approval에만 적용하고 생성/직접가입은 유지한다. 변경의 실제old Assignment도 정확한 현CM에서 선택하며 자격/배치/캐릭터 source 근거를 기존 서명에 결합한다.

[직접 검증 집계](validation/eligibility-results.json): 고유45PASS(신규19·기존26), 최종 소스의 분할 통과10+8+27·중복 없음. 기존35예비 통과/중간 실패를 합산하지 않는다. 초기에는 확인근거에 캐릭터 원자료 누락을 시험에서 발견해 보완했고 그 변수참조 오류도 수정했다. 나머지 재실행 원인은 합성 fixture의 ledger/lease 시각 불일치와 종료시각 설정 전 autoflush 제약으로, 정상 fixture를 맞춘 뒤 통과했다. 기존 Starlette/AnyIO 경고1개다.

같은 역할 power·정밀도/보존 성공본/경고·원후보/제외/페이지·same-room다른점유·지원역할·후보/context/POST 일치,8인 반대파티·확인후변경거절·원ACK·두번째item실패 rollback/반대T 보존, 승인최신자격실패 pending/업무자료불변·저장파티 유지·마지막자리 경쟁/거절/철회·기존변경을 확인했다. 신규 HTTP는 synthetic principal router와 실제 합성Bearer의 인증/외부intent/취소session·no-store를 구분 검증했다. 후보20캐릭터 추가 전후 SQL 횟수 동일을 확인했으며 사용자 환경 성능 인수로 확대하지 않는다.

최종 후보이미지에서 소스239파일·기본116/신규177 전체 OpenAPI·기존component/쓰기shape 일치·보존을 확인했다. 별도 합성0031 DB/NOSUPERUSER LOGIN의 실제 factory/readiness·health200·새GET 인증거절2건/no-store를 확인했다. 작성 예시21/비정상16 정적검사는 실행45건과 별도다. 위 격리검증 당시에는 실제 개발API를 교체하지 않았다. 이후 [개발 반영](../../../engineering/operations/eligibility-rollout.md)을 완료했다. DB migration/실회원·기기/운영 인수는 이번에도 미실행이다.
