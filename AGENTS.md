# Opero AI assist Working Rules

## Pull Request Naming

- Do not include `codex`, `claude`, `ai`, or any AI-assistant name in pull request titles.
- Use product/feature-focused PR titles only.
- Pull request titles must align with the branch naming convention in `CONTRIBUTING.md`.
- If the branch uses `feat/`, `fix/`, `chore/`, or `refactor/`, use the same change type in the PR title, for example `fix/login-timeout` -> `fix: prevent login timeout loop`.

## Mandatory Bench Housekeeping After Code Changes

When a change is made in this app, do not stop at code edits. Always run the post-change steps and report the result.

### Site selection
- Do not hardcode a site name in commands.
- Use the active bench-level site resolution rule unless the user explicitly provides a site.

### Required sequence
1. Run migrate when Python/backend code changed (or when uncertain):
   - `bench --site <site> migrate`
2. Clear cache:
   - `bench --site <site> clear-cache`
3. Build assets when JS/CSS changed:
   - `bench build --app opero`
4. Restart bench services:
   - `bench restart`

### Completion rule
- In the final response, explicitly confirm each command was run and whether it succeeded or failed.
- If any command fails, include the failing command and the exact error summary.
