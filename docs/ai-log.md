# AI Study Assistant 2.0 - Learning Log

## Project Progress

- Following AI Study Assistant 2.0 Updated Specification and Learning Roadmap Version 2.1.
- Phase 0: Git and project housekeeping.

## What I Learned

- A Git tag marks an important project version.
- A commit message briefly describes a change.
- Environment files and secret keys must never be committed to Git.

## Current Status

- Project 1 tag: v1.0
- Project 2 tag: v2.0-alpha
- backend/.env.example created.
- quiz_routes.py indentation corrections made locally.
- Git diff discrepancy still needs resolution.

## 2026-11-10 — Phase 1, Step 2 Progress

- Reviewed and approved the nine database entities and their relationships.
- Reviewed and approved table fields and deletion rules.
- Approved the nine RLS ownership rules.
- Inspected existing database constraints and indexes.
- Verified 46 owned study_history records: one owner, no empty questions or answers, and no missing timestamps.
- Identified 5 study_history records with NULL user_id. These must be preserved without assigning an unknown owner.
- Verified 5 existing quizzes containing 23 complete quiz questions.
- Reviewed the initial docs/schema.sql draft. It remains incomplete and has NOT been executed in Supabase.
- No database migration or schema changes have been executed.

Next: Complete the migration design, finalize and review docs/schema.sql, then follow the Version 2.1 roadmap for migration and two-user RLS testing.
