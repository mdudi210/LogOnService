export function getCookie(name: string): string | null {
  const key = `${name}=`;
  const parts = document.cookie.split(';').map((c) => c.trim());
  for (const part of parts) {
    if (part.startsWith(key)) {
      return decodeURIComponent(part.slice(key.length));
    }
  }
  return null;
}
