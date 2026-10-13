"use client";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Header } from "./header";
import { StorageNotice } from "@/features/studio/common";
import { usePreferences } from "@/features/studio/preferences";
export function WorkspaceShell({ children }: { children: ReactNode }) {
  const creator = usePathname().startsWith("/creator");
  const { sidebarCollapsed } = usePreferences();
  return <div className={`studio-app ${creator ? "creator-app" : "admin-app"} ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}><Header /><main id="main-content" className="studio-main" tabIndex={-1}><StorageNotice />{children}</main></div>;
}
