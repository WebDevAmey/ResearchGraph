// Report text cites sources as [3] or [2][5]. Before rendering markdown we turn
// each marker into a link with a `cite:` href, which the renderer swaps for an
// interactive <Citation>. Markdown links like [text](url) are left untouched.

const MARKER = /\[(\d+)\](?!\()/g;

export const CITE_PREFIX = "cite:";

export function linkCitations(markdown: string): string {
  return markdown.replace(MARKER, (_, id) => `[${id}](${CITE_PREFIX}${id})`);
}

export function citationId(href: string | undefined): number | null {
  if (!href?.startsWith(CITE_PREFIX)) return null;
  const id = Number(href.slice(CITE_PREFIX.length));
  return Number.isInteger(id) ? id : null;
}

/** Splits plain text (no markdown) into text and citation parts. */
export function splitCitations(text: string): (string | number)[] {
  const parts: (string | number)[] = [];
  let last = 0;
  for (const match of text.matchAll(/\[(\d+)\]/g)) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    parts.push(Number(match[1]));
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}
