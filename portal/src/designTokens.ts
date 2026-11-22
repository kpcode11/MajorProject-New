/**
 * Design tokens and component style primitives derived from `supabase/DESIGN.md` (Phase 9, P9-02).
 *
 * Key rules from `supabase/DESIGN.md`:
 * - Single emerald primary (`#3ecf8e`) as the signature chromatic CTA and indicator;
 *   text on primary is near-black (`#171717`), NEVER white.
 * - Pure white (`#ffffff`) canvas with calibrated greyscale hierarchy (`#ededed`..`#171717`).
 * - Deep near-black (`#1c1c1c`, `canvas-night`) for code blocks, featured telemetry cards,
 *   and composited dark inspector panes.
 * - Weight 500 across display/headings with tight negative letter-spacing; weight 400 body;
 *   system monospace (`ui-monospace`) for code/telemetry snippets.
 * - Tight `6px` (`rounded.sm`) button and input radii (never pill-shaped buttons);
 *   `12px` (`rounded.lg`) card radii with `1px solid #dfdfdf` hairlines.
 */
import type { CSSProperties } from 'react';

export const SUPABASE_COLORS = {
  primary: '#34d399',
  primaryDeep: '#047857',
  primaryText: '#065f46',
  primarySoft: '#6ee7b7',
  ink: '#0f172a',
  inkSecondary: '#1e293b',
  inkMute: '#475569',
  inkMute2: '#cbd5e1',
  inkFaint: '#e2e8f0',
  onPrimary: '#0f172a',
  onDark: '#ffffff',
  canvas: '#ffffff',
  canvasSoft: '#f8fafc',
  canvasNight: '#0f172a',
  canvasNightSoft: '#1e293b',
  hairline: '#cbd5e1',
  hairlineStrong: '#94a3b8',
  hairlineCool: '#e2e8f0',
  hairlineCool2: '#f1f5f9',
  hairlineCool3: '#cbd5e1',
  accentPurple: '#4f46e5',
  accentViolet: '#4338ca',
  accentPurpleSoft: '#e0e7ff',
  accentYellow: '#f59e0b',
  accentTomato: '#dc2626',
  accentPink: '#be185d',
  accentIndigo: '#4f46e5',
  accentCrimson: '#b91c1c',
} as const;

export const SUPABASE_FONTS = {
  sans: "Circular, 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif",
  mono: "ui-monospace, Menlo, Monaco, Consolas, 'Liberation Mono', monospace",
} as const;

export const SUPABASE_RADII = {
  xs: '4px',
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
} as const;

export const SUPABASE_SPACING = {
  xxs: '2px',
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  xxl: '32px',
  huge: '64px',
} as const;

export const SUPABASE_TYPOGRAPHY: Record<string, CSSProperties> = {
  displayLg: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '36px',
    fontWeight: 500,
    lineHeight: 1.15,
    letterSpacing: '-0.72px',
    color: SUPABASE_COLORS.ink,
  },
  displayMd: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '28px',
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: '-0.42px',
    color: SUPABASE_COLORS.ink,
  },
  headingLg: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '22px',
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: '0',
    color: SUPABASE_COLORS.ink,
  },
  headingMd: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '18px',
    fontWeight: 500,
    lineHeight: 1.4,
    letterSpacing: '0',
    color: SUPABASE_COLORS.ink,
  },
  bodyMd: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '16px',
    fontWeight: 400,
    lineHeight: 1.5,
    letterSpacing: '0',
    color: SUPABASE_COLORS.ink,
  },
  buttonMd: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '14px',
    fontWeight: 500,
    lineHeight: 1.0,
    letterSpacing: '0',
  },
  caption: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '13px',
    fontWeight: 400,
    lineHeight: 1.45,
    letterSpacing: '0',
    color: SUPABASE_COLORS.inkMute,
  },
  micro: {
    fontFamily: SUPABASE_FONTS.sans,
    fontSize: '12px',
    fontWeight: 400,
    lineHeight: 1.45,
    letterSpacing: '0',
  },
  code: {
    fontFamily: SUPABASE_FONTS.mono,
    fontSize: '14px',
    fontWeight: 400,
    lineHeight: 1.5,
    letterSpacing: '0',
  },
};

export const SUPABASE_COMPONENTS = {
  buttonPrimaryGreen: {
    ...SUPABASE_TYPOGRAPHY.buttonMd,
    backgroundColor: SUPABASE_COLORS.primary,
    color: SUPABASE_COLORS.onPrimary,
    borderRadius: SUPABASE_RADII.sm,
    padding: '8px 16px',
    border: `1px solid ${SUPABASE_COLORS.primaryDeep}`,
    cursor: 'pointer',
  } satisfies CSSProperties,
  buttonSecondaryOutline: {
    ...SUPABASE_TYPOGRAPHY.buttonMd,
    backgroundColor: SUPABASE_COLORS.canvas,
    color: SUPABASE_COLORS.ink,
    borderRadius: SUPABASE_RADII.sm,
    padding: '8px 16px',
    border: `1px solid ${SUPABASE_COLORS.hairlineStrong}`,
    cursor: 'pointer',
  } satisfies CSSProperties,
  buttonOnDark: {
    ...SUPABASE_TYPOGRAPHY.buttonMd,
    backgroundColor: SUPABASE_COLORS.canvasNight,
    color: SUPABASE_COLORS.onDark,
    borderRadius: SUPABASE_RADII.sm,
    padding: '8px 16px',
    border: `1px solid ${SUPABASE_COLORS.inkSecondary}`,
    cursor: 'pointer',
  } satisfies CSSProperties,
  textInput: {
    ...SUPABASE_TYPOGRAPHY.bodyMd,
    fontSize: '14px',
    backgroundColor: SUPABASE_COLORS.canvas,
    color: SUPABASE_COLORS.ink,
    borderRadius: SUPABASE_RADII.sm,
    padding: '8px 12px',
    border: `1px solid ${SUPABASE_COLORS.hairline}`,
  } satisfies CSSProperties,
  cardFeatureLight: {
    backgroundColor: SUPABASE_COLORS.canvas,
    color: SUPABASE_COLORS.ink,
    borderRadius: SUPABASE_RADII.lg,
    padding: '24px',
    border: `1px solid ${SUPABASE_COLORS.hairline}`,
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  } satisfies CSSProperties,
  cardFeatureDark: {
    backgroundColor: SUPABASE_COLORS.canvasNight,
    color: SUPABASE_COLORS.onDark,
    borderRadius: SUPABASE_RADII.lg,
    padding: '24px',
    border: `1px solid ${SUPABASE_COLORS.inkSecondary}`,
    boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
  } satisfies CSSProperties,
  codeBlock: {
    ...SUPABASE_TYPOGRAPHY.code,
    backgroundColor: SUPABASE_COLORS.canvasNight,
    color: SUPABASE_COLORS.onDark,
    borderRadius: SUPABASE_RADII.sm,
    padding: '16px',
    border: `1px solid ${SUPABASE_COLORS.canvasNightSoft}`,
  } satisfies CSSProperties,
  pillTagGreen: {
    ...SUPABASE_TYPOGRAPHY.micro,
    backgroundColor: SUPABASE_COLORS.primary,
    color: SUPABASE_COLORS.onPrimary,
    borderRadius: SUPABASE_RADII.full,
    padding: '2px 8px',
    fontWeight: 500,
    display: 'inline-block',
  } satisfies CSSProperties,
  pillTagSoft: {
    ...SUPABASE_TYPOGRAPHY.micro,
    backgroundColor: SUPABASE_COLORS.canvasSoft,
    color: SUPABASE_COLORS.ink,
    borderRadius: SUPABASE_RADII.full,
    padding: '2px 8px',
    border: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
    display: 'inline-block',
  } satisfies CSSProperties,
} as const;
