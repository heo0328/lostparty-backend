# 캐릭터 관리 v2 계약 후보 산출물

Issue53 전체14·15의 정적 소비 대조용이다. **신규 관리 API는 로컬 구현·격리 검증/반영 단계다. [최신 구현/한계](../character-management-implementation.md)를 따른다. 미커밋·미push이므로 원격 고정 구현으로 인계하지 않는다.** 기존 예약 GET의 구현 완료와 혼동하지 않는다. 로컬 현재 앱 OpenAPI를 함께 갱신했고 기존 게시 명세는 아직 변경되지 않았다.

- [Schema](schema.json): `$defs.Context`는 GET/성공PUT, `$defs.PutBody`는 요청, `$defs.Error`는 아래 기본 오류 예시용 envelope다.
- [완전 합성 예시·상태 전이](examples.json): 일반설정/초기설정/재설정/잔여참조, 순서 생략·빈배열·거절·no-op·옛ACK/현재GET·409/명시재시도.
- [비교 fixture](comparator-fixtures.json): null·비수치/비유한·동률·비ASCII/UTF-16 비교. comparator의 짧은id는 순수 정렬 라벨이며 API의 canonical UUID 예시가 아니다.
- [검증 도구](validate.py): `python3 docs/features/rosters/activity-and-presentation/character-management-contract/validate.py`. 문서 Schema/예시/의미검사만 하며 서버·DB·Flutter parser를 시험하지 않는다.

## GET 집합 불변식과 재설정

GET의 scope는 현재 소유원정대의 실제 버전이다. characters와 ordered_all_character_ids는 비퇴역 canonical 전체문맥을 동일 순서·동일 ID 집합으로 제공한다. usable=true이면 blocked_reason=null, false이면 CHARACTER_UNUSABLE/IDENTITY_CONFLICT 중 현재 실제 사유다. unknown usable을true로 합성하지 않는다. 읽기 소유권없음은전체403이다.

activity_character_ids와 representative_character_id는 **현재 저장한 설정 값**이다. 모든 configuration_state에서 활동 ID가 현재 비퇴역문맥 밖에 있거나 unusable이고 대표가 null/활동 밖/비퇴역문맥 밖일 수 있다. GET은 이를 자동삭제/대표대체하거나 configured를 정상이라고 가정해 거절하지 않는다. 저장state를 임의 configured/needs_reconfiguration으로 다시 쓰지도 않는다. 다음 상태표를 따른다.

| 상태 | 읽기·화면 처리 |
|---|---|
| unconfigured, 빈활동·대표null | 일반 최초설정. 성공GET의 실제기본version1, 추천draft는읽기만으로저장하지않음 |
| unconfigured, 잔여활동/대표 | 저장값보존·복구draft. 정상 configured의집합포함검사로화면차단금지 |
| needs_reconfiguration, 누락/퇴역ID·unusable | 현재문맥밖 activity IDs는 `activity-set - characters-set`, 대표이상은 null/비활동/문맥밖/unusable로 파생해 경고. 빠진ID에가짜characters행을만들지않음 |
| configured, 이후자격/문맥변경으로불완전 | GET은같은느슨한잔여집합규칙으로허용. state문자열만으로쓰기유효성을보장하지않음 |

이 허용은 타원정대 ID를 보내도 된다는 뜻이 아니다. 저장참조는해당소유원정대의과거 canonical ID여야하며 실제다른계정/회원참조 모순은503 SERVICE_UNAVAILABLE 후보로닫고유출하지않는다. 퇴역ID표시를위한추가상세조회나빈이름캐릭터는생성하지않는다.

PUT은 항상 최종활동1..200·본인원정대 현재usable·대표가최종활동안에있음을엄격검사한다. 기존잔여를자동OFF/삭제하지않고사용자의명시완성된의도를받는다. 순서가있으면정확활동-대표 집합(최대199)이며생략과빈배열을구분하고null은거절한다. 같은valid configured의동일명령은no-op, 초기상태를configured로바꾸는명시저장은의미변경이다.

## 비교값과 관측

rank(null후순위)→정규decimal레벨내림차순(null후순위)→이름UTF-16 code-unit 오름차순→canonical UUID이다. 대표는렌더링앞고정이며원장rank0으로저장하지않는다. 숫자는유한비음수문자열만정규화하고비수치/비유한은null이다. 부호없는정규형·소수끝0제거·0만의값은'0', 길이64초과정규값은null로정렬한다. GET wire는정규숫자문자열/null만내며Native는double로되돌려재정렬하지않는다. 매우큰지수/입력길이의파서자원제한은실제구현에서provider/기존DTO와맞춰검증할항목이며문서도구를서비스parser로사용하지않는다.

동일GET의전체목록/정렬필드를첫드롭기준으로사용한다. 순서지문은관측ID/rank/정규level/name·정책/회원/소유세대를포함하고시각/role/visible은제외한다. GET/ON·OFF/대표변경/동일드롭은순서쓰기없음, 실제달라진드롭만movable슬롯을교체해정규화한다. 새캐릭터/관측레벨/이름변경은옛지문409이며최신기본순서로옛드롭을자동재해석하지않는다.

## 오류·멱등·게시 상태

413 CHARACTER_CONTEXT_TOO_LARGE는전체문맥1001 sentinel이며무음잘림/일부분저장없음. 문맥1000/활동200은별개다. 기본오류는기존code/message/request_id, HTTP409 REQUEST_IN_PROGRESS는기존 Retry-After 헤더를사용한다. 레이트제한은기존429 envelope의retry필드정책을그대로따르므로이문서의기본Error정의를기존모든API오류의재정의로쓰지않는다.

동일key+본문은원ACK(24시간기존보관정책), 동일key다른본문409 IDEMPOTENCY_CONFLICT, 기존기한초과409 IDEMPOTENCY_EXPIRED이다. 복구·409·세대불확실의다음GET은현재상태확정용이며ACK를현재응답으로재작성하지않는다. GET실패를저장실패/빈값으로바꾸거나PUT를새key로자동중복실행하지않는다.

모든예시의지문/ID/이름은합성이다. 지문'a'64는형식예시이며실제서명/원장hash의증명이아니다. **현재 파일은 미커밋·미push이고55923cc/fe5e082의게시파일에포함되지않는다.** 계약작성당시 미수행이던 실행/동시성 검증 결과는 최신 구현 문서를 따른다. DB초기화불필요·미실행,추후필요시대상/영향과사용자사전확인필수다.
