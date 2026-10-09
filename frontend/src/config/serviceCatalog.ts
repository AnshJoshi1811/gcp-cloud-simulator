import { LucideIcon, HardDrive, Cpu, Network, Shield, MessageSquare, Activity, Globe, Lock, Route, Box, Server, Layers, Cloud, PackageSearch, Key, Gauge, KeyRound, ListChecks, Database, FolderTree, ScrollText, Workflow, Zap } from 'lucide-react';

export interface ServiceLink {
  label: string;
  path: string;
  icon?: LucideIcon;
}

export interface Service {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  category: string;
  enabled: boolean;
  sidebarLinks?: ServiceLink[];
}

export interface ServiceCategory {
  id: string;
  name: string;
  services: Service[];
}

export const serviceCategories: ServiceCategory[] = [
  {
    id: 'storage',
    name: 'Storage',
    services: [
      {
        id: 'storage',
        name: 'Cloud Storage',
        description: 'Object storage for companies of all sizes',
        icon: HardDrive,
        category: 'Storage',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/storage' },
          { label: 'Buckets', path: '/services/storage/buckets', icon: HardDrive },
          { label: 'Activity', path: '/services/storage/activity', icon: Activity },
          { label: 'Settings', path: '/services/storage/settings' },
        ],
      },
    ],
  },
  {
    id: 'compute',
    name: 'Compute',
    services: [
      {
        id: 'compute-engine',
        name: 'Compute Engine',
        description: 'Virtual machines running in Google\'s data center',
        icon: Cpu,
        category: 'Compute',
        enabled: true,
        sidebarLinks: [
          { label: 'VM Instances', path: '/services/compute-engine/instances', icon: Cpu },
          { label: 'Instance Groups', path: '/services/compute-engine/instance-groups', icon: Server },
        ],
      },
    ],
  },
  {
    id: 'networking',
    name: 'Networking',
    services: [
      {
        id: 'vpc',
        name: 'VPC Network',
        description: 'Virtual Private Cloud and networking',
        icon: Network,
        category: 'Networking',
        enabled: true,
        sidebarLinks: [
          { label: 'VPC Networks', path: '/services/vpc/networks', icon: Globe },
          { label: 'Subnets', path: '/services/vpc/subnets', icon: Network },
          { label: 'Firewall Rules', path: '/services/vpc/firewalls', icon: Lock },
          { label: 'Routes', path: '/services/vpc/routes', icon: Route },
        ],
      },
      {
        id: 'loadbalancer',
        name: 'Cloud Load Balancing',
        description: 'Distribute traffic across backend instances',
        icon: Workflow,
        category: 'Networking',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/loadbalancer', icon: Workflow },
        ],
      },
    ],
  },
  {
    id: 'iam',
    name: 'IAM & Admin',
    services: [
      {
        id: 'iam',
        name: 'IAM',
        description: 'Identity and Access Management',
        icon: Shield,
        category: 'IAM & Admin',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/iam' },
          { label: 'Service Accounts', path: '/services/iam/service-accounts', icon: Shield },
          { label: 'IAM Policies', path: '/services/iam/policies' },
        ],
      },
    ],
  },
  {
    id: 'containers',
    name: 'Containers',
    services: [
      {
        id: 'gke',
        name: 'Kubernetes Engine',
        description: 'Managed Kubernetes service for containerised workloads',
        icon: Box,
        category: 'Containers',
        enabled: true,
        sidebarLinks: [
          { label: 'Clusters', path: '/services/gke/clusters', icon: Server },
          { label: 'Node Pools', path: '/services/gke/node-pools', icon: Layers },
        ],
      },
      {
        id: 'cloud-run',
        name: 'Cloud Run',
        description: 'Serverless containers with revision and traffic controls',
        icon: Cloud,
        category: 'Containers',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/cloud-run', icon: Cloud },
          { label: 'Services', path: '/services/cloud-run', icon: Server },
        ],
      },
      {
        id: 'functions',
        name: 'Cloud Functions',
        description: 'Deploy and invoke serverless functions',
        icon: Zap,
        category: 'Containers',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/functions', icon: Zap },
          { label: 'Functions', path: '/services/functions', icon: Zap },
        ],
      },
      {
        id: 'artifact-registry',
        name: 'Artifact Registry',
        description: 'Container image repositories and local registry simulation',
        icon: PackageSearch,
        category: 'Containers',
        enabled: true,
        sidebarLinks: [
          { label: 'Repositories', path: '/services/artifact-registry', icon: PackageSearch },
        ],
      },
    ],
  },
  {
    id: 'messaging',
    name: 'Messaging',
    services: [
      {
        id: 'pubsub',
        name: 'Pub/Sub',
        description: 'Messaging and ingestion for event-driven systems',
        icon: MessageSquare,
        category: 'Messaging',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/pubsub', icon: MessageSquare },
          { label: 'Topics', path: '/services/pubsub', icon: MessageSquare },
          { label: 'Subscriptions', path: '/services/pubsub', icon: MessageSquare },
        ],
      },
    ],
  },
  {
    id: 'security',
    name: 'Security',
    services: [
      {
        id: 'secretmanager',
        name: 'Secret Manager',
        description: 'Store and manage secrets securely',
        icon: Key,
        category: 'Security',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/secretmanager', icon: Key },
          { label: 'Secrets', path: '/services/secretmanager', icon: Key },
        ],
      },
      {
        id: 'kms',
        name: 'Cloud KMS',
        description: 'Manage encryption keys and encrypt/decrypt data',
        icon: KeyRound,
        category: 'Security',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/kms', icon: KeyRound },
          { label: 'Key Rings', path: '/services/kms', icon: KeyRound },
        ],
      },
    ],
  },
  {
    id: 'integration',
    name: 'Application Integration',
    services: [
      {
        id: 'tasks',
        name: 'Cloud Tasks',
        description: 'Managed task queues for asynchronous execution',
        icon: ListChecks,
        category: 'Application Integration',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/tasks', icon: ListChecks },
          { label: 'Queues', path: '/services/tasks', icon: ListChecks },
        ],
      },
    ],
  },
  {
    id: 'databases',
    name: 'Databases',
    services: [
      {
        id: 'sql',
        name: 'Cloud SQL',
        description: 'Managed PostgreSQL and MySQL instances',
        icon: Database,
        category: 'Databases',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/sql', icon: Database },
          { label: 'Instances', path: '/services/sql', icon: Database },
        ],
      },
      {
        id: 'memorystore',
        name: 'Memorystore',
        description: 'Managed Redis instances for caching',
        icon: Gauge,
        category: 'Databases',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/memorystore', icon: Gauge },
          { label: 'Instances', path: '/services/memorystore', icon: Gauge },
        ],
      },
      {
        id: 'firestore',
        name: 'Firestore',
        description: 'NoSQL document database',
        icon: FolderTree,
        category: 'Databases',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/firestore', icon: FolderTree },
          { label: 'Collections', path: '/services/firestore', icon: FolderTree },
        ],
      },
    ],
  },
  {
    id: 'monitoring',
    name: 'Monitoring',
    services: [
      {
        id: 'monitoring',
        name: 'Cloud Monitoring',
        description: 'Monitor your Google Cloud and AWS resources',
        icon: Activity,
        category: 'Monitoring',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/monitoring', icon: Activity },
          { label: 'Metrics', path: '/services/monitoring', icon: Activity },
          { label: 'Alerts', path: '/services/monitoring', icon: Activity },
        ],
      },
      {
        id: 'autoscaling',
        name: 'Autoscaling',
        description: 'Automatic scaling policies for compute resources',
        icon: Gauge,
        category: 'Monitoring',
        enabled: true,
        sidebarLinks: [
          { label: 'Dashboard', path: '/services/autoscaling', icon: Gauge },
          { label: 'Policies', path: '/services/autoscaling', icon: Gauge },
        ],
      },
      {
        id: 'logging',
        name: 'Cloud Logging',
        description: 'Aggregate, filter, and query logs across services',
        icon: ScrollText,
        category: 'Monitoring',
        enabled: true,
        sidebarLinks: [
          { label: 'Logs Explorer', path: '/services/logging', icon: ScrollText },
        ],
      },
    ],
  },
];

export const getAllServices = (): Service[] => {
  return serviceCategories.flatMap(category => category.services);
};

export const getServiceById = (serviceId: string): Service | undefined => {
  return getAllServices().find(service => service.id === serviceId);
};
