# Opero AI Working Rules

All AI tools (Claude, Codex, Cursor, etc.) read from this file.

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
- Never push directly to `main` — always use a PR
- Always branch off the latest `main`
- If `main` has moved while working, rebase before opening the PR: `git rebase origin/main`
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

No co-author lines. No `--no-verify`.

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

## Post-Merge Bench Housekeeping

Run these steps after every PR merge. Do not stop at code edits — always run and report the result.

### Site selection
- Do not hardcode a site name in commands.
- Use the active bench-level default site unless the user explicitly provides one (see `common_site_config.json` → `default_site`).

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

4. **Restart**— always run:
   ```bash
   bench restart
   ```

> Also run `bench migrate` and `bench restart` before committing to verify changes locally first.

### Completion rule
In the final response, explicitly confirm each command was run and whether it succeeded or failed. If any command fails, include the failing command and the exact error summary.
