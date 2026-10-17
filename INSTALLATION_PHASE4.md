# Observatoire Orchestral — Phase 4 consolidated release

## Install (one GitHub upload)

This ZIP is a **complete repository snapshot** based on the supplied project archive, with Phase 3.1 classification, Phase 3 coverage queries, and Phase 4 improvements merged. The source archive may be older than your live repository. **Before replacing your repository, compare the ZIP with your latest GitHub version, especially `config.js`, the GitHub workflow, and any changes since the supplied archive.** Do not overwrite current settings or later features without reviewing the differences.

Safest route: upload only the changed files from this ZIP to their corresponding paths, after reviewing them: `scripts/classification.py`, `scripts/collect.py`, `scripts/monitoring_queries.py`, `scripts/test_phase4.py`, `assets/app.js`, `index.html`, `style.css`, `sw.js`. Leave your existing `config.js`, secrets, Supabase database and accounts untouched.

No SQL migration required. `supabase/read_only_quality_audit.sql` is optional, read-only. **Do not run old `supabase/schema.sql`.**

## What changes
- Topic-first classification and title-based rejection of obvious ticket/archives; preserves existing rows.
- Broad orchestra searches with shared queries.
- Collector prints inserted vs duplicates vs excluded (counts are based on Supabase representation response).
- Member approval check before showing the dashboard (server-side RLS must still enforce access).
- Quick topic navigation and clearer article counts.
- PWA cache version bump to refresh UI assets.

## Tests
`python -m unittest discover -s scripts -p 'test_phase4.py'` (requires no API keys).
`python -m unittest discover -s scripts -p 'test_phase31.py'` (legacy tests; some may be based on earlier assumptions).

## Limits
- No live Supabase integration test; source site 403/503 errors remain possible.
- Existing articles are NOT reclassified or deleted.
- Full review article text extraction remains limited by publisher access.
- No automatic mass approval or account creation.
- Current website still fetches up to 5,000 records client-side; scalable server pagination is a future upgrade.
