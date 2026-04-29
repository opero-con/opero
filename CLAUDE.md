# Claude Instructions for Opero

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

## Deployment

After a PR merges to `main`, run on the target site:

```bash
bench --site <site> migrate
bench --site <site> clear-cache
bench restart
```

Run `bench migrate` and `bench restart` before committing so changes can be tested locally first.

## Versioning

Stays on the `0.x.y` patch track. Bump `opero/__init__.py` (`__version__`) with each PR.

After merging to `main`, tag the release:

```bash
git checkout main && git pull origin main
git tag v<version>
git push origin v<version>
```

Example: `git tag v0.2.15 && git push origin v0.2.15`

## Commit Style

```
type: short description
```

Types: `feat`, `fix`, `bump`, `chore`, `refactor`, `docs`

No co-author lines. No `--no-verify`.
