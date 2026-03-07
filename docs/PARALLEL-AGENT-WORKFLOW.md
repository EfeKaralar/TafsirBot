# Parallel Agent Workflow

This document defines the preferred Git workflow for using multiple agents in parallel with git worktrees.

The goal is to avoid stale branches, duplicate conflict resolution, and PRs that are reviewable in isolation but unsafe to merge together.

## When To Use This

Use this workflow when:

- multiple agents will work on related tasks in the same repository
- the tasks may touch overlapping files
- you want separate worktrees and separate PRs
- one branch needs to act as the integration branch before merge to `master`

## Core Rule

Create and publish the shared integration base first.

Do not start parallel agent branches from `master` if there is already a coordination commit, contract document, or shared refactor that all agents need.

## Recommended Branch Topology

Example:

- `master`
- `issue-9-webhook-api`
  - integration branch for the current feature cluster
- `worktree-issue-9-webhook-api`
  - agent branch for API work
- `issue-10-postgres-persistence`
  - agent branch for Postgres work

In this model:

- agent branches should be based on `issue-9-webhook-api`, not `master`
- agent PRs should target `issue-9-webhook-api`, not `master`
- only after integration is complete should `issue-9-webhook-api` open a PR to `master`

## Step-By-Step Workflow

1. Create the integration branch from `master`.

2. Add and commit the shared baseline first.
   Examples:
   - contract docs
   - shared request/response schema
   - agreed migration direction
   - repo-wide coordination notes

3. Push the integration branch immediately.

4. Create worktrees for each agent from the integration branch.

5. In each worktree:
   - create a branch from the integration branch
   - pull the latest integration branch before starting
   - keep scope limited to one issue

6. Open agent PRs against the integration branch.

7. Review and merge agent PRs sequentially.

8. If a later agent PR touches files changed by an earlier merged PR:
   - rebase or merge the integration branch into that agent branch
   - resolve conflicts there
   - re-run verification
   - then review again

9. After all agent work is integrated, open one final PR from the integration branch to `master`.

## Commands

### Create the integration branch

```bash
git checkout master
git pull origin master
git checkout -b issue-9-webhook-api
git push -u origin issue-9-webhook-api
```

### Add worktrees for parallel agents

```bash
git worktree add ../TafsirBot-api issue-9-webhook-api
git worktree add ../TafsirBot-postgres issue-9-webhook-api
```

### Create agent branches inside each worktree

```bash
git checkout -b worktree-issue-9-webhook-api
git push -u origin worktree-issue-9-webhook-api
```

```bash
git checkout -b issue-10-postgres-persistence
git push -u origin issue-10-postgres-persistence
```

### Keep an agent branch current before final review

```bash
git fetch origin
git rebase origin/issue-9-webhook-api
```

If your team prefers merge instead of rebase for agent branches:

```bash
git fetch origin
git merge origin/issue-9-webhook-api
```

## PR Rules

- Agent PRs target the integration branch.
- The integration PR targets `master`.
- Do not open multiple sibling PRs to `master` when they depend on a shared baseline.
- If an agent PR becomes obsolete because its changes were integrated manually, close it with a note explaining which branch or PR superseded it.

## Review Order

Review PRs in dependency order:

1. shared contract / shared refactor
2. backend interface changes
3. persistence or storage changes
4. frontend work built against the stabilized backend

If two PRs touch the same file, do not merge both without rebasing the later one.

## What Went Wrong In The Previous Attempt

The avoidable failure mode was:

- integration baseline existed on a feature branch
- agent branches were still opened from `master`
- both agent PRs targeted `master`
- both PRs touched `scripts/rag_poc.py`
- direct PR merges would have regressed the integration baseline and forced a separate recovery step

The recovery path was cherry-picking and manual integration. That works, but it is not the preferred workflow.

## Preferred Recovery If This Happens Again

If agent PRs are already open against the wrong base:

1. stop merging those PRs
2. fetch both branches locally
3. integrate them onto the correct branch
4. push the corrected integration branch
5. open one clean PR from the integration branch to `master`
6. close the stale agent PRs as superseded

## Practical Rules For Future Runs

- freeze the shared contract first
- push the integration branch before agents start
- branch worktrees from the integration branch, not `master`
- target agent PRs to the integration branch
- merge overlapping PRs one at a time
- require a rebase before final review when overlapping files changed
- promote only the integrated branch to `master`
