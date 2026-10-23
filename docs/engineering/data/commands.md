# 공통 업무 명령·읽기·데이터 책임

<a id="section"></a>

## 명령과 재시도

업무 쓰기는 서버 세션에서 actor를 결정하고 명령별 엄격 입력·UUIDv4 Idempotency-Key·기대revision을 사용한다. 신규 선택과 응답 유실 복구를 구분한다. 같은 operation/회원/key/body는 당시 결과를 복구하고 다른 body는 IDEMPOTENCY_CONFLICT다. 명령군별 정확한 권한/입력/원ACK 우선순위는 해당 계약을 따른다.

일반 업무 멱등 저장소는24시간 성공 응답 복구·이후 tombstone과 lease/generation fencing을 사용한다. 진행 중 REQUEST_IN_PROGRESS/Retry-After, 만료 IDEMPOTENCY_EXPIRED와 사용자 재결정이 필요한 revision 충돌은 다르다. 인증 refresh의60초 복구와 이 업무 프로토콜을 섞지 않는다.

<a id="section-2"></a>

## 트랜잭션과 읽기

업무 상태·현재 사용량/목록head·감사·명령 결과는 같은 트랜잭션으로 저장한다. 여러 공개 명령을 차례로 호출해 원자 명령을 흉내내지 않는다. 네트워크 호출을 업무 DB잠금 안에서 수행하지 않으며 외부 관찰 뒤 반영 직전에 세션·자격·키 버전을 재검사한다.

조회는 권한 있는 저장 원본의 snapshot을 읽고 참가·설정 기본행·예약·재개 제안을 만들지 않는다. 복합 조회는 명시한 READ ONLY/REPEATABLE READ 범위를 유지한다. context는 읽기 시점의 동의 근거이며 쓰기는 최신 조건을 다시 검사한다.

<a id="section-3"></a>

## 응답과 보존

no-store와 공개 안전 error.code/request_id를 사용한다. 원문 토큰·키·SQL parameter를 응답/로그에 넣지 않는다. 원 ACK는 과거 성공이며 현재 GET·현재 권한과 구분한다. 쓰기 성공 후 후속GET 실패가 성공을 취소하지 않는다.

현재 권한 상실과 과거 완료/감사 삭제를 혼동하지 않는다. 이름·클라이언트 snapshot으로 다른 canonical ID나 소유권을 만들지 않는다. nullable/미지원/검토필요와0·정상·관계없음을 합치지 않는다. [DB 기록 시각](record-timestamps.md), [품질·UX 기준](../development/quality-and-ux.md).

실행 계약의 각 operation이 구체 규칙의 원본이다. 이 문서는 기존 계약의 공통 책임을 설명하며 모든 API에 동일한 검증 순서·오류를 새로 강제하지 않는다.
