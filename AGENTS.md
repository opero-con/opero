# Opero Codex Working Rules

## Mandatory Bench Housekeeping After Code Changes

When a change is made in this app, do not stop at code edits. Always run the post-change steps and report the result.

### Default site
- Use site: `127.0.0.1` unless the user explicitly provides a different site.

### Required sequence
1. Run migrate when Python/backend code changed (or when uncertain):
   - `bench --site 127.0.0.1 migrate`
2. Clear cache:
   - `bench --site 127.0.0.1 clear-cache`
3. Build assets when JS/CSS changed:
   - `bench build --app opero`
4. Restart bench services:
   - `bench restart`

### Completion rule
- In the final response, explicitly confirm each command was run and whether it succeeded or failed.
- If any command fails, include the failing command and the exact error summary.
