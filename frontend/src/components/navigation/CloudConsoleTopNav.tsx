import { useLocation, Link } from 'react-router-dom';
import { ChevronRight, Menu } from 'lucide-react';
import ProjectSelector from '../ProjectSelector';
import { getServiceById } from '../../config/serviceCatalog';

interface Breadcrumb {
  label: string;
  path: string;
}

interface CloudConsoleTopNavProps {
  onMenuClick?: () => void;
}

const CloudConsoleTopNav = ({ onMenuClick }: CloudConsoleTopNavProps) => {
  const location = useLocation();

  const getBreadcrumbs = (): Breadcrumb[] => {
    const paths = location.pathname.split('/').filter(Boolean);

    if (paths.length === 0) {
      return [{ label: 'Control room', path: '/' }];
    }

    const breadcrumbs: Breadcrumb[] = [];

    // Handle /services/{serviceName} routes
    if (paths[0] === 'services' && paths[1]) {
      const service = getServiceById(paths[1]);
      if (service) {
        breadcrumbs.push({ label: service.name, path: `/services/${paths[1]}` });

        if (paths[1] === 'storage') {
          if (paths[2] === 'buckets') {
            breadcrumbs.push({ label: 'Buckets', path: `/services/storage/buckets` });
            if (paths[3]) {
              breadcrumbs.push({
                label: decodeURIComponent(paths[3]),
                path: `/services/storage/buckets/${paths[3]}`,
              });
              if (paths[4] === 'objects' && paths[5]) {
                breadcrumbs.push({
                  label: decodeURIComponent(paths[5]),
                  path: `/services/storage/buckets/${paths[3]}/objects/${paths[5]}`,
                });
              }
            }
          } else if (paths[2] === 'settings') {
            breadcrumbs.push({ label: 'Settings', path: `/services/storage/settings` });
          }
        }
      }
    }

    return breadcrumbs.length > 0 ? breadcrumbs : [{ label: 'Control room', path: '/' }];
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex-shrink-0">
      <div className="h-full px-4 md:px-6 flex items-center justify-between gap-6">
        <nav className="flex items-center gap-1.5 min-w-0 overflow-x-auto no-scrollbar">
          <button
            type="button"
            onClick={onMenuClick}
            className="md:hidden p-1.5 -ml-1.5 mr-1 rounded hover:bg-gray-100 flex-shrink-0"
            aria-label="Open navigation"
          >
            <Menu className="w-5 h-5 text-gray-700" />
          </button>
          <Link to="/" className="text-sm text-gray-500 hover:text-gray-900 flex-shrink-0">
            Home
          </Link>
          {breadcrumbs.map((crumb) => (
            <div key={crumb.path} className="flex items-center gap-1.5 flex-shrink-0">
              <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
              <Link
                to={crumb.path}
                className="text-sm font-medium text-gray-900 px-1 py-0.5 rounded hover:bg-gray-100"
              >
                {crumb.label}
              </Link>
            </div>
          ))}
        </nav>

        <div className="flex items-center gap-4 flex-shrink-0">
          <ProjectSelector />
        </div>
      </div>
    </header>
  );
};

export default CloudConsoleTopNav;
