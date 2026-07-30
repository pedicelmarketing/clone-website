/**
 * Every route, from one file.
 *
 * An OPTIONAL catch-all (`[[...slug]]`) rather than `page.tsx` + `[slug]`,
 * because a plan with no extra pages makes `generateStaticParams()` return an
 * empty array, and `output: export` rejects a dynamic route with no params
 * outright ("Page /[slug] is missing generateStaticParams()"). Every plan
 * written before multi-page existed is exactly that case, so the two-file
 * arrangement broke every single-page brand.
 *
 * The catch-all also keeps the layout vocabulary in ONE page chunk shared by
 * all routes. Five route folders would emit five chunks, and Gate 10 caps the
 * whole bundle at 300 KB gzipped.
 *
 * `generateMetadata` is what gives each route its own <title>; Gate 11 asserts
 * those are unique across routes, because forgetting it is the classic
 * static-export mistake and nothing else in the harness can see it.
 */

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPages, loadDesignPlan } from "@/lib/design-plan";
import { PageBody } from "@/components/page-body";

const plan = loadDesignPlan();

type Params = { slug?: string[] };

/** `/` is `slug: []`; `/about/` is `slug: ["about"]`. */
export function generateStaticParams(): Params[] {
  return getPages(plan).map((p) => (p.slug ? { slug: [p.slug] } : { slug: [] }));
}

function pageFor(slug?: string[]) {
  const key = slug?.[0] ?? "";
  return getPages(plan).find((p) => p.slug === key);
}

export async function generateMetadata(
  { params }: { params: Promise<Params> },
): Promise<Metadata> {
  const page = pageFor((await params).slug);
  return { title: page?.title, description: page?.description || undefined };
}

export default async function Page({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const page = pageFor(slug);
  if (!page) notFound();
  return <PageBody plan={plan} slug={page.slug} />;
}
