# 개인 완료 탈퇴 후 다른 캐릭터 재신청 — 수정 설계

**최종 인수/통합 기준:** 사용자 기기에서 과거 기록 보존·다른 캐릭터 신청/가입 완료를 확인한 뒤 Issue13을 사용자 승인 종료했다. [수정 브랜치 통합 기록](../reapplication-integration-2026-10-27.md)에 구현/DDL·직접20PASS·개발 반영·기기 인수/차후 보완을 모았다. 아래 정상회원 미확인/Native 확인 대기는 당시 구현·반영 시점 기록이다.

**최신 상태 — 개발 반영·실행 확인 완료:** 소스c1f86d8/이미지581a1a5e·DB0033, [반영·검증 기록](../../../engineering/operations/reapplication-history-rollout.md)·[전체185 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6436334435)를 따른다. 아래 게시/반영 예정은 소스 검증 당시 이력이다. 다음 Native 제보 재신청 기기 확인/Backend 차이 대응이며 정상회원 성공은 미확인이다.

2026-10-27 / 작업 구간 **모집 재신청의 과거 기록·새 참가 판정 정합성 보완** / 브랜치 `fix/raid-recruitment-reapplication`.

최신 origin/dev `18830c21bd260592a5455526b7565a3a7ef7a1a9`에서 분기했다. 현재 checkout은 같은 수정 브랜치다. 사용자 구현 승인 후 아래 수정과 직접 검증을 완료했다. **이 소스 구간을 게시한 뒤 개발 DB0033·API 반영과 Issue13 인계를 이어간다.** dev/main 통합과 AWS는 범위 밖이다.

## 구현·직접 검증 결과

- 수정 전 합성 C/N 흐름에서 다른 캐릭터가 후보에 있어도 apply context가 `TARGET_CONTEXT_STALE`로 거절되는 것을 실패 재현했다. 수정 후 후보→context→신청 pending→리더 승인→새 실제 참가가 통과했다. direct_join도 같은 종료 근거를 사용한다.
- `admission_history`는 실제 T/현재 세대의 최신 종료 CM, 해당 revision의 불변 종료 이벤트, 이벤트에 기록된 모든 Assignment ID와 실제 바인딩·종료 상태를 대조한다. 같은 근거를 후보 서명·context/명령 검증·최종 새 CM 설치에서 사용한다. 근거 누락은 허용으로 바꾸지 않는다.
- 새 참가에는 새 CM/가입순번·Assignment/바인딩을 할당한다. 과거 completed/left·종료 CM·완료/이벤트·동의/해제 예약·N의 업무 행은 보존한다. 과거 record는 종료 snapshot을 우선하며, 이전 snapshot 없는 이벤트는 그 과거 Assignment의 불변 해제 예약에서만 시간을 읽는다. SessionParticipation 재사용이 과거 기록을 planned/현재 시각으로 바꾸지 않는다.
- `0033_reapplication_history`는 현재 Assignment 부분 유일 인덱스에서 completed만 제외한다. 실제 조건은 `state <> 'left' AND state <> 'legacy_ended' AND state <> 'completed'`이며 기존 CHECK 안에서 active/stopped_incomplete만 점유한다. 새 테이블·컬럼·행 변환/삭제·과거 이벤트 backfill은 없다. readiness/베타/worker/관련 서비스는0033을 명시 지원하며 미지 head는 거절한다. 과거 head의 원 유일 제약 검사도 유지한다.
- 공개 경로·operation·요청/응답/ACK·오류 코드·wire2/profile1은 동일하다. 기본 OpenAPI 전체와 현재 OpenAPI의 paths/components는 불변이며 현재 정책 메타데이터에0033과 재참가 의미만 추가했다. **현재178/199·기본116/133**, 닫힌 베타 bundle·완결 예시130/원ACK32/음성3 검증 통과다.

격리 PostgreSQL의 **고유20PASS**: 신규14와 관련 기존6. 신규는 신청/승인, 직접가입·완료 캐릭터 거절/새 ID/old·N 행 불변/예약/원ACK, 직업·레벨·전투력3, pending 무점유/승인 전 변경, 설치 실패 롤백, 동시 재가입1승, 기존 자료 있는0032→0033 행/sequence 보존·old-event 기록/미지 head 거절, HTTP, 종료 근거 누락/다른 세대3, completed/left 다중 아이템이다. active/stopped 중복 인덱스 거절도 직접 확인했다. 관련 기존6은 같은 지속관계 재참가1·개인 완료 탈퇴/승계2·후보 페이지/쿼리수1·마지막 한도 동시승인1·분 일정 다인 동의 재평가1이다.

재현 RED1 후 신규 묶음8PASS(0032 거절의 반환 형태 기대1개 정정), 후속11PASS(HTTP historical reader의 필수 profile 누락1개 정정), 최종 해당 HTTP와 혼합 묶음2PASS를 합쳐 중복 제거한20이다. 서버 동작을 기대에 맞춰 완화하지 않았고 실패한 두 시험 호출은 기존 계약대로 수정했다. 합성 자료·인증 override HTTP이며 정상회원/기기 인수는 아니다. 전체 회귀·dump/restore·실회원 명령은 실행하지 않았다.

다음은 후보 소스/고정 패키지/두 계약 확인→API/동일 worker 잠시 중지→기존 DB의0033 인덱스 DDL→새 API/health/worker/읽기 확인→반영 기록 게시·Issue13 인계다. DB33에서 이전420e057 API만 재시작하지 않으며, 실패하면 자료·스키마를 유지한 전진 수정을 한다.

## 아래는 구현 전 설계 당시의 조사 기록

당시 실행API source420e057·이미지cd581ac0·DB0032를 유지한 상태에서 조사·설계했으며, 아래 미구현/미실행 표현은 그 시점 기록이다.

## 갱신된 요청과 확인 수준

원본은 [Issue13 전체182번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6435522815)이다. 작성2026-10-27 15:39:58 KST, 수정15:47:02 KST의 갱신본을 확인했다. 댓글 추가 없이 같은182에 결과가 덧붙었으며 전체 댓글은183개였다.

추가된 Native4833a164 결과: 확인창 오류라벨의 굵기/간격/배율 측정을 수정했고 TARGET_CONTEXT_STALE을 참가정보 재조회 안내로 구분했다. 서버 denied context에서는 POST0·미확인 슬롯 없음·다른 명령 사용 가능을 직접시험으로 확인했다. 111PASS/분석0은 Native 자체보고이며 Backend 재현이나 사용자 재신청 해결은 아니다. 기존 편성 잠금·계정 완료 탈퇴·추방/CN 독립 관리는 통과 보고로 보존한다.

제품 기준은 확정돼 있어 재승인할 정책은 없다. 과거 캐릭터 완료·참가 기록·해제 예약·N 참가는 보존하고 다른 적격 캐릭터의 새 C 신청/승인/가입을 평가한다. 같은 완료 캐릭터·직업/정원·입장레벨/전투력·다른 방 점유·한도·동의/권한을 완화하지 않는다.

## 정적으로 확인한 원인 경로

1. 개인 완료 탈퇴는 선택 Assignment를completed로, 실제 C CycleMember를cancelled로 남긴다. N 참가가 있으면 지속 Member는 유효하게 남는다.
2. 후보 evaluator는 현재active Assignment와 선택 캐릭터의 WeeklyState/점유를 평가해 다른 적격 캐릭터를 후보로 내보낼 수 있다.
3. admission-context와 신청/승인 검증은공통 admit_bundle에서같은지속Member/현재Round의과거Assignment를읽고old.state가left가아니면TARGET_CONTEXT_STALE로거절한다. 이조건은과거completed를새참가와분리하지못한다.
4. 코드조건만풀어도DB에서막힌다. 실행DB를SET TRANSACTION READ ONLY로조회해0032와아래실제인덱스정의를확인했다. 회원행/식별정보/환경값은조회·게시하지않았다.

`uq_recruitment_current_assignment(round_id,membership_id)`의현재조건은 `state <> 'left' AND state <> 'legacy_ended'`다. completed도유일성에포함되므로같은지속Member/Round에새Assignment를추가할수없다. CycleMember쪽은이미0031에서cancelled/removed를제외하는부분유일인덱스로바뀌어새CM을추가할수있다. ORM의과거전체UniqueConstraint선언과실제이행DB를혼동하지않는다.

또한record_bundle_join은membership_action표식이있는일부종료만새CM을만들고,일반cancelled/removed는기존CM을재사용한다. 개인완료탈퇴가남긴과거CM/배정을그대로보존하려면이연결도함께보완해야한다. 아직합성동선의실행재현은하지않았으므로실회원제보원인확정으로표시하지않는다.

## 수정 설계

### 종료 이력과 신규 참가를 같은 기준으로 분류

- 공통 재참가 판정을 두어 Member·실제T/현재세대·CycleAssignment의귀속·종료CM의ended_at/상태·해당revision의불변종료이벤트를함께확인한다. cancelled/removed의증명된종료만새참가로평가한다. 실제참가중/검토·완료유지/중단유지CM의기존차단을해제하지않는다.
- 과거Assignment가completed/left라는이유만으로무조건허용하지않는다. 바인딩누락·다른세대/귀속·종료근거불일치는기존오류/검토경계로처리한다. replacing/resuming의기존캐릭터변경·비활성재개동작은이새참가규칙에섞지않는다.
- 같은판정결과를후보공통평가·GET context/validate_only·신청쓰기·승인검토/실제가입·최종record_bundle_join이사용한다. 필요한근거는기존내부서명/스냅샷에결합하고새API필드를노출하지않는다. 신청pending은CM/Assignment/예약/한도를소비하지않으며승인시최신상태를재검사한다.

### 새로운 참가 식별자와 과거 기록 보존

- 유효한지속Member와방/주차/현재세대는유지한다. N의Member/CM/배정·리더·표/예약·revision을C재참가때문에교체하지않는다.
- 새C실제가입은새CM ID/가입순번과새Assignment ID를만들고새CycleAssignment로결합한다. 과거completed/종료CM/배정/바인딩을active로되돌리거나새캐릭터로덮지않는다. 여러아이템묶음도전부새참가로원자처리한다.
- 세션참여는기존재참가의revision/동의처리를사용하되과거Consent/해제예약/완료원장·불변이벤트는보존하고새예약은새CM/Assignment근거로저장한다.
- 과거anchor의record가현재재활성화된SessionParticipation이나변경된일정때문에planned/새시각으로바뀌지않게한다. 종료이벤트의record snapshot을우선하고기존개인완료탈퇴자료는그CM의과거Assignment에귀속한불변해제예약의시각으로투영한다. 증거없는시각은기존nullable필드로남기며새자료를만들거나과거이벤트를backfill하지않는다.

### 최소 DB 제약 변경 — 0033

- 새migration `0033_reapplication_history`에서현재Assignment유일인덱스의조건만 `state IN ('active','stopped_incomplete')`로바꾼다. active중복방지와중단상태의점유보호는유지하고completed를현재참가의유일성에서제외한다. 활성슬롯·CM·주간점유·FK/감사보호제약은그대로다.
- 기존0031/0032 migration은수정하지않는다. 새컬럼/테이블/행변환/삭제·dump복원은없다. 이변경은새기능의기록/현재점유를구분하는DDL이며개발자료를살리기위한이전통로가아니다.
- 새스키마head를명시적으로지원하도록startup/readiness·베타가용성·worker/관련서비스의head검사를맞춘다.알수없는head를단순>=비교로허용하지않는다. 인덱스predicate도검사하고ORM의관련현재정의와실제DB를일치시킨다. 기본0023앱/기존자료읽기경계는유지한다.
- 공개경로·요청/응답/ACK/오류코드·wire2/profile1·후보역할/제외집계·cursor는보존하고실행계약의스키마메타데이터/내부판정설명을갱신한다. 지원하지않는DBhead에서새쓰기를허용해unique500을내지않는다.

## 직접 검증과 완료 기준

처음에승인된베타C/N동시생성·양계정양주차참가→A의C개인완료탈퇴/승계·N보존→B의C만신청모드변경/위임→A다른캐릭터후보와GET context불일치를합성PostgreSQL/HTTP로실패재현한다. 같은원자료fixture에서수정후후보→허용context→신청pending→검토/승인→새C참가·예약까지성공해야한다. direct_join은같은새참가판정으로대조한다.

- 과거CM/Assignment/바인딩/완료·이벤트/해제예약의행내용과기록anchor응답이불변이고N의업무상태도그대로인지비교한다. 새CM/Assignment/가입순번·새표복사/예약/동의는별도여야한다.
- 같은완료캐릭터·직업중복·입장레벨/전투력·다른방점유/한도·자격/권한·마감거절,누락/손상바인딩·다른세대근거를검증한다. 현재실제참가·completed/stopped유지관계를새가입으로오인하지않는다.
- 다중아이템의일부완료/나머지left,신청당시허용후승인전조건변경·모드변경·권한승계,동시승인/가입·마지막자리·실패롤백·원ACK재생무변경·한도같은방중복차감없음을직접확인한다.
- 0032→0033을격리DB에서한번검증해기존행불변·완료이력과새배정공존·active/stopped중복거절·startup/worker/ready와두OpenAPI/닫힌DTO일치를확인한다. 기존탈퇴/추방·일반재참가/기록reader·분시간/조율의직접영향만선택한다. 전체회귀·전체덤프복원리허설은반복하지않는다.

구현승인후같은수정브랜치에서구현/DDL/계약/직접검증/기록을작업구간으로묶어commit/push·원격확인하고Issue13에인계한다. 현재설계기록은로컬누적이며기능구현/시험인계를위한commit/push는아직없다.

개발반영계획은후보소스/패키지/계약검증완료→API/동일worker잠시중지→기존DB컨테이너/자료/키/환경을유지한0033 DDL원자적적용→새API시작·head/인덱스/health/로그/읽기조회확인이다. 기존420e057은0033 readiness를지원하지않으므로구이미지만단순재적용하지않는다. 문제시자료와0033구조를유지한전진수정이며DB초기화/과거덤프복원/무검증다운그레이드는하지않는다.

실회원제보요청을재전송하거나회원자료를시험용으로고치지않는다. 완료는합성재현해결·검증·게시·개발반영·인계이며정상회원/기기성공과구분한다. dev/main병합·AWS배포·기존전체인수는이번후속의별도범위다.

[전체184번째 Backend · 재신청 정적 조사/수정 설계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6435892485)에갱신수신·정적/DB구조확인·0033설계를회신하고실제전체순번/본문을확인했다. Native추가시험요청없음·다음Backend합성재현/구현·직접검증단계다.
