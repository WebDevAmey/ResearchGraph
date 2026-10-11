import type { Metadata } from "next";

import { ResearchView } from "@/components/research/research-view";

export const metadata: Metadata = { title: "Research" };

export default async function ResearchPage(props: PageProps<"/research/[id]">) {
  const { id } = await props.params;
  return <ResearchView id={id} />;
}
