import { useParams, NavLink } from "react-router-dom";
import { BarChart3, FileText, Brain, Clock } from "lucide-react";

const tabs = [
  { label: "Timeline", path: "timeline", icon: Clock },
  { label: "Analytics", path: "analytics", icon: BarChart3 },
  { label: "Report", path: "report", icon: FileText },
  { label: "AI Coach", path: "insights", icon: Brain },
];

export function SessionSubNav() {
  const { id } = useParams();

  return (
    <nav className="flex gap-1 border-b border-border mb-4">
      {tabs.map((tab) => (
        <NavLink
          key={tab.path}
          to={`/session/${id}/${tab.path}`}
          className={({ isActive }) =>
            `flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              isActive
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`
          }
        >
          <tab.icon className="h-4 w-4" />
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
