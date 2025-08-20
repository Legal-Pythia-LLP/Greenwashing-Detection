import { Link, NavLink } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import { LanguageSelector } from "@/components/LanguageSelector";

const TopNav = () => {
  const { t } = useTranslation();
  
  return (
    <header className="sticky top-0 z-30 backdrop-blur supports-[backdrop-filter]:bg-background/70 bg-background/80 border-b">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-6 w-6 rounded [background-image:var(--gradient-primary)] shadow-[var(--shadow-glow)]" aria-hidden />
          <span className="font-semibold tracking-tight">{t('nav.title')}</span>
        </Link>
        <div className="flex items-center gap-3">
          <NavLink to="/" className={({ isActive }) => cn("px-3 py-2 rounded-md text-sm", isActive ? "bg-secondary" : "hover:bg-secondary")}>{t('nav.dashboard')}</NavLink>
          <NavLink to="/upload" className={({ isActive }) => cn("px-3 py-2 rounded-md text-sm", isActive ? "bg-secondary" : "hover:bg-secondary")}>{t('nav.upload')}</NavLink>
          <Button asChild>
            <Link to="/upload">{t('nav.newAnalysis')}</Link>
          </Button>
          <LanguageSelector />
        </div>
      </nav>
    </header>
  );
};

export default TopNav;
