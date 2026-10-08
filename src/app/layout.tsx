import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "./workspace.css";
import "./pkb.css";
import { WorkspaceProvider } from "@/features/content-factory/workspace-provider";
import { WorkspaceShell } from "@/features/workspace/shell";
import { ErrorBoundary } from "@/features/workspace/error-boundary";
import { VideoProvider } from "@/features/video-qa/provider";
import { UnsavedChangesGuard } from "@/features/content-factory/use-unsaved-changes";
import "./roles.css";
import "./leader.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Review Content Factory",
  description: "AI review video factory & affiliate network",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="vi"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <UnsavedChangesGuard />
        <ErrorBoundary>
          <WorkspaceProvider>
            <VideoProvider><WorkspaceShell>{children}</WorkspaceShell></VideoProvider>
          </WorkspaceProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
