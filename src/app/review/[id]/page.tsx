import { ReviewDetail } from "@/features/reviews/review-detail";

export default async function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReviewDetail id={id} />;
}
