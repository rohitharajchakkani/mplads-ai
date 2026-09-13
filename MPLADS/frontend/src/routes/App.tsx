import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { LoadingBlock } from "../components/DataState";
import { AdminShell } from "../layouts/AdminShell";
import { AppShell } from "../layouts/AppShell";
import { MonitoringShell } from "../layouts/MonitoringShell";
import { MonitoringAccessProvider } from "../monitoring/MonitoringAccess";
import { AccessRequestsPage, AuditLogsPage, ConfigurationPage, DataQualityPage, DatasetsPage, SystemHealthPage, UsersPage } from "../pages/AdminPages";
import { AskAiPage } from "../pages/AskAiPage";
import { ExecutivePage } from "../pages/ExecutivePage";
import { AlertDetailPage, AlertsPage, AnomaliesPage, BenchmarkingPage, DuplicatesPage, FinancialPage, LifecyclePage, MonitoringOverviewPage, ReviewCaseDetailPage, RecommendationsPage, ReviewsPage, RiskDetailPage, RiskPage } from "../pages/MonitoringPages";
const HomePage = lazy(() => import("../pages/HomePage")); const DashboardPage = lazy(() => import("../pages/DashboardPage")); const ExplorerPage = lazy(() => import("../pages/ExplorerPage")); const EntityDetailPage = lazy(() => import("../pages/EntityDetailPage")); const WorksPage = lazy(() => import("../pages/WorksPage")); const WorkDetailPage = lazy(() => import("../pages/WorkDetailPage")); const StatisticsPage = lazy(() => import("../pages/StatisticsPage")); const SearchPage = lazy(() => import("../pages/SearchPage")); const AboutPage = lazy(() => import("../pages/AboutPage")); const NotFoundPage = lazy(() => import("../pages/NotFoundPage"));
export function App() {
  return <MonitoringAccessProvider><Suspense fallback={<div className="page-container py-10"><LoadingBlock label="Opening page…" /></div>}><Routes><Route element={<AppShell />}>
    <Route path="/" element={<HomePage />} /><Route path="/dashboard" element={<DashboardPage />} />
    <Route path="/mps" element={<ExplorerPage type="mps" />} /><Route path="/mps/:id" element={<EntityDetailPage type="mp" />} />
    <Route path="/states" element={<ExplorerPage type="states" />} /><Route path="/states/:id" element={<EntityDetailPage type="state" />} />
    <Route path="/districts" element={<ExplorerPage type="districts" />} /><Route path="/districts/:id" element={<EntityDetailPage type="district" />} />
    <Route path="/works" element={<WorksPage />} /><Route path="/works/*" element={<WorkDetailPage />} />
    <Route path="/statistics" element={<StatisticsPage />} /><Route path="/search" element={<SearchPage />} /><Route path="/about" element={<AboutPage />} />
    <Route element={<MonitoringShell />}>
      <Route path="/monitoring" element={<MonitoringOverviewPage />} /><Route path="/monitoring/ai" element={<AskAiPage />} />
      <Route path="/monitoring/executive" element={<ExecutivePage />} /><Route path="/monitoring/executive/attention" element={<ExecutivePage />} /><Route path="/monitoring/executive/trends" element={<ExecutivePage />} /><Route path="/monitoring/executive/geography" element={<ExecutivePage />} /><Route path="/monitoring/executive/comparison" element={<ExecutivePage />} /><Route path="/monitoring/executive/drilldown" element={<ExecutivePage />} />
      <Route path="/monitoring/risk" element={<RiskPage />} /><Route path="/monitoring/risk/*" element={<RiskDetailPage />} /><Route path="/monitoring/alerts" element={<AlertsPage />} /><Route path="/monitoring/alerts/:id" element={<AlertDetailPage />} />
      <Route path="/monitoring/duplicates" element={<DuplicatesPage />} /><Route path="/monitoring/anomalies" element={<AnomaliesPage />} /><Route path="/monitoring/financial" element={<FinancialPage />} /><Route path="/monitoring/lifecycle" element={<LifecyclePage />} />
      <Route path="/monitoring/reviews" element={<ReviewsPage />} /><Route path="/monitoring/reviews/:caseId" element={<ReviewCaseDetailPage />} /><Route path="/monitoring/benchmarking" element={<BenchmarkingPage />} /><Route path="/monitoring/recommendations" element={<RecommendationsPage />} />
    </Route>
    <Route element={<AdminShell />}>
      <Route path="/admin/access-requests" element={<AccessRequestsPage />} /><Route path="/admin/users" element={<UsersPage />} /><Route path="/admin/datasets" element={<DatasetsPage />} />
      <Route path="/admin/data-quality" element={<DataQualityPage />} /><Route path="/admin/audit-logs" element={<AuditLogsPage />} /><Route path="/admin/system" element={<SystemHealthPage />} /><Route path="/admin/configuration" element={<ConfigurationPage />} />
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Route></Routes></Suspense></MonitoringAccessProvider>;
}
