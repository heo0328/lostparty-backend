# Issue #13 W2-B — 주차별 생성·조회·일반 참가

2026-10-21 / `feat/raid-recruitment` / 구현 검증 기준 HEAD `6490f69` 이후 변경.

후속 사용자 지시에 따라 W1/W2 및 선행 계약을 이 기록을 포함한 완료 구간 커밋으로 보존한다. 미push·서버 미반영이며 아래 미커밋/커밋 없음 표기는 구현 종료 당시 기록이다.

**합의 계약의 W2-B 범위를 로컬 구현하고 격리 PostgreSQL/후보 HTTP 앱에서 검증했다. 실제 서버 공개·Flutter 적용·운영 완료는 아니다.** 기준은 [계약4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md), [ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), [전체84번째 Flutter 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)이다. 다음 작업은 [W3](ISSUE_13_TWO_CYCLE_WORK_PLAN.md)다.

## 구현 범위

후보 `cycle_router.py`는 **17경로/19동작**이다. 기존 main에는 등록하지 않았다.

| 경로·동작 | 구현 |
|---|---|
| GET creation-context / POST raid-rooms | 예정 Room/주차/Item/Round UUID·실제 weekly revision·C/N 선택 검토, 단일 명령 원자 생성 |
| GET raid-rooms / POST search / GET room | 명시 target 목록·카드, 숙련도 OR/null 저장값·남은 자리·인원 정렬·그룹 회원/캐릭터 SQL 필터·cursor |
| GET detail / GET private plan | target generation의 실제 참가·자리·리더·계획·본인 assignment/participation |
| GET filter-context / GET group member-projections | 기존 그룹 권한 snapshot 재사용, 실제 target 참가자/선택 캐릭터 projection |
| GET admission-context / POST join / POST applications | 대상 주차의 자격·전투력/활동·소유·한도·CAS·일정 마감·전체 묶음 검증 |
| GET application / POST approve/reject/withdraw | 소유자·해당 주차 공대장만 조회/처리, 승인 직전 최신 자격 재검사, 최소 조회와 공대장 검토 응답 |
| GET own memberships / GET own·room applications | persistent 관계와 실제 target 참가 구별, 주차별 신청·만료·cursor |

`0025_cycle_admissions`는 신청·Session·Segment 소유를 위한 **추가3표**만 만든다. 기존 신청의 방/회원 pending 유일 제약을 변경하거나 과거 기록을 새 주차 신청으로 복사하지 않는다. 새 신청은 `(cycle,generation,user)` pending 유일 제약이며 Session/Segment에는 정확한 방·주차·세대·Round 복합 FK를 둔다. 새3표의 DB 기록시각·readiness도 확인한다. 0024/0025에서 구 API 활성화/worker는 계속 거절한다.

## 명령·조회 의미

- 생성 미체크는 T만, 체크C는 C/N 둘 다, 체크N은 N만 생성한다. 미체크N effect는 `target_only`, 체크N은 `target_is_next`다. 체크C만 context의 `next_cycle_creation.selection`을 `continuation.next_selection`에 그대로 제출한다. 대체 N 캐릭터의 소유/활동/역할도 사전 검토한다.
- context는 actor/명령/T/체크·대체선택/예정ID·전체 묶음·카탈로그/그룹·소유/활동/한도·원장·power source에 결합한 120초 이내 AEAD token이다. 현재 C 종료보다 길게 유효하지 않다. GET은 RR/READ ONLY이며 source/default/dedup/예약 행을 생성하지 않는다.
- 원키·불변본문의 ACK 복구를 context 만료·주차·권한 재검사보다 먼저 한다. 같은 예정 Room UUID를 새키로 재사용하면 `CONTEXT_ALREADY_USED`로 거절한다. C/N 성공·초기 target/members/plan revision1·각 주차 첫 리더/순번1을 한 transaction으로 확정한다. N 실패/마지막 마감·06시 경계 실패는 C·N·원장·준비 ACK를 모두 rollback한다. 생성 오류에 허용된 최소 conflicts/failed_cycle_key를 제공한다.
- global Room revision은 공통 정보, members/plan/target revision은 T의 값이다. 정원/입장 모드/숙련도/전투력과 기간 근거는 T snapshot을 사용한다. C/N 같은 방의 persistent 관계는 하나여서 방 한도를 두 번 사용하지 않는다. target 쓰기가 반대 주차 revision/head를 올리지 않는다.
- 실제 참가 수는 target/current generation의 활성 Assignment와 정확한 WeeklyOccupancy를 가진 고유 관계다. persistent 회원이나 과거 함께하기 의사를 인원으로 세지 않는다. 신규 참가의 전체 묶음·역할 편성·선택 역할의 최신 성공 전투력·소유/생명주기·주간 원장 CAS를 한 transaction에서 검증한다.
- pending 신청은 점유·참가순번·예약을 만들지 않는다. N 신청 만료는 N 종료이며 현재 C 종료가 아니다. 승인은 저장된 공개 신청 출처를 서버에서 확인하고 최신 소유/활동/전투력·전체 묶음·정원·마감·target/leadership CAS를 다시 검사한다. 이후 group scope로 바뀐 공개 출처 신청의 예외를 보존한다.
- 생성의 수동 일정은 target 실제 날짜·수10시·개시+30분 floor·5분 정렬·최대24시간·cycle 끝을 검증한다. 수요일00~05:55는 해당 실제 cycle의 마지막 수요일이다. C의 명시 새 수동시각은 본인 확인/예약, 복사한 N은 `confirmation_pending`·예약0이다. 기간·정책 근거는 T별 보존한다. 조율 후보 평가·추가 일정 명령/worker는 W4다.
- 검색의 가시성/회원·캐릭터/숙련도 OR/남은 자리·인원 정렬은 SQL pagination 전에 적용한다. `unrestricted`는 실제 null만, OR 순서만 바뀌면 같은 cursor, null/중복/미지 enum은 거절한다. cursor는 회원·세션·T·현재 C·그룹 권한/필터·T directory head와 결합한다. N 변경으로 C cursor를 무효화하지 않는다.
- 일반 상세는 방 가시권한에 따른 안전한 projection이다. 비회원의 build/현재 자격 비교는 숨긴다. private plan은 persistent 관계와 **그 T 실제 관계**를 모두 요구한다. C 리더/회원이라는 이유만으로 미참가 N private plan을 열지 않는다. 편성은 실제 party/slot 그대로이며 리더를 1번 슬롯으로 옮기지 않는다.

## 계약·재현

`cycle_wire.py`는 고정 전체 계약의 참조 schema에서 생성한 정적 DTO다. 실행 앱은 docs를 읽지 않는다. 생성 도구는 별도 tooling venv의 `datamodel-code-generator==0.86.0`으로 실행한다.

```sh
python docs/design/build_issue13_w2_models.py --generator /path/to/tooling-venv/bin/datamodel-codegen
```

다른 출력 경로는 `--output`으로 지정한다. `cycle_schemas.py`는 canonical 수요일 날짜와 strict 요청 검증을 보완한다. HTTP 중복 JSON/일반 query·헤더/예상 외 필드/크기 제한은 유지하고 GET 목록의 `experience_levels` 반복 query만 허용한다. 기존 route의 기본 반복 허용 집합은 여전히 비어 있다.

합의 계약은 0.4.1/policy4·53경로/56동작/204schema·canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`로 변경하지 않았다. **실행 원본은 W2-A의116경로 그대로**다. 후보 오류/입력/성공 응답은 고정 계약의 실제 schema/ref/format으로 검증한다. 전체56동작의 FastAPI 일치나 실행 서버 준비를 뜻하지 않는다. `jsonschema==4.26.0`을 테스트 의존성에 추가하고 테스트 이미지에 고정 계약을 포함했다.

## 검증

- W2-B 신규 **35PASS/187.90초**. 이전24PASS와 추가 경계·경합11PASS는 이35개와 중복이므로 합산하지 않는다.
- 그룹 projection·공대장 신청 검토 응답과 N 미체크 effect를 보완한 뒤 관련 **6PASS/34.78초** 재검증. 신규 고유 사례는35개 그대로다.
- 제한 LOGIN의 독립 DB에서 0025까지 이행, 기존 실제 표의 모든 열 지문 보존, 새 모델/FK/시각/readiness와 구 활성화 차단을 확인했다. C/N 원자성·최종 ACK rollback·대체 캐릭터·원 ACK 우선·개별 신청·승인/거절/철회·최신 권한·실제 원장 수를 확인했다.
- HTTP 생성→상세/계획→검색/목록→참가/본인 목록과 오류 응답, 그룹 projection/공대장 검토를 합의 schema에 직접 대조했다. 한 자리 동시 참가 2요청 중1개만 성공, OR 순서 정규화·N/C cursor 격리, 비공개/그룹 권한 소멸·member/character 필터, 조회 지문 보존을 확인했다.
- 기존 W1 cycle·W2-A summary·v1 생성/일정/개인표·계정 bootstrap/기록시각 **121PASS/220.02초**. main/FastAPI와 실행 OpenAPI116경로의 전체 일치도 포함한다. 이번 확인 범위는 신규35+회귀121의 고유156사례이며 단일156개 실행 결과가 아니다. 앞선 W1/W2-A 기록의 수와 중복 합산하지 않는다. 기존 BlockingPortal deprecation 경고1건만 남았다.
- Python AST·문서 링크·`git diff --check`·고정 계약 hash 확인 통과. 실제 서버/provider/실회원/기기/운영 성능 측정은 하지 않았다. 테스트 중 bootstrap 최대 합성4000캐릭터 측정 출력은 기존 시험의 재실행이며 W2 검색 성능 수치로 쓰지 않는다.

## 다음 Backend·게시 경계

다음 **W3**는 명시 N개방/재개·기존 C 참가자 N즉시참가·B충돌보존/대체·T 취소/재참가·공대장 승계/위임이다. 취소된 기존 Assignment의 UNIQUE를 지키며 재활성화/새 joined_order·이벤트를 기록하고 완료 이력을 부활시키지 않는다. 다음 W4는 조율/제출표·확인/완료·공통 명령·06시 worker/v1 adapter·legacy review 해소다. 현재 조회는 새 명시 open generation 중심으로 검증했으며 이행된 review/닫힘/취소 세대의 실행 경로와 계획 명령 권한은 W3/W4에서 완성한다.

원본 OpenAPI/실제 소비 가능 경로·게시 SHA가 준비되면 검증된 구간을 묶어 commit/push·원격확인 후 Issue #13에 인계한다. W5까지 무조건 기다리는 규칙은 아니다. 이번은 미완성 worker/호환 계층 때문에 서버 공개/네이티브 시험을 요청하지 않았고 기존 개발 DB·API 이미지/컨테이너·사용자 자료를 바꾸지 않았다. 새 Issue 댓글·commit/push·merge·배포도 없다.
