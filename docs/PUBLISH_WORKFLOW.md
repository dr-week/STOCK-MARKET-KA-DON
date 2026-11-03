# Publishing workflow

This repository includes a Windows PowerShell helper for previewing, committing, and pushing selected changes. It is designed to keep the routine to one command while allowing each run to change scope, destination, and commit behavior.

## Quick use

From the repository root:

```powershell
  pnpm repo:publish -- -Help
  pnpm repo:publish                              # preview eligible changes
  pnpm repo:docs                                 # preview documentation changes
  pnpm repo:backend -- -ChangeSet Changed
  pnpm repo:publish -- -Preset desktop -Action Push -Message "feat: update desktop app"
pnpm repo:publish -- -Preset docs -Action Push -Message "docs: publish guide updates"
```

The default action is `Preview`. After checking its selected-file list, use `-Action Commit` for a local commit or `-Action Push` to commit and push. A commit message is required for either write action. The default change set is `Changed` (tracked modifications/deletions plus new files); `All` scans every tracked file plus new files.

## Common combinations

| Goal | Command |
| --- | --- |
| Preview all changed safe files | `pnpm repo:publish` |
| Preview only docs | `pnpm repo:docs` |
| Preview tracked changes | `pnpm repo:publish -- -ChangeSet Tracked` |
| Preview new files | `pnpm repo:publish -- -ChangeSet Untracked` |
| Scan every tracked file | `pnpm repo:publish -- -ChangeSet All` |
| Commit selected docs locally | `pnpm repo:publish -- -Preset docs -Action Commit -Message "docs: refresh guides"` |
| Push backend changes to another branch | `pnpm repo:publish -- -Preset backend -Action Push -Branch feature/backend-docs -Message "docs: update backend guide"` |
| Add an extra exclusion | `pnpm repo:publish -- -Exclude docs/drafts,desktop/tauri/target` |
| Use another Git remote | `pnpm repo:publish -- -Action Push -Remote upstream -Branch main -Message "docs: sync guide"` |

Use `-Include` to override a preset's include paths for a single run. `-Exclude` filters paths after selection. Both accept comma or semicolon separated repo-relative paths and directory prefixes.

## Script modules

- `scripts/publish.ps1` parses options, chooses configuration and preset precedence, prints the preview, and coordinates the workflow.
- `scripts/publish/modules/Configuration.ps1` loads JSON config and resolves named presets.
- `scripts/publish/modules/Paths.ps1` normalizes filters and enforces the root allowlist and blocked path rules.
- `scripts/publish/modules/Git.ps1` contains shared Git command and repository-root helpers.
- `scripts/publish.config.example.json` defines the tracked default scopes. The ignored `scripts/publish.config.json` can customize them locally.

Use the flags for one-run adjustments. Edit the JSON template/local config for repeatable defaults; edit a module only when changing that module's responsibility.

## Local configuration

Copy the template and edit it locally:

```powershell
Copy-Item scripts/publish.config.example.json scripts/publish.config.json
```

The local config file is ignored by Git. It can set `remote`, `branch`, `changeSet`, default `include` and `exclude` paths, `allowedRoots`, and named `presets`. A preset can define its own `include`, `exclude`, and `changeSet`. The command-line paths take precedence over preset paths; explicit command-line values take precedence over config defaults.

Example preset:

```json
"presets": {
  "docs": { "include": ["README.md", "docs"] },
  "launcher": { "include": ["desktop/tauri", "README.md"] }
}
```

Message, branch, and remote defaults can also be set with `SMKD_PUBLISH_MESSAGE`, `SMKD_PUBLISH_BRANCH`, and `SMKD_PUBLISH_REMOTE`.

## Safety and behavior

- Databases, SQLite sidecars, logs, credentials, keys, generated build folders, and the `fast-framework` submodule are always blocked.
- The safe root allowlist is configurable, but the blocked-path rules remain active even if a path is included by a preset.
- The helper refuses pre-staged changes to avoid accidentally mixing a staged snapshot with newer working-copy contents.
- Real commits are assembled in a temporary Git worktree. The current checkout and index are left alone.
- `Preview` does not commit or push. `Commit` creates a commit in an isolated worktree and saves a durable reference under `refs/codex/publish/<commit>`; it does not move the active local branch. `Push` publishes the commit to the selected remote/branch.
- Git hooks run by default. `-NoVerify` is available only as an explicit override.
- `fast-framework` is a separate submodule and must be published from its own checkout.

## Troubleshooting

- **Unknown preset:** inspect `presets` in `scripts/publish.config.json` or run `pnpm repo:publish -- -Help`.
- **No eligible changes:** check the preview selection, selected paths, safe-root allowlist, and mandatory exclusions.
- **Pre-staged changes:** review them, then unstage or commit them separately before retrying.
- **Push rejected:** verify remote permissions and whether the destination branch advanced; rerun preview after syncing the branch.
- **No pnpm installed:** invoke the script directly: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/publish.ps1 -Action Preview`.
