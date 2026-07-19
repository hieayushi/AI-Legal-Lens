"use client";
import { useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/ui/Sidebar";
import { Menu, Scale } from "lucide-react";

const NO_SIDEBAR_ROUTES = ["/login"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const showSidebar = !NO_SIDEBAR_ROUTES.includes(pathname);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (!showSidebar) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-parchment">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex flex-col flex-1 min-w-0 h-screen overflow-hidden">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-parchment-border lg:hidden flex-shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 rounded-lg text-ink-soft hover:bg-parchment-warm hover:text-ink transition-colors focus:outline-none"
              aria-label="Toggle Sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-6.5 h-6.5 bg-brand rounded-lg flex items-center justify-center">
                <Scale className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-display font-bold text-ink text-sm">LegalLens</span>
            </div>
          </div>
          <div className="w-8" />
        </header>

        <main className="flex-1 overflow-y-auto min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
