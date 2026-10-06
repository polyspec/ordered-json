<!-- doc-id: validation -->
<!-- source-sha256: f08bebfc51971ccc43fa9a72282de8141ffd252f31965be0e424eade7a43ed71 -->
# 검증

[English](validation.md)

<a id="repository-check"></a>
## 통합 검사

개발 중에는 unit test만 실행합니다(`python3 scripts/test.py --unit`). 통합 검사, PIE 산출물 검사, owner 검사는 [hosted CI](#ci)가 push마다 실행하는 end-to-end 검사입니다. 어떤 규칙도 commit이나 push 전에 로컬 실행을 요구하지 않으며, pre-push hook은 tracker와 체크리스트만 읽습니다. 그래도 로컬에서 통합 검사를 실행하려면 [필수 도구](installation.ko.md#requirements)를 설치하고 저장소 루트에서 실행합니다.

~~~sh
make tools
make check
~~~

검증기와 문서 검사기 테스트를 실행하고, 선택한 패키지를 빌드하고, 등록된 모든 구현에 공통 JSON 사례를 적용하고, 통합 기록 `var/records/verification.json`을 생성한 뒤 체크아웃의 [기록](#records)과 함께 공통·패키지 문서를 검사합니다. 통합 기록에는 추적된 모든 파일의 소스 해시가 포함됩니다.

각 빌드 단계는 시작 줄, 도착하는 대로의 출력, 종료 상태와 경과 시간을 출력합니다. 빌드 단계와 PIE 명령에는 시간 한도가 없으며, 종료 상태와 출력이 결과를 결정합니다. 패키지 테스트는 케이스가 끝날 때마다 그 케이스와 경과 시간을 출력합니다. 케이스마다 직전 결과 이후 60 s가 주어지며, 이를 넘기면 검증기가 테스트 process group을 종료하고 실행 중이던 케이스 이름과 함께 실패합니다. 각 어댑터는 공통 사례를 한 번에 하나씩 받고, 검증기는 사례와 그 응답의 경과 시간을 출력합니다. 응답마다 60 s가 주어지며, 이를 넘긴 어댑터는 종료되고 해당 사례 이름이 보고됩니다. 실행 전체에는 한도를 두지 않습니다. 빌드 단계, 패키지 테스트 명령, 어댑터가 끝나면 검증기는 그 process group을 종료하므로, 그것이 background에서 시작한 process는 그보다 오래 남거나 그 출력을 열어 두지 않습니다. 실패는 실행도 다른 언어도 끝내지 않습니다. 단위 테스트, 각 언어의 빌드, 케이스와 symbol listing, 패키지 테스트, 모든 어댑터의 모든 공통 사례는 끝까지 실행되고, 실패한 빌드는 자기 언어의 이후 단계만 건너뛰며, 실행은 그 뒤 모든 실패를 나열하고 기록을 쓰지 않은 채 status 1로 끝납니다.

<a id="records"></a>
## 기록

commit의 근거는 그것을 검증하는 실행입니다. `make pie-check`는 PIE 기록 `var/records/pie-verification.json`을, `make check`는 통합 기록 `var/records/verification.json`을 씁니다. Git은 `var/`를 무시하므로 어떤 기록도 커밋하지 않습니다. 기록은 `benchmarks/results.json`을 뺀 모든 추적 파일을 해시하므로, 커밋된 기록은 다음 commit에서 오래된 기록이 되고 변경마다 로컬 기계에서 전체 실행을 강요합니다. `--records`가 있으면 `make check` 마지막의 문서 검사는 같은 체크아웃의 통합 기록과, 있으면 PIE 기록을 현재 소스와 대조하므로, 두 기록을 모두 쓰는 실행은 두 기록을 모두 검사합니다.

통합 기록에는 소스 해시, 패키지 파일 기록, 실제 런타임 버전, 실행 중인 Python patch release, 사례 수, 결과, 검사기 테스트 수, 빌드 경고, 추가 입력 개정본이 포함됩니다. PHP 버전과 확장 버전은 별도 필드입니다. 입력이 변경되면 현재 검증 근거로 유효하지 않습니다. 실행 중 변경과 불완전한 구현 결과는 거부합니다. 이 기록은 게시 근거가 아닙니다. 모든 기록과 보고서(`var/records/verification.json`, `var/records/pie-verification.json`, `benchmarks/results.json`, 실패한 benchmark의 검토용 사본, `docs/reports/ojson-comparison.json`)는 Git이 무시하고 어떤 manifest도 읽지 않는 `var/`의 파일에 끝까지 쓴 뒤 그 경로 위로 이름을 바꾸므로, 읽는 쪽은 이전 파일이나 새 파일을 보며 파일의 일부를 보지 않습니다.

<a id="supplementary"></a>
## 추가 입력

~~~sh
make tools
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make tools`는 [외부 입력](../../external-inputs.json)이 고정한 nst/JSONTestSuite 개정본을 `.cache/JSONTestSuite`로 가져오고, 개정본, 사례 수, 입력 해시가 고정값과 다른 체크아웃은 각 필드의 기대값과 실제값을 밝히며 거부합니다.

추가 입력 사용 여부를 기록합니다. `i_` 사례에는 공통 UTF-8·깊이 정책을 적용합니다. 공식 입력과 기대값은 저장소 루트에만 있으며 어댑터에 독립 기대값을 추가하지 않습니다.

[외부 입력](../../external-inputs.json)이 그 개정본과 사례 해시를 고정하며, 다른 체크아웃으로 측정한 기록은 문서 검사를 통과하지 못합니다. `make check`와 `make pie-check`는 어떤 작업보다 먼저 추가 사례를 그 고정값과 비교하고, `make pie-check`는 PHAR의 해시도 PIE 고정값과 비교합니다. 다른 필드마다 빌드를 시작하기 전에 기대값과 실제값을 밝히며 명령이 실패합니다.

<a id="individual"></a>
## 개별 구현

공통 체크아웃에서 선택한 검사는 정의된 어댑터를 빌드하고 실행합니다. 통합 기록은 갱신하지 않습니다.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/verify.py --only rust
python3 scripts/verify.py --only go
python3 scripts/verify.py --only php --only php-extension
~~~

독립 체크아웃은 다음과 같이 검사합니다.

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
make check
~~~

각 패키지는 독립 빌드 대상으로 유지하지만 공유 검사 명령은 루트 registry와 검증기가 정의합니다. 네이티브 확장은 `php-extension/`에서 Git이 추적하는 소스 파일을 실행의 임시 디렉터리에 복사해 빌드하며 같은 체크아웃의 형제 PHP 패키지와 함께 검사합니다. 각 실행은 실행 디렉터리를 출력하고 끝날 때 제거하므로, 한 체크아웃의 실행들은 빌드 출력을 공유하지 않습니다. 실행의 모든 cargo 명령과 benchmark의 `cargo run`은 `CARGO_TARGET_DIR`를 그 실행 안의 디렉터리로 설정하므로, 환경이 지정하거나 다른 체크아웃이 채운 target 디렉터리가 Rust probe, package test, benchmark binary를 제공하지 않습니다.

추가 입력은 `make check JSON_TEST_SUITE=/path/to/JSONTestSuite`로 검사합니다.

<a id="pie"></a>
## PIE 산출물 검사

`make tools`는 [외부 입력](../../external-inputs.json)이 고정한 PIE 릴리스를 [공식 릴리스](https://github.com/php/pie/releases)에서 `make pie-check`의 기본 `PIE`인 `.cache/pie/pie.phar`로 내려받고, SHA-256이 고정값과 다른 파일은 두 해시를 밝히며 거부합니다. 출처는 `gh attestation verify --owner php .cache/pie/pie.phar`로 확인할 수 있습니다. 공통 루트에서 실행합니다.

~~~sh
make pie-check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

[PIE 검사기](../../scripts/check_pie.py)는 확장의 추적 소스 파일을 임시 실행 디렉터리에 복사하고, 그 디렉터리에 PIE 설정을 격리하고, 복사본을 경로 저장소로 등록하고, 패키지 인식을 확인하고, PIE로 빌드합니다. 같은 공통 어댑터와 기대값으로 해당 산출물을 직접 검사합니다. 중간에 일반 네이티브 빌드를 실행하지 않습니다.

PIE 기록 `var/records/pie-verification.json`은 PIE 버전과 PHAR 해시, 실행 디렉터리 기준의 선언된 산출물 경로, 명령, 소스 해시, PHP·확장 버전, 사례 결과를 기록합니다. PHAR 해시와 추가 입력 개정본은 고정값과 일치해야 합니다. 빌드된 모듈은 경로로만 명시합니다. 링크 시점에 새 식별자와 서명이 들어가므로 그 해시는 한 번의 실행만 가리키며, 검사기는 해시를 담은 기록을 거부합니다. 빌드 오류, 빌드 도구 누락, 어댑터 경고, 검사 중 변경은 검증 실패로 처리합니다. 컴파일 경고는 기록에 유지합니다. 이 검사는 모듈을 설치하거나 패키지를 게시하지 않습니다. 기록은 `benchmarks/results.json`을 뺀 모든 추적 파일을 해시하며, 같은 체크아웃에서 `make pie-check` 뒤에 실행하는 `make check`의 문서 검사는 PIE 기록이 현재 소스와 맞지 않으면 거부합니다.

<a id="ci"></a>
## Hosted CI

`.github/workflows/ci.yml`은 모든 pull request와 [merge queue](#publish)의 모든 merge group에서 전체 suite를 실행합니다. 하나의 matrix에 두 job이 있고 `fail-fast: false`이므로 한 job이 다른 job을 취소하지 않습니다.

~~~sh
make tools
make ci CI_JOB=suite JSON_TEST_SUITE=.cache/JSONTestSuite
make ci CI_JOB=docs
make ci-summary CI_JOB=suite
~~~

job `suite`는 고정 파일에서 Python, Node.js, Go, PHP를 설치하고, 내려받는 유일한 단계인 `make tools`를 실행한 뒤 target `hooks`, `pie-check`, `check`를 실행합니다. `make pie-check`는 PIE 기록을, `make check`는 통합 기록을 쓰고 그 문서 검사가 두 기록을 검사합니다. job `docs`는 Python만 설치하고 `docs-check`와 `owner-validate`를 실행합니다. 모든 step은 make target을 실행하고 실패한 step 뒤에도 실행됩니다(`if: !cancelled()`). `make ci`(`scripts/ci_run.py`)는 job의 모든 target을 끝까지 실행하고, 출력을 도착하는 대로 출력하며 `var/ci/<job>/logs/<target>.log`에 쓰고, 각 target의 상태, 종료 상태, 시간을 `var/ci/<job>/summary.json`에 기록합니다. `make ci-summary`는 각 target과 그 상태와 시간, 실패한 target마다 첫 실패 줄을 담은 `var/ci/<job>/summary.md`를 쓰고, `var/records`의 기록을 `var/ci/<job>/records`로 복사하고, 요약을 GitHub의 job summary에 덧붙이며 실패하지 않습니다. step `report`는 실패 뒤에도 `var/ci/<job>/`를 artifact `ci-<job>-<run id>-<attempt>`로 upload합니다. 어떤 step에도 시간 한도가 없습니다. `actions/python-versions`가 `ubuntu-26.04`용 Python 3.9를 build하지 않으므로 job은 push gate처럼 `ubuntu-24.04`에서 실행하며, 기록은 실행한 Python과 PHP의 patch release를 적습니다.

<a id="publish"></a>
## main 공개

모든 변경은 pull request와 merge queue를 거쳐 `main`에 들어갑니다. 이 저장소의 어떤 명령도 `main`을 push하지 않습니다. branch는 GitHub의 표준 명령이나 GitHub UI로 공개합니다.

~~~sh
git push origin HEAD:refs/heads/<branch>
gh pr create --base main --head <branch> --fill
gh pr merge <branch> --auto --rebase
~~~

`.github/ruleset.json`의 GitHub ruleset `main`은 enforcement `active`로 `refs/heads/main`에 적용되고 bypass actor가 없으므로 관리자에게도 적용됩니다. 규칙은 다음과 같습니다.

- `pull_request`: 변경은 pull request로 들어옵니다. 승인은 필요 없고 모든 merge method를 허용합니다. merge queue는 자체 method로 merge하고 `gh pr merge --auto`는 자기가 고른 method로 auto-merge를 요청하므로, `rebase`만 허용하는 규칙은 pull request를 queue 밖에 둡니다.
- `merge_queue`: merge queue는 method `REBASE`로 merge하므로 pull request의 각 commit이 `main`에 각각의 commit으로 들어갑니다. grouping strategy는 `ALLGREEN`이고, 한 번에 최대 5개 항목을 build하고 merge하며, 항목을 더 기다리지 않습니다. `check_response_timeout_minutes`는 GitHub의 최대값인 360이므로 긴 suite가 이것으로 끊기지 않습니다.
- `required_linear_history`, `non_fast_forward`, `deletion`: `main`에 merge commit, force-push, 삭제가 없습니다.
- `required_status_checks`: GitHub Actions app(integration 15368)의 check `push-gate`, `suite`, `docs`입니다. 각각 `make push-gate`와 `make docs-check`를 실행하는 `.github/workflows/push-gate.yml`의 job, 전체 suite를 실행하는 `.github/workflows/ci.yml`의 job입니다.

직접 `git push origin <commit>:main`은 `GH013: Repository rule violations found`로 거부됩니다. `gh pr merge --auto`는 pull request의 필수 check가 pull request에서 통과하면 그 pull request를 merge queue에 넣습니다. queue는 그것을 `main` 위에 rebase해 branch `gh-readonly-queue/main/pr-<number>-<sha>`에 merge group을 만들고, 두 workflow가 그 commit에서 실행되며(`merge_group`), check가 통과하면 queue가 `main`을 정확히 그 commit으로 옮깁니다. check가 실패하면 pull request는 queue에서 빠지고 `main`은 움직이지 않습니다. merge group의 `ci.yml` 실행은 취소되지 않습니다. group마다 ref가 따로 있고, `cancel-in-progress`는 pull request에만 적용됩니다. merge된 pull request의 branch는 삭제됩니다(`delete_branch_on_merge`). rebase는 merge된 commit에 새 hash를 주므로, `git pull --rebase`가 queue가 merge한 local commit을 버립니다.

`make github-ruleset`은 선언의 저장소 설정(`allow_rebase_merge`, `allow_auto_merge`, `delete_branch_on_merge`)을 바꾸고 선언된 이름의 ruleset을 만들거나 갱신하되 다른 곳만 바꾸며, 다시 비교합니다. `make github-ruleset-check`는 아무것도 바꾸지 않으며, 설정이 다르거나 live ruleset이 없거나 선언과 다르면 field마다 live 값과 선언 값을 밝히며 실패합니다. 둘 다 저장소 administration 권한이 있는 인증된 `gh`가 필요합니다. `scripts/tests/test_github_ruleset.py`는 가짜 `gh`로 script를 실행합니다.

<a id="documentation-checks"></a>
## 문서 검사

~~~sh
make docs-check
~~~

[검사기](../../scripts/docs_check.py)는 각 문서 목록, 링크, 번역 쌍과 개정 해시, 절과 코드 블록 일치, 기능 상태를 검사합니다. `make check`가 통합 기록을 쓴 뒤 붙이는 `--records`가 있으면 체크아웃의 [기록](#records)이 현재 소스와 일치하는지도 검사합니다. `make docs-check`는 그 비교를 생략합니다. 공통 목록에는 공통 문서만 등록합니다. 각 패키지 디렉터리는 자체 목록으로 검사합니다.

한국어 `source-sha256`을 갱신하기 전에 코드·테스트와 영어·한국어 내용을 비교합니다. 해시 일치는 번역 정확성을 증명하지 않습니다. 외부 링크는 문법만 검사하며 접속하지 않습니다. [hosted CI](#ci)가 모든 pull request와 모든 merge group에서 이 검사들을 실행합니다.

<a id="limits"></a>
## 한계

사례 모음은 파서 허용 여부와 [인수 계약](../spec/json-contract.ko.md#acceptance)을 검사합니다. 모든 API 인수, 기본값이 아닌 모든 깊이 설정, 선언된 모든 최소 런타임, 모든 플랫폼, 모든 호스트 인코더 연동을 검증하지는 않습니다. Windows와 ZTS 네이티브 빌드는 검증되지 않았습니다.

실패한 검사와 컴파일 경고를 직접 보고합니다. 입력이 변경되면 이전 결과를 사용하지 않습니다. JSON 기록 생성 후 문서 검사가 실패할 수 있으므로 완료 전에 전체 검사가 성공해야 합니다.
