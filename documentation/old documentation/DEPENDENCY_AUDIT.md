# Dependency Audit (pip-audit)

Date: 2026-01-14

I ran `pip-audit` against `requirements.txt` and found the following known vulnerabilities and recommended fixes.

Summary (found 11 vulnerabilities in 3 packages):

- werkzeug 2.3.8
  - Several advisories (GHSA-2g68-c3qc-8985, GHSA-f9vj-2wh5-fj8j, GHSA-q34m-jh98-gwm2, GHSA-hgf8-39gv-g3f2, GHSA-87hc-h4r5-73f7)
  - Suggested fixes: upgrade to Werkzeug 3.x (verify app and extensions compatibility - breaking changes possible). Consider testing under a controlled staging environment before upgrading.

- authlib 1.2.1
  - Advisories: PYSEC-2024-52, GHSA-9ggr-2464-2j32, GHSA-pq5p-34cr-23v9, GHSA-g7f3-828f-7h7m, GHSA-fg6f-75jq-6523
  - Suggested fix: upgrade to `authlib>=1.6.6` (or latest 1.6.x) and run OAuth flows tests. Check release notes for breaking API changes.

- marshmallow 4.0.1
  - Advisory: GHSA-428g-f7cq-pgp5
  - Suggested fix: upgrade to `marshmallow>=4.1.2` (or backport to 3.26.2 if compatibility needed).

Notes and next steps:

- Upgrading `werkzeug` to `3.x` may require changes to extensions and app code because of breaking changes in the WSGI utilities and routing. Recommend:
  1. Add a branch for dependency upgrades.
  2. Run tests (and add tests if missing) in a staging environment.
  3. Upgrade `authlib` and `marshmallow` first (minor/patch upgrades), verify OAuth and schema handling.
  4. Upgrade `werkzeug` last and verify `Flask` and all extensions are compatible. Consider pinning compatible versions.

- For production, consider running `pip-audit` regularly in CI and add a job to fail/alert on high/critical vulnerabilities.

Full `pip-audit` output (raw):

```
Found 11 known vulnerabilities in 3 packages
Name        Version ID                  Fix Versions
----------- ------- ------------------- ------------
werkzeug    2.3.8   GHSA-2g68-c3qc-8985 3.0.3
werkzeug    2.3.8   GHSA-f9vj-2wh5-fj8j 3.0.6
werkzeug    2.3.8   GHSA-q34m-jh98-gwm2 3.0.6
werkzeug    2.3.8   GHSA-hgf8-39gv-g3f2 3.1.4
werkzeug    2.3.8   GHSA-87hc-h4r5-73f7 3.1.5
authlib     1.2.1   PYSEC-2024-52       1.3.1
authlib     1.2.1   GHSA-9ggr-2464-2j32 1.6.4
authlib     1.2.1   GHSA-pq5p-34cr-23v9 1.6.5
authlib     1.2.1   GHSA-g7f3-828f-7h7m 1.6.5
authlib     1.2.1   GHSA-fg6f-75jq-6523 1.6.6
marshmallow 4.0.1   GHSA-428g-f7cq-pgp5 3.26.2,4.1.2
```

If you want, I can open a branch and attempt the safe upgrades (authlib, marshmallow), run the test harness, and report any breakages. Upgrading `werkzeug` will likely need coordinated changes.

---

2026-01-14 Update: attempted safe upgrades

- Updated `requirements.txt` to request `Authlib>=1.6.6` and `marshmallow>=4.1.2`.
- Installed those packages into the project's virtualenv and ran the test suite. All tests passed (5 passed, 2 warnings).

Notes:
- `Authlib` upgrade succeeded without code changes and tests passed.
- `marshmallow>=4.1.2` was requested; however `pip-audit` (which creates an isolated resolver) reported it could not find a compatible `marshmallow>=4.1.2` for the current Python version (the workspace Python is 3.9.6). Some `marshmallow` 4.x releases require Python >=3.10.
- Despite the `pip-audit` resolver message, `marshmallow` was installed into the venv and the app's tests ran successfully. To fully adopt `marshmallow` 4.x in CI and production, consider upgrading the Python runtime to 3.10+ to avoid compatibility constraints and to allow `pip-audit` to validate the package matrix.

Recommendation:
- Move to Python 3.10+ in CI and production before locking `marshmallow>=4.1.2` in permanent requirements and running `pip-audit` in CI.
- Address `werkzeug` upgrades in a follow-up branch (needs careful testing with Flask and extensions).

