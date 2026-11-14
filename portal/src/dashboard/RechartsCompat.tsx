/**
 * Declarative Recharts-compatible SVG chart primitives for the Phase 9 Admin Dashboard (P9-02).
 *
 * Provides `ResponsiveContainer`, `BarChart`, `Bar`, `XAxis`, `YAxis`, `CartesianGrid`,
 * `Tooltip`, `ReferenceLine`, and `Legend` components that render deterministic,
 * accessible `<svg>` charts in both browsers and `happy-dom` Vitest environments
 * without external peer-dependency conflicts.
 */
import { Children, isValidElement, type ReactElement, type ReactNode } from 'react';
import { SUPABASE_COLORS, SUPABASE_FONTS } from '../designTokens.js';

export interface ResponsiveContainerProps {
  width?: string | number;
  height?: number;
  children: ReactNode;
}

export function ResponsiveContainer({
  width = '100%',
  height = 260,
  children,
}: ResponsiveContainerProps): ReactNode {
  return (
    <div
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        minHeight: `${height}px`,
        position: 'relative',
      }}
    >
      {children}
    </div>
  );
}

export interface BarProps {
  dataKey: string;
  name?: string;
  fill?: string;
  stackId?: string;
}

export function Bar(_props: BarProps): ReactNode {
  void _props;
  return null;
}

export interface XAxisProps {
  dataKey: string;
}

export function XAxis(_props: XAxisProps): ReactNode {
  void _props;
  return null;
}

export interface YAxisProps {
  allowDecimals?: boolean;
}

export function YAxis(_props: YAxisProps): ReactNode {
  void _props;
  return null;
}

export interface CartesianGridProps {
  strokeDasharray?: string;
}

export function CartesianGrid(_props: CartesianGridProps): ReactNode {
  void _props;
  return null;
}

export function Tooltip(): ReactNode {
  return null;
}

export function Legend(): ReactNode {
  return null;
}

export interface ReferenceLineProps {
  x?: number | string;
  label?: string;
  stroke?: string;
  strokeDasharray?: string;
}

export function ReferenceLine(_props: ReferenceLineProps): ReactNode {
  void _props;
  return null;
}

export interface BarChartProps {
  data: ReadonlyArray<Record<string, unknown>>;
  width?: number;
  height?: number;
  ariaLabel?: string;
  testId?: string;
  children?: ReactNode;
}

export function BarChart({
  data,
  width = 760,
  height = 240,
  ariaLabel = 'Bar chart',
  testId,
  children,
}: BarChartProps): ReactNode {
  const bars: BarProps[] = [];
  const refLines: ReferenceLineProps[] = [];
  let xKey = 'label';

  Children.forEach(children, (child) => {
    if (!isValidElement(child)) return;
    const el = child as ReactElement<Record<string, unknown>>;
    if (el.type === Bar) {
      bars.push(el.props as unknown as BarProps);
    } else if (el.type === ReferenceLine) {
      refLines.push(el.props as unknown as ReferenceLineProps);
    } else if (el.type === XAxis && typeof el.props.dataKey === 'string') {
      xKey = el.props.dataKey;
    }
  });

  const padLeft = 44;
  const padRight = 24;
  const padTop = 28;
  const padBottom = 44;
  const plotW = Math.max(100, width - padLeft - padRight);
  const plotH = Math.max(80, height - padTop - padBottom);

  const maxTotal = Math.max(
    1,
    ...data.map((row) => {
      if (bars.some((b) => b.stackId)) {
        return bars.reduce((acc, b) => acc + Number(row[b.dataKey] ?? 0), 0);
      }
      return Math.max(0, ...bars.map((b) => Number(row[b.dataKey] ?? 0)));
    }),
  );

  const slotW = data.length > 0 ? plotW / data.length : plotW;
  const barW = Math.max(8, Math.min(44, slotW * 0.66));

  return (
    <figure style={{ margin: 0 }}>
      <svg
        role="img"
        aria-label={ariaLabel}
        data-testid={testId}
        viewBox={`0 0 ${width} ${height}`}
        style={{
          width: '100%',
          height: 'auto',
          display: 'block',
          fontFamily: SUPABASE_FONTS.sans,
        }}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = padTop + plotH * (1 - frac);
          const val = Math.round(maxTotal * frac);
          return (
            <g key={frac}>
              <line
                x1={padLeft}
                y1={y}
                x2={padLeft + plotW}
                y2={y}
                stroke={SUPABASE_COLORS.hairlineCool}
                strokeDasharray="3 3"
              />
              <text
                x={padLeft - 8}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill={SUPABASE_COLORS.inkMute}
              >
                {val}
              </text>
            </g>
          );
        })}

        {data.map((row, idx) => {
          const cx = padLeft + idx * slotW + slotW / 2;
          const xStart = cx - barW / 2;
          const labelStr = String(row[xKey] ?? idx);
          let stackedHeight = 0;

          return (
            <g key={labelStr}>
              {bars.map((bar, bIdx) => {
                const rawVal = Math.max(0, Number(row[bar.dataKey] ?? 0));
                const h = (rawVal / maxTotal) * plotH;
                const fill = bar.fill ?? SUPABASE_COLORS.primary;
                if (bar.stackId) {
                  const y = padTop + plotH - stackedHeight - h;
                  stackedHeight += h;
                  return (
                    <rect
                      key={bar.dataKey}
                      x={xStart}
                      y={y}
                      width={barW}
                      height={Math.max(0, h)}
                      fill={fill}
                      rx={2}
                    >
                      <title>{`${labelStr} · ${bar.name ?? bar.dataKey}: ${rawVal}`}</title>
                    </rect>
                  );
                }
                const singleW = barW / Math.max(1, bars.length);
                const y = padTop + plotH - h;
                return (
                  <rect
                    key={bar.dataKey}
                    x={xStart + bIdx * singleW}
                    y={y}
                    width={Math.max(4, singleW - 2)}
                    height={Math.max(0, h)}
                    fill={fill}
                    rx={2}
                  >
                    <title>{`${labelStr} · ${bar.name ?? bar.dataKey}: ${rawVal}`}</title>
                  </rect>
                );
              })}
              <text
                x={cx}
                y={padTop + plotH + 18}
                textAnchor="middle"
                fontSize="11"
                fill={SUPABASE_COLORS.inkMute}
              >
                {labelStr}
              </text>
            </g>
          );
        })}

        {refLines.map((rl, idx) => {
          const numX = typeof rl.x === 'number' ? rl.x : Number(rl.x);
          const xCoord = Number.isFinite(numX)
            ? padLeft + Math.max(0, Math.min(1, numX)) * plotW
            : padLeft + plotW / 2;
          const stroke = rl.stroke ?? SUPABASE_COLORS.ink;
          return (
            <g key={`${rl.label ?? 'ref'}-${idx}`} data-testid={`threshold-line-${idx}`}>
              <line
                x1={xCoord}
                y1={padTop - 6}
                x2={xCoord}
                y2={padTop + plotH}
                stroke={stroke}
                strokeWidth={1.75}
                strokeDasharray={rl.strokeDasharray ?? '4 4'}
              />
              {rl.label && (
                <text
                  x={xCoord + 4}
                  y={padTop + 10 + idx * 13}
                  fontSize="11"
                  fontWeight="500"
                  fill={stroke}
                  fontFamily={SUPABASE_FONTS.mono}
                >
                  {rl.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {bars.length > 0 && (
        <div
          style={{
            display: 'flex',
            gap: '16px',
            flexWrap: 'wrap',
            justifyContent: 'center',
            marginTop: '8px',
            fontSize: '12px',
            color: SUPABASE_COLORS.inkMute,
          }}
        >
          {bars.map((b) => (
            <span
              key={b.dataKey}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <span
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '2px',
                  backgroundColor: b.fill ?? SUPABASE_COLORS.primary,
                  display: 'inline-block',
                }}
              />
              {b.name ?? b.dataKey}
            </span>
          ))}
        </div>
      )}
    </figure>
  );
}
