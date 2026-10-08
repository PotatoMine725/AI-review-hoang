import { VideoDetail } from "@/features/video-qa/screens";
export default async function Page({ params }: PageProps<"/merchant/library/[id]">) { const { id } = await params; return <VideoDetail id={id} />; }
