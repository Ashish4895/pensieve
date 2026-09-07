export function getCookie(name: string): string {
  const row = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith(`${name}=`));
  return row ? decodeURIComponent(row.split("=").slice(1).join("=")) : "";
}
