<!-- doc-id: development -->
<!-- source-sha256: c80db7d77115570ef9b37f03420458934d1f6d8f110d03a0b7e433080ab6cc85 -->
# 개발 절차

[English](AGENTS.md)

<a id="workflow"></a>
## 필수 작업 절차

수정 전에 [문서 관리](docs/documentation-plan.ko.md), 관련 [명세](docs/spec/json-contract.ko.md), [기능 상태](docs/features.ko.md)를 읽습니다. 동작을 변경하기 전에 명세를 갱신합니다. 완료하지 않은 작업은 기능 기록에 표시합니다.

올바른 코드와 사실에 맞는 이력을 유지합니다. 실제 원인을 직접 설명합니다. 코드 변경에 관련 문서, 기능 상태, 변경 기록을 포함합니다. 개인 선호, 대화 맥락, 인증 정보, 백업 위치는 Git 외부에서 관리합니다.

관측된 결함은 추적되는 RED 테스트로 재현합니다. 아직 관측되지 않았지만 발생 가능한 결함은 그 문제를 드러낼 입력과 요구 결과를 가진 결정적인 RED 사례를 먼저 작성합니다. 구현 전에 의도한 실패를 확인하고 원인을 고친 뒤 같은 사례와 관련 패키지 사용 테스트를 GREEN으로 검증합니다. 사례가 문제를 드러내지 못하면 기준을 낮추지 말고 조사합니다.

영어가 정본입니다. 같은 정보로 한국어 문서를 함께 갱신합니다. 번역 전체를 비교한 후에만 `source-sha256`을 갱신합니다. 문서, 주석, 커밋 메시지, 번역에는 주체와 동작을 명시한 직접적인 기술 표현을 사용합니다.

메시지 전송, 산출물 게시, 접근 제어 변경, 이력 재작성 권한을 임의로 해석하지 않습니다. 해당 작업에 이미 제공된 권한을 따릅니다.

기본적으로 `main`에서 작업합니다. 에이전트가 작업하거나 상황상 브랜치나 워크트리가 필요하면 브랜치는 `{type}/{shortname}-{체크리스트 ID}`, 워크트리는 `{프로젝트}-{shortname}-{체크리스트 ID}`로 만들고, `main`에 합친 즉시 둘 다 제거합니다. 브랜치를 `main`에 통합한 뒤 커밋이나 동등한 변경이 반영됐고 워크트리가 깨끗한지 확인합니다. 삭제할 워크트리에만 있는 `.gitignore` 제외 파일 중 계속 필요한 파일은 먼저 다른 곳에 보존합니다. 그런 다음 워크트리와 로컬 브랜치를 제거합니다. 미통합 작업이나 진행 중인 작업은 보존합니다.

`main`에 통합할 수 없는 테스트 전용 브랜치의 의미 있는 커밋은 관련 기능을 커밋하기 전에 체리픽하고, 나머지 테스트 전용 변경은 폐기한 뒤 워크트리와 브랜치를 제거합니다. 제거할 수 없다면 먼저 소유 체크리스트에 번호가 붙은 하위 항목을 추가하고 원인과 정확한 제거 조건을 기록합니다.

<a id="feature-state"></a>
## 기능 상태

[기능 상태](docs/features.ko.md)는 이 저장소의 tracker입니다. `scripts/full_run.py`는 각 기능 행의 구현 칸을 읽습니다. 상태는 그 칸에만 둡니다. 기능 표의 절은 표만 담고, `scripts/docs_check.py`는 `docs/features.md`와 그 번역의 다른 곳에 code span이나 표 칸으로 적힌 상태와 그 절의 다른 줄에서 file, 줄, 열을 적으며 실패합니다. tracker를 읽는 모든 도구(`scripts/docs_check.py`, `scripts/full_run.py`, `scripts/push_gate.py`)는 하나의 parser로 행을 읽고, 기능 표가 없는 tracker, 기능 행이 없는 표, ID가 기능 ID `F-...`가 아닌 행을 거부하므로, 행을 내지 않는 tracker는 어떤 검사도 통과하지 못합니다. 이 절이 상태를 정의합니다.

`implemented`는 해당 동작이 구현됐다는 뜻입니다. `partial`은 구현이 진행 중인 기능을 표시합니다. 이것이 이 저장소의 활성 작업이며, `partial`인 행이 있는 동안 `make check`는 실행을 거부합니다. `planned`는 구현을 시작하지 않은 기능을 표시합니다. `shared-suite`는 공통 JSON 테스트, `package-tests`는 구현 자체의 테스트, `docs-tests`는 문서 검사기 테스트, `benchmark`는 저장소 벤치마크 프로토콜과 커밋된 결과를 뜻합니다. 각 상태는 자신을 뒷받침하는 기록을 가리킵니다. 공통 스위트와 검사기 테스트는 [검증 기록](docs/verification.json)을, 벤치마크는 [벤치마크 결과](benchmarks/results.json)를 가리킵니다. 검증 기록에는 실제 버전, 사례 수, 실행 시각, 소스 해시가 있습니다. 벤치마크 결과는 깨끗한 체크아웃에서 workload가 선언한 프로토콜과 입력으로 측정했을 때에만 근거가 됩니다. `source-only`는 확인된 배포 방식이며 레지스트리 게시는 검증되지 않았습니다. 게시 확인 결과는 [distribution.json](docs/distribution.json)에서 별도로 관리합니다.

<a id="verification"></a>
## 필수 검사

각 구현 패키지는 자체 소스와 문서 목록을 관리합니다. 명령은 저장소 루트에서 실행합니다.

변경을 진행하는 동안에는 그 변경을 소유한 테스트만 실행합니다. RED 사례와 같은 사례의 GREEN, 변경한 구현의 검사, 변경한 스크립트를 다루는 검증기 unit test입니다. 수정할 때마다 더 넓은 검사를 다시 실행하지 않습니다.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/test.py --unit test_docs_check.DocumentationChecks.test_missing_anchor_fails
git diff --check
~~~

`scripts/verify.py --only`는 선택한 구현을 빌드하고 그 구현의 케이스·심볼 목록, 선언된 패키지 테스트, 공통 사례를 실행하며 기록을 쓰지 않습니다. `scripts/test.py --unit`은 지정한 검증기 unit test를 실행하며 기록을 쓰지 않습니다. test가 없는 module처럼 test를 하나도 고르지 않는 이름은 어떤 test도 실행하기 전에 `selected 0 tests`와 그 이름을 출력하며 실패합니다.

`make check`는 활성 항목이 모두 끝난 뒤 한 번 실행하고 단계별 경과 시간을 보고합니다. 추가 사례를 포함하면 그 실행은 다음과 같습니다.

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make check`는 검증보다 먼저 guard `scripts/full_run.py`를 시작합니다. 이 저장소의 활성 작업은 [기능 상태](docs/features.ko.md)에서 구현 상태가 `partial`인 기능 행입니다. guard는 판단을 이유와 함께 출력하고, 그런 행이 있으면 각 ID를 기능과 함께 나열하며 거부하고, `make hooks-check`가 보고하듯 pre-push hook이 설치되지 않았으면 거부하고, 추적 파일의 변경이 커밋되지 않았거나 `.gitignore`가 무시하지 않는 파일이 추적되지 않으면 각각을 밝히며 거부합니다. 전체 실행은 커밋된 tree를 검증하고, build는 추적되지 않은 파일도 읽기 때문입니다. 검증 마지막의 문서 검사가 `docs/pie-verification.json`에 적용하는 검사를 그 기록이 통과하지 못하면 거부합니다. 오래된 PIE 기록 때문에 tree의 전체 실행을 소모하지 않기 위해서입니다. `var/full-run.json`이 현재 tree(`git rev-parse HEAD^{tree}`)의 전체 실행을 기록하고 있으면 그 실행을 commit, 시작 시각, 결과와 함께 밝히며 거부하고, `incomplete` record의 process가 아직 실행 중이면 거부합니다. 검증 명령을 시간 제한 없이 끝까지 실행하고 그 앞뒤에 record를 쓰므로, 멈춘 실행은 `incomplete`로 기록되어 남습니다. `make rerun-failed`는 현재 tree의 전체 실행이 실패했거나 끝나지 않았을 때만 검증을 다시 실행하고, 그 밖에는 거부됩니다. 검증은 target 하나이므로 전체가 다시 실행됩니다. `var/`는 Git이 무시하므로 checkout과 worktree마다 자기 record를 가집니다. CI는 `.github/workflows/push-gate.yml`의 job `push-gate`만 실행하며, 이 job은 검증을 실행하지 않습니다. 새 checkout에는 record가 없으므로, 그곳에서 `make check`는 `partial` 기능이 없고 tree가 깨끗하면 실행됩니다.

push는 `partial` 기능이 없을 때만 합니다. pre-push hook `.githooks/pre-push`는 `scripts/push_gate.py hook`을 실행합니다. 이 명령은 push되는 commit이나 working tree의 `docs/features.md`에 `partial` 행이 있으면 각 ref, commit, ID, 기능을 밝히며 push를 거부하고, 그 file을 읽을 수 없으면 거부합니다. 모든 `make` 실행은 Makefile을 읽을 때 `core.hooksPath`를 `.githooks`로 설정합니다. `make hooks`는 이를 설정하고 검사하며, `make hooks-check`는 `core.hooksPath`가 `.githooks`가 아니거나 hook이 실행 가능하지 않으면 실패합니다. hook이 없는 checkout에서 한 push는 hook을 실행하지 않으므로, `.github/workflows/push-gate.yml`의 job `push-gate`가 모든 branch에 push된 commit과 모든 pull request의 head commit에 `scripts/push_gate.py commit`을 실행합니다. 이 job은 기능이 `partial`이면 실패하고, `.githooks/pre-push`가 mode 100755로 추적되지 않으면 실패합니다. 이 job은 local checkout의 설정을 검사할 수 없습니다.

문서만 검토할 때는 `make docs-check`를 실행합니다. 이 검사는 검증 기록을 소스와 비교하지 않습니다. PIE 기록과 통합 기록은 기록 자신을 뺀 모든 추적 파일을 해시하고, 어떤 기록, 문서 검사, 공통 사례도 추적되지 않은 파일을 읽지 않으므로, 어떤 변경이든 커밋되면 기존 PIE 기록은 오래된 기록이 됩니다. 그때 전체 실행은 다음 순서를 따릅니다. 해당 추가 사례와 함께 `make pie-check PIE=/path/to/pie.phar`를 한 번 실행하고, `docs/pie-verification.json`만 커밋하고, `make check`를 한 번 실행하고, 그것이 쓴 `docs/verification.json`만 커밋합니다. guard는 PIE 기록이 오래됐거나 커밋되지 않았으면 `make check`를 거부하고 이 절차를 알려 줍니다. 검사를 통과시키기 위해 검증 결과나 소스 해시를 직접 수정하지 않습니다.

[구현 등록 정보](implementations.json)는 패키지 경로·빌드·어댑터·패키지 테스트·런타임 명령을 정의합니다. `make check`는 선언된 패키지 테스트 명령을 모두 실행합니다. 공통 사례는 JSON 계약만 검사하므로 한 패키지에만 있는 API에는 닿지 않으며, 그런 API는 해당 패키지의 테스트가 필요합니다. [package-tests.json](package-tests.json)은 모든 구현이 실행하는 케이스, 사유를 적은 면제, 패키지 고유 케이스, 그리고 공개 심볼마다 그것을 검증하는 케이스를 정의합니다. `make check`는 이 표준과 각 패키지가 보고한 케이스·심볼을 대조해 누락된 케이스, 선언되지 않은 케이스, 검증되지 않는 심볼, 더 이상 내보내지 않는 심볼 선언이 있으면 실패합니다. 공통 JSON 비교 알고리즘을 변경하지 않고 해당 등록 정보와 패키지 디렉터리로 새 언어를 추가합니다. 계약 변경은 같은 저장소 리비전에서 검증기와 관련 패키지를 갱신합니다. [저장소 계약](docs/spec/repositories.ko.md)을 참조합니다.

모든 언어 어댑터는 [official.json](examples/official.json)과 [scripts/verify.py](scripts/verify.py)를 사용합니다. 공통 사례는 해당 파일이나 `fixtures/`에 추가합니다. 언어별로 다른 예제나 기대 결과를 만들지 않습니다.

Rust 코드를 변경하면 `rust/`에서 `cargo clippy --all-targets -- -D warnings`를 실행합니다. Go 코드를 변경하면 `go/`에서 `go vet ./...`를 실행합니다. 네이티브 코드를 변경하면 PHP 확장을 다시 빌드합니다. 이전 바이너리나 이전 결과를 변경된 코드의 검증 근거로 사용하지 않습니다.

<a id="completion"></a>
## 완료

코드와 테스트를 읽고 문서의 정확성을 확인합니다. 자동 링크, 개정본, 상태 검사는 문장 내용의 정확성을 증명하지 않습니다. 테스트와 실제 게시를 별도로 확인하고 관측한 근거로만 [배포 상태](docs/operations/distribution.ko.md)를 갱신합니다.

Git 메시지는 사실대로 간단하게 작성합니다. 관련 없는 변경은 가능하면 분리합니다.
