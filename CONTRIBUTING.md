# Contributing to Opero

## Git Workflow

This repo uses **GitHub Flow**. `main` is the only permanent branch and is always deployable.

### Starting work

```bash
git checkout main
git pull origin main
git checkout -b feat/my-feature
```

Use a descriptive branch name prefixed with the type:

| Prefix | Use for |
|---|---|
| `feat/` | New functionality |
| `fix/` | Bug fixes |
| `chore/` | Maintenance, deps, config |
| `refactor/` | Code changes with no behaviour change |

### Committing

```bash
git add <specific files>
git commit -m "feat: short description of what changed"
```

Keep commits focused. One logical change per commit.

### Opening a PR

```bash
git push origin feat/my-feature
gh pr create --base main
```

Before opening the PR, if `main` has moved since you branched:

```bash
git fetch origin
git rebase origin/main
```

### After merge

Delete the feature branch:

```bash
git push origin --delete feat/my-feature
git branch -d feat/my-feature
```

## Rules

- Never push directly to `main`
- Never commit secrets or `.env` files
- Always bump the version in `opero/__init__.py` with each PR
- Always tag the release after merging

## Versioning

Format: `0.MINOR.PATCH` — stay on the patch track unless there is a major breaking change.

After every PR merge, tag the release so Frappe Cloud shows a clean version history:

```bash
git checkout main && git pull origin main
git tag v0.2.15
git push origin v0.2.15
```

Tags must match the version in `opero/__init__.py` prefixed with `v`.

## Deployment

After merging to `main`:

```bash
bench --site <site> migrate
bench --site <site> clear-cache
bench restart
```
