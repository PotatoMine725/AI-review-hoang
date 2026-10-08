import { VideoDetail } from "@/features/video-qa/screens";
export default async function Page({ params }: PageProps<"/admin/videos/[id]">) { const { id } = await params; return <VideoDetail id={id} admin />; }
