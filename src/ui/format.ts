// تنسيق الأرقام والتواريخ بالعربي
import { DAYS_PER_MONTH, MONTHS, START_YEAR } from '../game/defs';

export function fmtMoney(b: number): string {
  const neg = b < 0;
  const x = Math.abs(b);
  let out: string;
  if (x >= 1000) out = `${(x / 1000).toFixed(x >= 10000 ? 0 : 1)} تريليون`;
  else if (x >= 10) out = `${Math.round(x)} مليار`;
  else if (x >= 1) out = `${x.toFixed(1)} مليار`;
  else out = `${Math.round(x * 1000)} مليون`;
  return (neg ? '-' : '') + out;
}

export function fmtMoneyShort(b: number): string {
  const neg = b < 0;
  const x = Math.abs(b);
  let out: string;
  if (x >= 1000) out = `${(x / 1000).toFixed(x >= 10000 ? 0 : 1)}T`;
  else if (x >= 10) out = `${Math.round(x)}B`;
  else if (x >= 1) out = `${x.toFixed(1)}B`;
  else out = `${Math.round(x * 1000)}M`;
  return (neg ? '-' : '') + '$' + out;
}

export function fmtPop(m: number): string {
  if (m >= 1000) return `${(m / 1000).toFixed(2)} مليار`;
  if (m >= 10) return `${Math.round(m)} مليون`;
  if (m >= 1) return `${m.toFixed(1)} مليون`;
  return `${Math.round(m * 1000)} ألف`;
}

export function fmtNum(n: number): string {
  return Math.round(n).toLocaleString('en-US');
}

export function fmtArea(km2: number): string {
  if (km2 >= 1e6) return `${(km2 / 1e6).toFixed(2)} مليون كم²`;
  if (km2 >= 1000) return `${Math.round(km2 / 1000)} ألف كم²`;
  return `${Math.round(km2)} كم²`;
}

export function dateStr(day: number): string {
  const m = Math.floor(day / DAYS_PER_MONTH);
  return `${MONTHS[m % 12]} ${START_YEAR + Math.floor(m / 12)}`;
}

export function fullDate(day: number): string {
  const d = (Math.floor(day) % DAYS_PER_MONTH) + 1;
  return `${d} ${dateStr(day)}`;
}

export function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
}

export function plural(n: number, one: string, two: string, many: string): string {
  if (n === 1) return one;
  if (n === 2) return two;
  return `${n} ${many}`;
}
