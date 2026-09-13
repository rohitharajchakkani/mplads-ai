import { EmptyState } from "../components/DataState";

export default function NotFoundPage() {
  return <EmptyState title="Page not found" detail="The requested public route is not available." icon={<span className="text-lg font-semibold">404</span>} />;
}
