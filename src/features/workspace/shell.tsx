import type { ReactNode } from "react";
import { Header } from "./header";
import { Footer } from "./footer";

export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <div className="factory-app">
      <Header />
      <div className="factory-main workspace-main">
        <main id="main-content" className="factory-content workspace-content" tabIndex={-1}>{children}</main>
        <Footer />
      </div>
    </div>
  );
}
