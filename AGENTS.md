# Opero AI Working Rules

This is the single source of truth for app-specific AI-tool rules in this
repository. Other conventional instruction filenames in this repo are aliases
of this file.

## Git attribution (always)

- No product names, generated-with / made-with footers, or product
  `Co-authored-by` trailers in commits, PR titles, PR bodies, or branch names.
- Author commits as the repo owner. Match `git log origin/main`.
- After `gh pr create` or `gh pr edit`, run `gh pr view --json title,body` and
  strip any injected footer before finishing.

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
- After `gh pr create` or `gh pr edit`, run `gh pr view --json title,body` and strip any injected footer before finishing.
- `.github/workflows/sanitize-pr.yml` strips tool-name footers and `Co-authored-by` trailers from PR title/body, and fails if commit messages still contain them.

## Public site

Opero Site DocTypes load and publish Markdown in `opero-con/opero-content`. Set `opero_content_github_token` in `site_config.json` (optional `opero_content_repo`, `opero_content_base_branch`). Desk sidebar: Opero Website. Publisher lists files due for publish and the last ten GitHub commit links; Publish to website lives there. Load from website content stays on Site Settings. Load upserts by slug and does not delete extra local team members. Cubenet uses Show on website; Status is the title pill, not a form field. Checking queues To publish, or stays Published if already live. Unchecking a live record queues To unpublish; a never-live record goes back to Draft. After Publish to website succeeds (or finds the public site already up to date), To publish becomes Published and To unpublish becomes Unpublished. Drafts keep the live GitHub file unchanged. Load from GitHub marks live files Published and inactive team members Unpublished. New publications and team members start as Draft so Cubenet can edit without pushing. Publish commits to `main`; cubenet is the approval. Token needs Contents read/write on `opero-content` (no Pull requests). Do not put the token in git.


---

## Commit Style

```
type: short description
```

Types: `feat`, `fix`, `bump`, `chore`, `refactor`, `docs`

No `--no-verify`. No co-author lines — never add `Co-Authored-By` or any AI tool attribution to commits.

---

## Versioning

`opero/__init__.py` (`__version__`) tracks the last git tag. Stay on the `0.x.y` patch track.

Do not bump the version in feature PRs. Merge is not a release. Desk asset URLs cache-bust on this version, so cubenet picks up JS/CSS when you ship, not when you merge.

Cut a tag only when unreleased work on `main` has accumulated and you intend to install or deploy that snapshot. Then, in a `bump/` PR (never a direct push to `main`):

1. Set `__version__` to the new version
2. Add one `CHANGELOG.md` section covering the whole batch since the last tag
3. Merge the PR, then tag and GitHub-release:

```bash
git tag v<version>
git push origin v<version>
gh release create v<version> --title "v<version>" --notes "..."
```

Do not tag, changelog, or GitHub-release after every merge. Do not ask to ship after a single "landed".

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

1. Sync local main (`git fetch --prune`, fast-forward). Never push to `main`.
2. Delete the topic branch locally and on origin.
3. Run the post-landing scan and targeted tests.
4. Report the last tag and how many commits sit on `main` since it. Suggest a ship only when that batch has accumulated (a handful of features, end of a working day, or something you will actually install on cubenet). Otherwise stop.
