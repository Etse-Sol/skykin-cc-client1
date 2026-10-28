import { Navigate, Route, Routes } from 'react-router-dom';
import AgentLayout from './layouts/AgentLayout';
import SupervisorLayout from './layouts/SupervisorLayout';
import AdminLayout from './layouts/AdminLayout';
import AgentHome from './pages/agent/Home';
import LiveCall from './pages/agent/LiveCall';
import CallHistory from './pages/agent/CallHistory';
import WrapUp from './pages/agent/WrapUp';
import Customer360 from './pages/agent/Customer360';
import Crm from './pages/agent/Crm';
import Consult from './pages/agent/Consult';
import Cases from './pages/agent/Cases';
import Knowledge from './pages/agent/Knowledge';
import AgentSchedule from './pages/agent/Schedule';
import AgentLearning from './pages/agent/Learning';
import SupDashboard from './pages/supervisor/Dashboard';
import Reports from './pages/supervisor/Reports';
import Wallboard from './pages/supervisor/Wallboard';
import WfmSchedule from './pages/supervisor/WfmSchedule';
import Quality from './pages/supervisor/Quality';
import Evaluation from './pages/supervisor/Evaluation';
import SupLearning from './pages/supervisor/Learning';
import Surveys from './pages/supervisor/Surveys';
import TeamRealtime from './pages/supervisor/Team';
import AiLiveFloor from './pages/supervisor/Floor';
import AdminConsole from './pages/admin/Console';
import AdminFlows from './pages/admin/Flows';
import AdminUsers from './pages/admin/Users';
import AdminRoles from './pages/admin/Roles';
import AdminSkills from './pages/admin/Skills';
import { CallReasonsReport, IvrReport } from './pages/admin/Reports';
import {
  AdminAnnouncements,
  AdminChatbot,
  AdminIvr,
  AdminKnowledge,
  AdminQueues,
  AdminSettings,
  AdminVerification,
} from './pages/admin/Placeholders';
import AgentGate from './pages/AgentGate';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AgentGate />} />
      <Route path="/agent" element={<AgentLayout />}>
        <Route index element={<Navigate to="home" replace />} />
        <Route path="home" element={<AgentHome />} />
        <Route path="calls" element={<LiveCall />} />
        <Route path="interaction" element={<LiveCall />} />
        <Route path="history" element={<CallHistory />} />
        <Route path="wrap-up" element={<WrapUp />} />
        <Route path="customers" element={<Customer360 />} />
        <Route path="crm" element={<Crm />} />
        <Route path="consult" element={<Consult />} />
        <Route path="cases" element={<Cases />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="schedule" element={<AgentSchedule />} />
        <Route path="learning" element={<AgentLearning />} />
      </Route>
      <Route path="/supervisor" element={<SupervisorLayout />}>
        <Route index element={<Navigate to="team" replace />} />
        <Route path="team" element={<TeamRealtime />} />
        <Route path="floor" element={<AiLiveFloor />} />
        <Route path="dashboard" element={<SupDashboard />} />
        <Route path="reports" element={<Reports />} />
        <Route path="wallboard" element={<Wallboard />} />
        <Route path="schedule" element={<WfmSchedule />} />
        <Route path="quality" element={<Quality />} />
        <Route path="evaluation" element={<Evaluation />} />
        <Route path="learning" element={<SupLearning />} />
        <Route path="surveys" element={<Surveys />} />
      </Route>
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="console" replace />} />
        <Route path="console" element={<AdminConsole />} />
        <Route path="ivr" element={<AdminIvr />} />
        <Route path="chatbot" element={<AdminChatbot />} />
        <Route path="flows" element={<AdminFlows />} />
        <Route path="queues" element={<AdminQueues />} />
        <Route path="announcements" element={<AdminAnnouncements />} />
        <Route path="verification" element={<AdminVerification />} />
        <Route path="knowledge" element={<AdminKnowledge />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="roles" element={<AdminRoles />} />
        <Route path="skills" element={<AdminSkills />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="reports/ivr" element={<IvrReport />} />
        <Route path="reports/reasons" element={<CallReasonsReport />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
