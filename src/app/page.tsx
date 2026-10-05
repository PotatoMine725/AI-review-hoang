import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">AI Review Content Factory</h1>
      <p className="text-muted-foreground">
        Khung dự án tuần 1. Chưa có tính năng.
      </p>
      <Button>shadcn/ui hoạt động</Button>
    </main>
  );
}
