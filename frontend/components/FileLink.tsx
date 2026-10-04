"use client";
import { download } from "@/lib/api";

/** Protected uploads need the ID token, so they are fetched then saved; external links open normally. */
export function FileLink({ name, url }: { name: string; url: string }) {
  if (url.startsWith("/api/files/")) {
    return <button type="button" className="text-left font-semibold text-brand underline" onClick={() => download(url, name).catch(() => alert("Could not download the file"))}>{name}</button>;
  }
  return <a className="font-semibold text-brand underline" href={url} target="_blank" rel="noopener noreferrer">{name}</a>;
}
