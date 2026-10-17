# Phase 6.4 — Reclassement complet des 2 882 articles

This release replaces Phase 6.3. Upload the contents of the ZIP to the ROOT of your existing GitHub repository, keeping folder paths. Do not upload the ZIP itself as a repository file.

GitHub → Actions → "Phase 6.4 - Reclassement editorial complet" → Run workflow → preview. Inspect the log and the attached results artifact. Then run apply to change the categories.

- 2,882 article-by-article classifications in audits/phase64_full_reclassification.csv.
- Every article has a proposed category, even when the existing category remains appropriate.
- Only rows where the proposed category differs are actually updated.
- Supabase `articles.category` is the ONLY field modified.
- A row is skipped if its title, existing category, orchestra or reviewer differs from the audit snapshot.
- Articles with reviewed_by set are protected. Existing `review_status` values, even legacy auto-validation, are not changed. Members can subsequently review and correct categories.
- No articles are deleted; no SQL migration required.
- Based on available article titles, summaries and sources, NOT complete article texts. Some classifications will be imperfect; consult the full CSV before apply.
- Snapshot created 17 Oct 2026. New articles or changed categories are not overwritten.
- The CSV is a reversible change record: category_current stores the original category. To revert, restore those original values in a separate reviewed operation (not provided as a blind automatic rollback).

The classification is a rule-assisted editorial pass, not individual full-text fact-checking. Review of the complete original articles requires retrieving their full content.
