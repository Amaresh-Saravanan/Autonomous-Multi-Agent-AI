import IncidentDetailPage from "@/components/IncidentDetailPage";

export default async function IncidentDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <IncidentDetailPage incidentId={id} />;
}
