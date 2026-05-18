spot my epic

# Epic: Comments on Dashboards

## Problem

Users open dashboards in the morning and want to react to what they see — "this number looks wrong," "we expected this to spike last week," "context for new viewers." Today they have nowhere to write that down. They paste screenshots into Slack and the context dies there.

Support has logged 47 tickets in the last quarter from users asking how to "annotate" a dashboard. Customer interviews with three enterprise accounts (Acme Health, Northwind, Lattice Logistics) confirm the same pattern: their analyst writes the context, their executives read the dashboard, and the two never meet.

## Hypothesis

If we let users leave threaded comments on individual tiles within a dashboard, comment-to-link engagement goes up, and the dashboards become the place the work happens instead of the place the work is reported on. Slack screenshot traffic should drop.

## Proposed solution

- A comments side panel that opens from any dashboard

- Comments anchor to a specific tile, identified by tile ID

- Replies thread under each comment

- @-mentions notify the recipient via the existing notification system

- A comment count badge appears on each tile

- Markdown support for code blocks and bold

We're piggybacking on the existing notification service and the existing user-mention system. No new infra.

## Out of scope

- Page-level (whole-dashboard) comments — tile-level only for v1

- Resolving / archiving — we'll add in v2 based on usage

- Exporting comments to PDF — defer

## Acceptance criteria

- A user with view access can add a comment to any tile

- @-mention sends a notification within 30 seconds

- Comment count badge updates in real time across open sessions

- Existing dashboards continue to render with no migration needed

## Competitive landscape

Tableau and Power BI both have some form of dashboard commenting. Looker gates it behind their Enterprise tier.

## Packaging

Free for all paid tiers. No new SKU.

## Holistic impact

The Notifications team needs to add a new notification type. The Mobile team has confirmed they can render the comment count badge but threaded reading is web-only for v1.