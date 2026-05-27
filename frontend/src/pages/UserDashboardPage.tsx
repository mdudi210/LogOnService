import AppShell from "../components/AppShell";
import SelfServiceSecurityPanel from "../components/SelfServiceSecurityPanel";

export default function UserDashboardPage() {
  return (
    <AppShell role="user" title="User Security Dashboard">
      <SelfServiceSecurityPanel title="User Security Controls" />
    </AppShell>
  );
}
