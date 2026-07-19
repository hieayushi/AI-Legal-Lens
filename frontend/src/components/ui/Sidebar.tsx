"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Upload, MessageSquare, Search,
  Building2, BarChart2, FlaskConical, Shield, Scale,
  LogOut, X,
} from "lucide-react";
import { clsx } from "clsx";
import { useAuthStore } from "@/lib/store";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/query", label: "Ask LegalLens", icon: MessageSquare },
  { href: "/search", label: "Case Search", icon: Search },
  { href: "/governance", label: "Governance", icon: Building2 },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/evaluation", label: "Evaluation", icon: FlaskConical },
  { href: "/admin", label: "Admin", icon: Shield },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <>
      {/* Backdrop overlay for mobile drawer */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-ink/20 backdrop-blur-sm lg:hidden transition-opacity duration-200"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          "w-60 flex-shrink-0 bg-white border-r border-parchment-border flex flex-col h-screen",
          "fixed inset-y-0 left-0 z-50 lg:static lg:translate-x-0 transition-transform duration-200 ease-in-out",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b border-parchment-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="font-display font-bold text-ink text-sm leading-tight">LegalLens</div>
              <div className="text-[10px] text-ink-muted font-medium tracking-wide uppercase">AI Platform</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-ink-soft hover:bg-parchment-warm hover:text-ink lg:hidden transition-colors focus:outline-none"
            aria-label="Close Sidebar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-150",
                  active
                    ? "bg-brand-light text-brand font-medium"
                    : "text-ink-soft hover:bg-parchment-warm hover:text-ink"
                )}
              >
                <Icon className={clsx("w-4 h-4 flex-shrink-0", active ? "text-brand" : "")} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        {user && (
          <div className="px-3 py-3 border-t border-parchment-border">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-7 h-7 rounded-full bg-brand-light flex items-center justify-center text-brand text-xs font-bold flex-shrink-0">
                {user.full_name?.[0]?.toUpperCase() || "U"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-ink truncate">{user.full_name}</div>
                <div className="text-[10px] text-ink-muted capitalize">{user.role}</div>
              </div>
              <button onClick={logout} className="text-ink-muted hover:text-verdict-red transition-colors focus:outline-none">
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
