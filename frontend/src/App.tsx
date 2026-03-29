import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLayout } from "@/components/AppLayout";
import { isLoggedIn } from "@/lib/api";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Timeline from "./pages/Timeline";
import Analytics from "./pages/Analytics";
import FocusReport from "./pages/FocusReport";
import AICoach from "./pages/AICoach";
import SessionHistory from "./pages/SessionHistory";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected routes */}
          <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
            <Route path="/" element={<Index />} />
            <Route path="/session/:id/timeline" element={<Timeline />} />
            <Route path="/session/:id/analytics" element={<Analytics />} />
            <Route path="/session/:id/report" element={<FocusReport />} />
            <Route path="/session/:id/insights" element={<AICoach />} />
            <Route path="/sessions" element={<SessionHistory />} />
            <Route path="/profile" element={<Profile />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
