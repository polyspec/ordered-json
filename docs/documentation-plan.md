<!-- doc-id: documentation-plan -->
# Documentation management

[한국어](documentation-plan.ko.md)

This document defines the repository's documentation structure and update procedure. It is an active procedure. Implementation state is maintained in [features](features.md).

<a id="ownership"></a>
## Canonical documents

Each topic has one English canonical document and one `.ko.md` translation. The [manifest](documentation-manifest.json) registers every common Markdown document and its topic. Each implementation package registers its own documents. The common checker checks both levels. Other documents link to the canonical topic instead of repeating its rules.

| Location | Content |
| --- | --- |
| `README.md` | Project overview, minimum start procedure, document links |
| `docs/spec/` | Approved behavior, structures, API contracts, acceptance criteria |
| `docs/features.md` | Implementation, verification evidence, distribution status |
| `docs/operations/` | Current installation, execution, verification, publication procedures |
| `CHANGELOG.md` | Actual changes, reasons, verification |
| `docs/plans/` | Proposals pending approval |
| `AGENTS.md` | Development procedure and required checks |
| Outside Git | Personal preferences, conversation context, local authentication and backup details |

Specifications describe contracts. Feature records describe implemented behavior. Distribution records describe observed publication. These states are independent.

<a id="updates"></a>
## Update procedure

1. Read the applicable specification before changing code.
2. If the direction changes, update the specification first and mark unfinished implementation explicitly.
3. Include behavior changes, affected documentation, feature state, and changelog entries in the same change.
4. Update English and Korean together. Compare their information, commands, links, and status values.
5. Run the applicable checks against the changed files. Do not use results for different source files as current evidence.
6. Record publication only after checking the remote source, release, or package result.
7. Update relevant private memory outside Git.

After a proposal is approved, update the specification and remove the proposal document. Correct existing rules when they conflict with the approved contract or observed behavior.

<a id="checks"></a>
## Documentation checks

`make docs-check` checks registered document pairs, local link targets and anchors, matching section identifiers and executable code blocks, Korean translation revision hashes, required feature fields, evidence references, and current verification source hashes. It also rejects local home-directory paths in public documents and reports.

The Korean file's `source-sha256` comment records the English revision reviewed for that translation. Update it only after reviewing the translation. Matching hashes do not prove translation accuracy. The checker does not verify external website availability or prose meaning; those require review against code and test results.

`make check` runs the verifier and documentation checker tests, every registered JSON implementation, and `make docs-check`. [PIE verification](operations/validation.md#pie) records a separate build and shared case result. Hosted CI is not configured. Developers must run the required commands before committing.

<a id="records"></a>
## Technical records

Documents describe current behavior. Changelogs describe actual changes and verification. Commit messages and code comments identify the subject, operation, object, and result directly. State a necessary cause in one sentence. Use the same information in English and Korean. Do not include figurative language, personification, conversation history, or personal judgments.

Preserve correct code. Decide whether to revert from correctness and harmful effects, not merely from a difference in intent. Record the actual reason for a change. Separate unrelated changes into separate commits when possible.

External project comparisons belong only in an explicitly requested comparison report. Dependencies, executable verification inputs, and normative format requirements can be identified where required to reproduce or understand current behavior.
