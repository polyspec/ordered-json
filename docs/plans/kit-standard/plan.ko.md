<!-- doc-id: plan-kit-standard -->
<!-- source-sha256: 06eb99dfe4bf5fd4729faf2860440c050bd777ce47ff8b50ab243ab0310689e8 -->
# kit 표준

[English](plan.md)

## Prerelease reconsideration

0.0.10 이전 점검은 완료한 작업, 대체된 요구, 조건부 철회와 아직 증거가 필요한 작업을 구분한다. 과거 철회 이력도 이번 재검토에서 제외하지 않는다.

| Item | Review decision | Remaining condition |
| --- | --- | --- |
| T2.56 | Go 오류 처리 범위는 완료한 T2.57이 포함한다. 통합 기록을 유지한다. | 새 오류 처리 결함이 있을 때만 후속 항목으로 다룬다. |
| T2.65 | [Artifact proof](../../operations/distribution.ko.md#tag-release)가 요구하는 Composer archive consumer를 유지한다. Artifact 검증을 소스 설치로 대체하라는 요구는 철회한다. | 실제 패키징한 ZIP의 consumer 설치가 통과해야 한다. |
| T2.66 | 같은 artifact proof가 요구하는 npm tarball consumer를 유지한다. 개발용 소스 link는 범위가 다르다. 대체 요구는 철회한다. | 실제 tarball의 consumer 설치가 통과해야 한다. |
| T2.79 | Report 테스트는 Makefile이 include하는 형제 kit.mk를 읽으며 소유 workflow 테스트 20개가 모두 통과한다. | 이 경로 수정에 남은 조건은 없다. |
| T2.80 | 원래 철회는 CI 계획이 없다는 조건에 따른 것이었다. 이제 [실행 계획](../execution/plan.ko.md)이 있으며 T2.80-1이 공용 수정 반영을 추적한다. | Kit patch set을 통합하고 canonical workflow를 반영한다. |
| T2.48 | 동시 작업 부하가 높은 상태의 benchmark는 신뢰할 성능 증거가 아니다. 기존 결과를 유지하되 재측정 성공으로 주장하지 않는다. | Load average가 2 미만일 때 clean checkout에서 make benchmark를 실행하고 생성 결과를 커밋한 뒤 make benchmark-check를 실행한다. |
| T2.67 | 통합과 기록 갱신 후 최종 hosted 실행이 여전히 필요하다. | 최종 main revision의 hosted 검사가 통과해야 한다. |

### Prepared kit patch set

격리한 kit branch `fix/release-bootstrap-K614-1`은 관측한 실패를 위해 준비한 수정만 담는다.

- K614-1: 소비자 release 명령보다 먼저 형제 kit을 준비하고 빌드한다. 소유 workflow 테스트 아홉 개가 통과한다.
- K614-1-1: 동적으로 로드하는 tokenizer를 포함하여 arginfo 생성에 설정된 PHP CLI extension을 유지한다. 재현 테스트는 수정 전에 실패하고 수정 후 통과한다.
- K614-1-2: 오프라인 gate 전에 설치 단계에서 공용 Rust checker crate를 다운로드한다. Setup 순서 재현 테스트는 수정 전에 실패하고 수정 후 통과한다.

Patch set의 TypeScript 컴파일과 문서 검사가 통과한다. 이는 로컬 준비 결과이며 kit main에 수정이 들어갔거나 원격 aggregate가 통과했음을 뜻하지 않는다. 다른 활성 kit workspace와 미커밋 변경은 보존한다.

### Steps before publication

1. 진행 중인 kit 작업이 준비되면 kit 항목 세 개를 통합한다. Canonical gates 및 release workflow를 반영한다. 의존성 pin은 provider tag가 존재한 뒤에만 바꾼다.
2. 패키지 manifest와 consumer manifest 및 lock은 요청한 버전으로 유지한다. Clean committed tree에서 preview archive를 빌드하고 manifest와 파일 목록을 확인한다. 게시 workflow는 tag에서 최종 asset을 다시 빌드한다.
3. T2.48은 명시한 부하 조건에서 유효한 clean 측정으로만 완료한다. 검사를 맞추기 위해 timing data나 source state를 편집하지 않는다.
4. 최종 revision의 성공한 hosted 증거를 얻고 그 증거로 T2.80-1과 T2.67을 완료한다. Tag 생성과 게시는 그 뒤 단계이며 로컬 준비의 증거가 아니다.
