import type { Metadata } from "next";
import { LandingPage } from "@/features/marketing/landing";

export const metadata: Metadata = {
  title: "Reviewlab — Từ link sản phẩm đến video review",
  description: "Khám phá Reviewlab: nhập link sản phẩm, kiểm tra thông tin và sáng tạo video review trong một không gian làm việc.",
};

export default function Home() {
  return <LandingPage />;
}
