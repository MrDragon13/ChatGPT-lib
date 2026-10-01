const encoder = new TextEncoder();
const decoder = new TextDecoder();

export function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function base64UrlDecode(value: string): Uint8Array {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(value.replace(/-/g, "+").replace(/_/g, "/") + padding);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export function randomUrlSafe(byteLength = 32): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

export async function sha256UrlSafe(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return base64UrlEncode(new Uint8Array(digest));
}

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

export async function signJson(value: unknown, secret: string): Promise<string> {
  const payload = base64UrlEncode(encoder.encode(JSON.stringify(value)));
  const signature = await crypto.subtle.sign("HMAC", await hmacKey(secret), encoder.encode(payload));
  return `${payload}.${base64UrlEncode(new Uint8Array(signature))}`;
}

export async function verifySignedJson<T>(token: string, secret: string): Promise<T> {
  const [payload, signature, extra] = token.split(".");
  if (!payload || !signature || extra !== undefined) throw new Error("invalid signed token");
  const valid = await crypto.subtle.verify(
    "HMAC",
    await hmacKey(secret),
    base64UrlDecode(signature),
    encoder.encode(payload),
  );
  if (!valid) throw new Error("invalid signed token");
  try {
    return JSON.parse(decoder.decode(base64UrlDecode(payload))) as T;
  } catch {
    throw new Error("invalid signed token");
  }
}
