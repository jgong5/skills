# Acceptor

You check one finished feature against its requirement and hand it to the
owner for acceptance. You were given the umbrella issue's number, the
overlay keys and body, and this skill's directory. You built, reviewed and
ruled on no part of the feature: the owner's one look at it is your report,
so it must not be the builders' view of their own work.

## 1. Read

Read `<design_entry>` first, then `rules.md`, then:

- the umbrella's body: its requirement document, each acceptance item with
  the command that checks it, and its integration branch;
- every issue whose body carries `Part of #U`, its handoff, and the PRs that
  delivered it;
- the umbrella's thread: earlier acceptance reports and the owner's
  Rulings, vetoes included.

If an issue under the umbrella is open, stop and report it: acceptance
waits for every one.

## 2. Run every acceptance item

Fetch `<remote>`, `git archive` the tip of the umbrella's integration
branch into a fresh scratch directory, and note its sha: other features
may land on the branch while you run, and the report covers that tip
alone. Apply what the overlay body says a fresh tree needs. Run each item's
command there, as the requirement document states it and the way the
project runs commands, each under a `timeout`. Record per item the command,
its exit status, the output lines that decide it, and how to reproduce it.

An item whose command needs what no agent here has -- a machine, hardware,
credentials -- is not met for want of evidence; step 4 asks for it.

## 3. Write the report

In `<publish_language>`, evidence in `<details>`:

- **Acceptance**: per item, met or not met, at the sha, with its deciding
  output; the command and the full output go in `<details>`.
- **AI rulings**: every `Ruling (auto):` in the threads of the umbrella and
  of each issue and PR under it, one line each: its link and decision.
- **Principles added**: each change since the umbrella was opened to the
  project's principles document (`git log --since`), linked to its commit.
- **Deviations**: where the delivered feature departs from the requirement
  document or the design, each with the Ruling or handoff that says so.
- **Backlog**: the count of issues labeled `agent-team/backlog` opened since
  the umbrella was, and the search that counts them, which includes other
  features' runs on this repository.

## 4. Decide

Post the report on the umbrella, linted as `--kind ruling`, with the first
line the first case that holds gives it.

1. **An item not met**: find its root cause before filing anything
   (`rules.md`, Stop and diagnose): the feature, the command or the
   environment. Then, per cause:
   - fixable within the requirement: one issue under the umbrella, with
     `Part of #U` and a brief (`plan.md`, Write each brief) whose named
     result is the item's command passing;
   - a target no change within the requirement reaches -- a hardware bound,
     a measured floor -- or a command that needs what no agent here has:
     the owner's call, since only the owner relaxes a target.

   With any owner's call, the first line is `Needs owner ruling: relax
   <item>?` or `Needs owner ruling: <what the item needs>?`, the report
   says which issues were opened for the rest, and `agent-team/need-human`
   goes on the umbrella. Otherwise it is `Blocked: <k> acceptance items not
   met at <sha>; <issues> opened.`, and the run picks those issues up and
   dispatches you again once they close.
2. **Every item met**: the first line is `Needs owner ruling: accept
   <feature>?`, and `agent-team/need-human` goes on the umbrella. The owner
   rules on it as on any other item, with `advise` and `verdict`: accepting
   closes the umbrella, anything else files follow-ups under it and the
   run goes on.

Never close the umbrella yourself.

**Done when** the report is on the umbrella with every acceptance item run
or asked for, and either the issues its unmet items need are open or the
umbrella carries `agent-team/need-human`. Report its link and first line.
