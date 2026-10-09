# Design system (redesign, branch `redesign/frontend-ui`)

The console was a direct visual clone of the real GCP console (Google's own
blue, Inter, a gradient hero banner, identical rounded SaaS cards). This pass
gives it its own identity without restructuring the app: one token-level
change ripples through every page automatically, plus a hand redesign of the
navigation chrome and the home page.

## Why a token-level change

Nearly every page uses Tailwind's stock `blue-*` and `gray-*` utility classes
directly (`bg-blue-600`, `text-gray-500`, …) rather than semantic names.
Overriding what `blue` and `gray` *mean* in `tailwind.config.js` reskins the
whole app — every button, link, badge, and surface — without a page-by-page
rewrite. This is deliberate: a consistent, low-risk lever instead of 30+ files
touched by hand.

## Tokens

**Color**
- `gray-*` → Tailwind's `stone` scale (warm paper neutrals, not cool slate)
- `blue-*` → a custom deep teal ramp (`#15807A` at 600), replacing the literal
  Google blue the console was cloned in
- `rail` / `rail-hover` / `rail-border` → `#181611` / `#242018` / `#322D22`,
  the dark instrument-rail chrome (sidebar)
- Status colors (`success`/`warning`/`error`) are left alone and used *only*
  for real state (running/pending/stopped) — never for decoration, so they
  keep meaning something when you see them

**Type**
- IBM Plex Sans (UI text) + IBM Plex Mono (`font-mono`, for resource IDs,
  zone names, IPs — anything actually machine-generated, never decorative)
- Replaces Inter, which is the default every similar dashboard reaches for

**Layout**
- A persistent dark left rail (`ServiceRail.tsx`) replaces the old
  horizontal mega-menu dropdown. With 26 services across 9 categories, a
  menu that must be reopened for every navigation isn't the right shape —
  an always-visible, grouped list is. The active service expands inline to
  show its sub-pages (the mega-menu's old `sidebarLinks`), same information,
  no dead-code `DynamicSidebar` needed.
- The top bar is now just a breadcrumb + project selector — the previous
  glowing gradient logo badge is gone (that blurred-blob-behind-an-icon
  effect is one of the more common AI-generated-page tells).
- The home page (`HomePage.tsx`) drops the gradient hero banner and the
  fabricated "Recently Used" list (static fake timestamps in a dev tool
  undermine trust in what's real) for a plain status line and a dense
  service directory grouped by category — closer to a control panel than a
  marketing page.

## What this pass didn't touch

Individual service dashboard pages (Storage, Compute, VPC, …) keep their
existing layouts and copy — only their colors/type shifted via the token
change above. Bringing each one in line with the rail's information density
is a reasonable next pass, not bundled into this one.
