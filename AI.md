# Opero AI Working Rules

This is the single source of truth for app-specific AI-tool rules in this repository.

Bench-wide operational rules still come from
`../../AGENTS.md`.

## Rule Precedence

- Follow the user-level `AGENTS.md`, when present, for shared defaults and routing.
- Follow `../../AGENTS.md` for bench-wide
  operational rules.
- This file adds Opero-specific workflow, release, build, and versioning
  rules.
- If this file conflicts with the bench file on site resolution, housekeeping
  command order, or reporting, the bench file wins unless it explicitly grants
  an exception.

---

## Git Workflow

This repo uses **GitHub Flow** — `main` is the only permanent branch.

**For every piece of work:**

```bash
git checkout main
git pull origin main
git checkout -b feat/<short-description>   # or fix/, chore/, etc.
```

Work on the branch, then:

```bash
git push origin feat/<short-description>
gh pr create --base main
```

Merge the PR on GitHub, then delete the feature branch (remotely and locally).

**Rules:**
- Never push directly to `main` — always use a PR, no exceptions
- Always branch off the latest `main`
- If `main` has moved while working, rebase before opening the PR: `git rebase origin/main`
- PRs must be opened in **ready-to-merge** (open) status — never draft
- Delete feature branches after merge

---

## Pull Request Naming

- Do not include `codex`, `claude`, `ai`, or any AI-assistant name in pull request titles.
- Use product/feature-focused PR titles only.
- Pull request titles must align with the branch naming convention in `CONTRIBUTING.md`.
- If the branch uses `feat/`, `fix/`, `chore/`, or `refactor/`, use the same change type in the PR title, for example `fix/login-timeout` -> `fix: prevent login timeout loop`.

---

## Commit Style

```
type: short description
```

Types: `feat`, `fix`, `bump`, `chore`, `refactor`, `docs`

No `--no-verify`. No co-author lines — never add `Co-Authored-By` or any AI tool attribution to commits.

---

## Versioning

Stays on the `0.x.y` patch track. Bump `opero/__init__.py` (`__version__`) with each PR.

After merging to `main`:

1. Bump version and commit:
   ```bash
   # edit opero/__init__.py
   git add opero/__init__.py
   git commit -m "bump: release v<version>"
   git push origin main
   ```

2. Tag the release:
   ```bash
   git tag v<version>
   git push origin v<version>
   ```

3. Create a GitHub release with notes:
   ```bash
   gh release create v<version> --title "v<version>" --notes "..."
   ```

---

## After Code Edits (Local Testing)

After editing code and before committing, apply changes to the local site so you can verify them. Do not stop at code edits — always run and report the result.

### Site selection
- Do not hardcode a site name in commands.
- Resolve the site in this order:
  1. Use the explicit site provided by the user.
  2. Otherwise use `sites/currentsite.txt` if present and non-empty.
  3. Otherwise default to `127.0.0.1`.

### Required sequence

1. **Migrate** — run when Python/backend code changed (or when uncertain):
   ```bash
   bench --site <site> migrate
   ```

2. **Clear cache** — always run:
   ```bash
   bench --site <site> clear-cache
   ```

3. **Build assets** — run when JS/CSS changed:
   ```bash
   bench build --app opero
   ```

4. **Restart** — always run:
   ```bash
   bench restart
   ```

### Completion rule
In the final response, explicitly confirm each command was run and whether it succeeded or failed. If any command fails, include the failing command and the exact error summary.

### Relationship To Bench Rules
- This file is the canonical source for app-specific AI-tool operating rules in
  this repo.
- Bench-wide operational rules still come from
  `../../AGENTS.md`.

---

## Post-Merge

After a PR merges to `main`:

1. Sync local main:
   ```bash
   git checkout main
   git pull origin main
   ```
2. Update `CHANGELOG.md` — add a new `## <version> — <date>` section at the top with `### Added`, `### Changed`, and/or `### Fixed` entries summarising the PR
3. Follow the **Versioning** steps (bump `opero/__init__.py`, tag, GitHub release)
