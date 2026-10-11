import { describe, expect, it } from "vitest";

import { citationId, linkCitations, splitCitations } from "@/lib/citations";

describe("linkCitations", () => {
  it("turns markers into cite links", () => {
    expect(linkCitations("A claim [1][3].")).toBe("A claim [1](cite:1)[3](cite:3).");
  });

  it("leaves real markdown links alone", () => {
    expect(linkCitations("See [2](https://x.com) and [4].")).toBe(
      "See [2](https://x.com) and [4](cite:4).",
    );
  });
});

describe("citationId", () => {
  it("parses cite hrefs only", () => {
    expect(citationId("cite:12")).toBe(12);
    expect(citationId("https://example.com")).toBeNull();
    expect(citationId(undefined)).toBeNull();
  });
});

describe("splitCitations", () => {
  it("splits text and citation numbers", () => {
    expect(splitCitations("Finding [1][2] holds.")).toEqual(["Finding ", 1, 2, " holds."]);
    expect(splitCitations("No markers")).toEqual(["No markers"]);
  });
});
