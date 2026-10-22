# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

[실제 자료 영향·복원 리허설](../ISSUE_13_W5_RESTORE_PREFLIGHT.md) 완료: source83표/414행·시퀀스1·인증 키4개·환경/실행 설정 보관, 제한 app LOGIN의 복원본0029 이행/기존82업무표 보존·별도0023/구 이미지 복구·읽기/worker 불변 확인. 보호 unittest7PASS. 검증용 컨테이너/DB/network만 정리했고 비공개 백업은 `backups/`에0700/0600으로 보관한다. 문서/도구 commit/push·Issue 결과 게시 준비다. 이전 W5 자동304고유 검증과 별도이며 실제 개발 서버/DB 전환·Flutter 적용은 미실행이다.

착수/인계 시 AGENTS → 협업 규칙 → 이 문서 → AI_CONTEXT → 계약3판/4판/ACK를 읽고 Issue 본문/최신 댓글·Git/코드를 확인한다. 최신 공식 기록은 [전체90번째 Backend · W5 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6331483028)이며 추가 제품 입력/동일 계약 회신 대기는 없다. 계약0.4.1/policy two-cycle-contract-4를 유지한다.

## 다음 Backend — 개발 DB/API 실제 전환·소비 가능한 구간 인계

1. **대상/영향·승인 범위 확인**: 로컬 개발 DB0023→0029·API8000/worker 동시전환이 다음 구간이다. source는 여전히 API114경로/구 이미지/healthy다. 과거 모집7건은 C/N 밖·stopped 원천이며 새 C/N 공개 검색은0건(구 검색7건), persistent 관계7개/원본·ACK는 보존한다. 현재 plan은 TARGET_NOT_OPEN이고 영향0의 본인 leave-context는 허용되지만 실제 명령은 실행하지 않았다. 이 목록 차이를 전환 인계에 포함한다.
2. **직전 checkpoint·실제 전환**: [복원 리허설/전환 순서](../ISSUE_13_W5_RESTORE_PREFLIGHT.md)의 검증된 후보 이미지·자료/키/환경 보존과 복구 지점을 사용한다. 현재 source 실행 중 백업은 리허설 snapshot이며 전환 checkpoint가 아니다. 구 API/모든 worker 정지 후 새 백업을 확정하고0029 이행/보존·factory/새 worker 동시기동·health/계약/인증/v1/C/N을 검증한다. [compose.two-cycle.yaml](../../compose.two-cycle.yaml)은 진입점 override이며23이미지/구 worker를29와 혼용하지 않는다. 실제 source drop/초기화/downgrade·운영변경으로 확대하지 않는다.
3. **복구/쓰기 경계**: 새 쓰기 허용 전 실패는 승인된 checkpoint를 별도 DB에 복원·검증 후 연결을 전환한다. 새 쓰기 이후는 snapshot 복원으로 새 자료를 버리지 말고 영향/보존 범위를 확인한다. 실제 실행 SHA·이미지/DB·보존·검증 결과를 기록한다.
4. **실제 소비 증명 후 Flutter 인계**: 서버 경로/실행 SHA·고정 계약·확인/미확인을 준비하고 commit/push·원격 확인 후 같은 Issue로 메타/summary·주차 선택·계정 캐시 격리와 필요한 구간만 요청한다. v1 위험 방 쓰기409 CLIENT_UPGRADE_REQUIRED·원 ACK 우선·본인 수동 C/수10시와 개인표 유지·과거 모집7건 목록 차이를 포함한다. 현재 소스/리허설만으로 새 서버 시험을 요청하지 않는다.

추가 제품 입력/동일 계약 재회신 대기는 없다. 실제 개발 DB/API 전환·Flutter 적용·실회원/provider/기기·운영 인수는 미완료이며 #19 통계는 별도 후속이다.

## 유지할 기준

- 06시 N→C는 같은 실제 UUID/세대·리더/순번·Assignment/세션·동의/예약이다. 새 N 자동 생성/가입0, 지난 실제 T만 정리하며 부적격/unknown source는 증거·lease를 보존해 review로 둔다.
- G1은 C 행이 없을 때만 N이다. 공통/전역 GlobalScope·persistent CAS/영향0·120초 context/원 ACK·완료 이력을 보존한다. GET/summary는 READ ONLY이며 실제 참가/점유가 현재 세대 declined/legacy intent보다 우선한다.
- 추가 DDL/계약 변경은 없다. 고정53경로/56동작/204schema·canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`을 유지한다. 기본116/준비167경로는 소스 계약이고 실제114경로 이미지는 미전환이다.
- [측정 artifact](../design/issue13-w5-performance.json)는 합성 자료·서비스 호출/SQL 반환 rows/compact JSON bytes 기준이다. 구 실행 이미지 전체/실제 서버·provider/기기 성능이나 SLO를 대체하지 않는다. 검증/게시 이력은 [DEV_LOG](DEV_LOG.md) 기준이다.
