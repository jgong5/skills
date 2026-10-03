`thread` sorts on `submittedAt`, which is null for a pending review, so the sort raises `TypeError`. Drop entries with no `submittedAt` before sorting; `pr_state.py:41` has the same sort.
