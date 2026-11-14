// رسائل الشبكة بين اللاعبين وصاحب الغرفة
import type { Command } from '../game/types';

export type NetMsg =
  | { t: 'hello'; from: string; name: string }
  | { t: 'cmd'; from: string; seq: number; cmd: Command }
  | { t: 'ack'; to: string; seq: number; ok: boolean; msg?: string }
  | { t: 'snap'; from: string; ep: number; sn: number; z: string }
  | { t: 'bye'; from: string }
  | { t: 'hostlost'; from: string };

function toB64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

function fromB64(b64: string): Uint8Array {
  const s = atob(b64);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

/** ضغط الحالة (gzip + base64) عشان تكون الرسائل صغيرة */
export async function pack(obj: unknown): Promise<string> {
  const json = JSON.stringify(obj);
  if (typeof CompressionStream === 'undefined' || json.length < 3000) return 'j' + json;
  const stream = new Blob([json]).stream().pipeThrough(new CompressionStream('gzip'));
  const buf = await new Response(stream).arrayBuffer();
  return 'z' + toB64(buf);
}

export async function unpack<T>(s: string): Promise<T> {
  if (s[0] === 'j') return JSON.parse(s.slice(1)) as T;
  const bytes = fromB64(s.slice(1));
  const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(stream).text()) as T;
}
