---
name: BotGuard Resident Portal
description: Calm, privacy-first resident services and security operations
colors:
  primary: "#3ecf8e"
  primary-deep: "#24b47e"
  foreground: "#171717"
  muted: "#626762"
  canvas: "#f7f8f7"
  card: "#ffffff"
  border: "#d9ddd9"
  danger: "#e2005a"
  warning: "#a16207"
  dark-canvas: "#171b19"
  dark-card: "#202522"
  dark-foreground: "#f2f5f3"
  dark-muted: "#afb9b2"
  dark-border: "#39413c"
typography:
  body:
    fontFamily: "Aptos, Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Aptos, Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.45
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
spacing:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
---

# Design System: BotGuard Resident Portal

## Overview

**Creative North Star: "The Calm Security Desk."**

BotGuard is calm, privacy-first, and technically precise. The resident flow is direct; the security
console is dense but readable. Emerald identifies primary and positive states. Neutral surfaces carry
information. Crimson is reserved for errors and destructive actions.

## Colors

- Primary: Emerald `#3ecf8e`; hover: Deep Emerald `#24b47e`.
- Light: Ink `#171717`, muted `#626762`, canvas `#f7f8f7`, card `#ffffff`, border `#d9ddd9`.
- Semantic: Crimson `#e2005a`, warning `#a16207`.
- Dark: Canvas `#171b19`, card `#202522`, foreground `#f2f5f3`, muted `#afb9b2`, border `#39413c`.

Never use state color alone.

## Typography

Use Aptos or Segoe UI with system fallbacks. Use monospace only for code and telemetry.
Body is 14-16px with 1.55 line-height; labels are 12-13px with 1.45 line-height.

## Layout

Use a 64px sticky header, 48px compact navigation, `1280px` resident width, and `1320px` console.
Desktop page padding is 48px/24px; mobile is 32px/16px. Controls are at least 40px.
Collapse grids below 760px and scroll tables horizontally.

## Components

Place the theme toggle in the top header utility area. Use emerald primary buttons, hairline secondary
buttons, explicit input labels, visible focus, and compact semantic status. Cards represent one
concept; do not nest cards.

## Do's and Don'ts

Do preserve routes and test IDs, support both themes and keyboard use, keep privacy copy visible, and
test at 1440x900, 768x1024, and 390x844. Do not use gradients, hard shadows, glass, decorative icons,
nested cards, near-black dashboard shells, or all-caps long labels.
