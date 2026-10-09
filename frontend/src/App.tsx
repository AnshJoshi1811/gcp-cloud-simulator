import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppProvider } from './contexts/AppContext';
import { ProjectProvider } from './contexts/ProjectContext';
import CloudConsoleLayout from './layouts/CloudConsoleLayout';
import HomePage from './pages/HomePage';
import PlaceholderServicePage from './pages/PlaceholderServicePage';
import StorageDashboardPage from './pages/StorageDashboardPage';
import BucketListPage from './pages/BucketListPage';
import BucketDetails from './pages/BucketDetails';
import ObjectDetailsPage from './pages/ObjectDetailsPage';
// import ActivityPage from './pages/ActivityPage';
import EventsPage from './pages/EventsPage';
import SettingsPage from './pages/SettingsPage';
import IAMDashboardPage from './pages/IAMDashboardPage';
import ComputeDashboardPage from './pages/ComputeDashboardPage';
import CreateInstancePage from './pages/CreateInstancePage';
import InstanceGroupsPage from './pages/InstanceGroupsPage';
import GKEDashboardPage from './pages/GKEDashboardPage';
import CreateClusterPage from './pages/CreateClusterPage';
import GKEClusterDetailPage from './pages/GKEClusterDetailPage';
import CloudRunDashboardPage from './pages/CloudRunDashboardPage';
import CloudRunServiceDetailPage from './pages/CloudRunServiceDetailPage';
import ArtifactRegistryPage from './pages/ArtifactRegistryPage';
import VPCDashboardPage from './pages/VPCDashboardPage';
import NetworksPage from './pages/NetworksPage';
import SubnetsPage from './pages/SubnetsPage';
import FirewallsPage from './pages/FirewallsPage';
import RoutesPage from './pages/RoutesPage';
import MonitoringDashboard from './pages/MonitoringDashboard';
import CreateMetricPage from './pages/CreateMetricPage';
import PubSubDashboardPage from './pages/PubSubDashboardPage';
import SecretManagerDashboardPage from './pages/SecretManagerDashboardPage';
import SecretDetailPage from './pages/SecretDetailPage';
import AutoscalingDashboardPage from './pages/AutoscalingDashboardPage';
import KMSDashboardPage from './pages/KMSDashboardPage';
import TasksDashboardPage from './pages/TasksDashboardPage';
import SqlDashboardPage from './pages/SqlDashboardPage';
import MemorystoreDashboardPage from './pages/MemorystoreDashboardPage';
import FirestoreDashboardPage from './pages/FirestoreDashboardPage';
import LoggingDashboardPage from './pages/LoggingDashboardPage';
import LoadBalancerDashboardPage from './pages/LoadBalancerDashboardPage';
import FunctionsDashboardPage from './pages/FunctionsDashboardPage';
import ApiGatewayDashboardPage from './pages/ApiGatewayDashboardPage';
import IdentityDashboardPage from './pages/IdentityDashboardPage';
import CdnDashboardPage from './pages/CdnDashboardPage';

function App() {
  return (
    <AppProvider>
      <ProjectProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<CloudConsoleLayout />}>
            <Route index element={<HomePage />} />
            
            {/* Service Routes */}
            <Route path="/services/:serviceName" element={<PlaceholderServicePage />} />
            
            {/* Cloud Storage Service Routes */}
            <Route path="/services/storage">
              <Route index element={<StorageDashboardPage />} />
              <Route path="buckets" element={<BucketListPage />} />
              <Route path="buckets/:bucketName" element={<BucketDetails />} />
              <Route path="buckets/:bucketName/objects/:objectName" element={<ObjectDetailsPage />} />
              <Route path="activity" element={<EventsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* IAM Service Routes */}
            <Route path="/services/iam">
              <Route index element={<IAMDashboardPage />} />
            </Route>

            {/* Compute Engine Service Routes */}
            <Route path="/services/compute-engine">
              <Route index element={<ComputeDashboardPage />} />
              <Route path="instances" element={<ComputeDashboardPage />} />
              <Route path="instances/create" element={<CreateInstancePage />} />
              <Route path="instance-groups" element={<InstanceGroupsPage />} />
            </Route>

            {/* GKE Service Routes */}
            <Route path="/services/gke">
              <Route index element={<GKEDashboardPage />} />
              <Route path="clusters" element={<GKEDashboardPage />} />
              <Route path="clusters/create" element={<CreateClusterPage />} />
              <Route path="clusters/:clusterName" element={<GKEClusterDetailPage />} />
              <Route path="node-pools" element={<GKEDashboardPage />} />
            </Route>

            {/* Cloud Run Service Routes */}
            <Route path="/services/cloud-run">
              <Route index element={<CloudRunDashboardPage />} />
              <Route path="services/:serviceName" element={<CloudRunServiceDetailPage />} />
            </Route>

            {/* Artifact Registry Service Routes */}
            <Route path="/services/artifact-registry">
              <Route index element={<ArtifactRegistryPage />} />
            </Route>

            {/* VPC Network Service Routes */}
            <Route path="/services/vpc">
              <Route index element={<VPCDashboardPage />} />
              <Route path="subnets" element={<SubnetsPage />} />
              <Route path="firewalls" element={<FirewallsPage />} />
              <Route path="routes" element={<RoutesPage />} />
            </Route>
            
            {/* Cloud Monitoring Service Routes */}
            <Route path="/services/monitoring">
              <Route index element={<MonitoringDashboard />} />
              <Route path="create-metric" element={<CreateMetricPage />} />
            </Route>

            {/* Pub/Sub Service Routes */}
            <Route path="/services/pubsub">
              <Route index element={<PubSubDashboardPage />} />
            </Route>

            {/* Secret Manager Service Routes */}
            <Route path="/services/secretmanager">
              <Route index element={<SecretManagerDashboardPage />} />
              <Route path="secrets/:secretId" element={<SecretDetailPage />} />
            </Route>

            {/* Autoscaling Service Routes */}
            <Route path="/services/autoscaling">
              <Route index element={<AutoscalingDashboardPage />} />
            </Route>

            {/* Cloud KMS Service Routes */}
            <Route path="/services/kms">
              <Route index element={<KMSDashboardPage />} />
            </Route>

            {/* Cloud Tasks Service Routes */}
            <Route path="/services/tasks">
              <Route index element={<TasksDashboardPage />} />
            </Route>

            {/* Cloud SQL Service Routes */}
            <Route path="/services/sql">
              <Route index element={<SqlDashboardPage />} />
            </Route>

            {/* Memorystore Service Routes */}
            <Route path="/services/memorystore">
              <Route index element={<MemorystoreDashboardPage />} />
            </Route>

            {/* Firestore Service Routes */}
            <Route path="/services/firestore">
              <Route index element={<FirestoreDashboardPage />} />
            </Route>

            {/* Cloud Logging Service Routes */}
            <Route path="/services/logging">
              <Route index element={<LoggingDashboardPage />} />
            </Route>

            {/* Cloud Load Balancing Service Routes */}
            <Route path="/services/loadbalancer">
              <Route index element={<LoadBalancerDashboardPage />} />
            </Route>

            {/* Cloud Functions Service Routes */}
            <Route path="/services/functions">
              <Route index element={<FunctionsDashboardPage />} />
            </Route>

            {/* API Gateway Service Routes */}
            <Route path="/services/apigateway">
              <Route index element={<ApiGatewayDashboardPage />} />
            </Route>

            {/* Cloud Identity Platform Service Routes */}
            <Route path="/services/identity">
              <Route index element={<IdentityDashboardPage />} />
            </Route>

            {/* Cloud CDN Service Routes */}
            <Route path="/services/cdn">
              <Route index element={<CdnDashboardPage />} />
            </Route>

            {/* Legacy VPC route redirect */}
            <Route path="/services/vpc/networks" element={<Navigate to="/services/vpc" replace />} />

            {/* Legacy Routes - Redirect to new structure */}
            <Route path="/buckets" element={<Navigate to="/services/storage/buckets" replace />} />
            <Route path="/events" element={<Navigate to="/services/storage/activity" replace />} />
            <Route path="/settings" element={<Navigate to="/services/storage/settings" replace />} />
          </Route>
        </Routes>
        <Toaster position="top-right" />
      </BrowserRouter>
      </ProjectProvider>
    </AppProvider>
  );
}

export default App;
