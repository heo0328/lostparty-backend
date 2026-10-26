# 1차 기기 차이 조사·문자 정책 보완

2026-10-26 / 작업 구간 **기기 차이 실자료 조사·문자/목록 보완·인계** / `feat/raid-recruitment`.

대상 요청은 [전체162 Flutter 기기 차이](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6409130575)·[전체163 native 수정/조사 대기](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6409312568), 중간 회신은 [전체164 Backend 조사·join 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6409485714)이다. 실제 개발 d95e3827/이미지f458e6d5·DB0032를 REPEATABLE READ/READ ONLY로 조사했다. [공개 집계](../../../engineering/operations/records/device-feedback-investigation.json)를 함께 따른다. 실자료·원키/ACK 변경이나 명령 재실행은 하지 않았다. 민감 원문은 비공개 임시자료에만 보관하며 아래는 집계/정책 근거다.

## 여섯 항목의 결론과 책임

| 항목 | 확인 결과·다음 행동 |
|---|---|
| 참가한도 | 기본10/사용10. beta3개 지속방(C/N 표시4건)+이전10/14 review_required 미종료관계7개다. 종료8관계는 제외·C/N 및 생성/참가 중복 없음. 현재 집계식의 누수 근거 없음. C/N 표시와 전체 지속관계가 다른 것이며 미종료관계의 집계 제외/종료를 임의 수행하지 않는다. 개발자료는 beta 전 폐기 방침이며 이를 위해 변환/이중운영 통로를 추가하지 않는다. |
| 번호5 후보 | direct_join·kazeros_act4 hard/catalog2026.08.20/최소1720. 제보 저장레벨1704.00은 같은 evaluator에서 RAID_ITEM_LEVEL_REQUIRED다. join의 일반 characters 목록은 필터후보 API 경로가 아니다. 아래 join intent 제안을 소비 확인 후 구현하며 apply 위장/반복 context/앱재계산을 하지 않는다. |
| 자동조율 | 현재 번호3(30분)/5(20분)는 threshold2/참가2지만 공통표 유효시작0. 번호4는 공통후보131개이나 threshold3/참가2. 복사표와 최신개인표 버전 차이는 자동전파하지 않는 계약이다. worker 성공 확인. 현재 snapshot이며 과거 합류시각의 모든 표/예약 복원 근거는 아니다. |
| 개인표 ACK | 제보 회원의 beta-v2-submission 성공1건은200/revision2/source_personal_version5, availability_copy=null·대상 BetaSchedule 없음이다. 요청profile만으로 beta 대상이라고 가정하면 안 된다. beta 대상은 자동신규1/명시기존+1, 기존일정은 개인표 버전 변경시에만 갱신/동일버전 no-op이다. 이 ACK와 실제 미확인 journal 원키의 일치는 입력 부족으로 미확정. 원ACK 변경/원키교체/삭제·명령재실행 없음. |
| 문자 | 사용자 최신 지시로 한글완성형/호환자모+ASCII U+0020~007E 전체로 확대. NFC→허용검사→일반공백trim→20코드포인트, 빈memo/null·빈preset불가,4096UTF8byte/32768body·앱로컬금칙어 유지. 요청원문은 보존한다. |
| 오류 | 한도/레벨/일정/권한/CAS/멱등 등 기존 구체코드를 유지하며 새 미적용 추정 allowlist는 추가하지 않는다. 실제 로그의 내모집500을 재현했고 아래 목록 결함을 보완했다. 원인 불명 서버예외를 앱 입력오류/확정미적용으로 둔갑시키지 않는다. |

## 직접 수정·계약

- 종료된 지속관계에 선택 주차 CM이 없는 membership-actions 목록의 projection이 cm.generation을 참조해 AttributeError/500이 발생했다. 알려진 세대가 있을 때만 비교하도록 수정했다. content=null·relation_only·비공개 번호/메모 경계를 유지하며 기존 자료를 보정/생성하지 않는다. 기존 실자료 서비스 조회는 C/N×current/ended/all×두 reader12개 중 membership-actions ended/all4개 실패→별도 프로세스에 수정 함수를 로드한 읽기 전용12개 모두 PASS다. 실제 API 프로세스/파일 교체는 아니다.
- beta_text는 ASCII 기호 전체, Memo/MemoStored와 preset 저장응답은 같은 허용범위를 사용한다. 저장문자 DTO는 NFC/trim/20자와 제어문자 제외를 검증하며 요청은 정규화 전 원문 digest를 유지한다. 메모/문구의 성공 ACK나 과거 제출본을 다시 쓰지 않는다. 추가 DB migration/테이블/패키지 변경은 없다.
- wire2/profile1을 유지하고 `hangul-printable-ascii-1` 보완표식을 실행 OpenAPI에 둔다. 원267afe5의 계약/이전SHA는 당시 기준이고, 이번 문자 보완의 정확 소스SHA와 고정 링크는 최종 회신에서 구분한다. 제안 Memo/MemoStored·공통32벡터(ASCII95문자 전체 포함)·wire 생성물을 함께 갱신하고 동결 base-openapi.gz는 그대로 둔다.

## join 후보조회 제안·미합의 경계

기존 GET admission-character-candidates의 query와 data.intent에join을 추가하는 최소안이다. direct_join만, mismatch는409 ADMISSION_MODE_CHANGED, actor=null. 기존 apply/change_character와 동일 실제T/소유/레벨/역할전투력·완료/점유/정원·배치 evaluator를 재사용한다. shape/정렬/페이지/exclusion·정책admission-eligibility-2는 유지하고 snapshot/cursor는 기존대로intent/profile에 바인딩한다. 전체한도/일정/최신권한은 선택 후 join context/POST에서 확정한다. 소비 확인 전 구현/실행 OpenAPI에join을 추가하지 않았다. 다음 담당은 Flutter의 최소안 소비 확인→Backend 구현/직접검증/게시·인계다.

## 검증과 인계 범위

직접영향 고유7개 시험 PASS: 문자32벡터/저장DTO, 새기호 preset 저장·원본문멱등, 메모 pending/승인 snapshot, closed reader matrix, 종료관계/선택CM없음 목록, 기존일정 명시복사 no-op, beta 자동신규1/명시기존+1·원ACK재생이다. 최종 문자벡터1건 재확인은 중복 합산하지 않는다. 실행 OpenAPI 기본116/133·현재178/199 전체일치/기존612 schema 보존, 제안48/문자32·66operation/118fixture·원ACK32동일성, 문서/링크·diff 검사도 PASS다. 기존 Starlette/AnyIO 경고는 유지하며 무관 패키지 변경은 하지 않았다. 정확 source/commit/push는 최종 회신에서 함께 기록한다. 직접시험만 수행하고 기존 전체모집 회귀를 반복하지 않는다. 후보 소스와 실제 서버반영, 합성계정/서비스조회/실제HTTP·기기 인수는 구분한다. 이번 요청은 원인대조/필요구현 인계이며 서버교체·실회원자료 변경/배포는 요청하지 않았다. 따라서 실제 개발은 기존d95e3827/DB0032를 유지한다. 새 ASCII 저장/목록 보완은 소스 인계만으로 실서버 성공이라 보고하지 않는다. dev/main통합·AWS배포·자료삭제 없음, Issue13 OPEN·기기 나머지/완료해체/두주차 인수는 미완료다.
