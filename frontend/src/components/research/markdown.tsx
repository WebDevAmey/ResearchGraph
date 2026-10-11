"use client";

import ReactMarkdown, { defaultUrlTransform, type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { Citation } from "@/components/research/citation";
import { CITE_PREFIX, citationId, linkCitations } from "@/lib/citations";
import { cn } from "@/lib/utils";

const components: Components = {
  a({ href, children }) {
    const id = citationId(href);
    if (id !== null) return <Citation id={id} />;
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  },
  // Report sections already have their own headings; demote any the model adds.
  h1: ({ children }) => <h3>{children}</h3>,
  h2: ({ children }) => <h3>{children}</h3>,
};

// react-markdown strips unknown URL schemes; let our `cite:` links through.
const urlTransform = (url: string) => (url.startsWith(CITE_PREFIX) ? url : defaultUrlTransform(url));

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("prose-report", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components} urlTransform={urlTransform}>
        {linkCitations(children)}
      </ReactMarkdown>
    </div>
  );
}
