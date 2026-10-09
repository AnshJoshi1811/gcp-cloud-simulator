import { Link, useLocation } from 'react-router-dom';
import { LayoutGrid, Cloud } from 'lucide-react';
import { serviceCategories } from '../../config/serviceCatalog';

/**
 * The persistent left-hand navigation rail. Replaces the old horizontal
 * mega-menu dropdown: with 26 services across 9 categories, a dropdown that
 * has to be re-opened for every navigation isn't the right shape for this
 * much surface area — an always-visible, grouped list is.
 */
interface ServiceRailProps {
  onNavigate?: () => void;
}

export default function ServiceRail({ onNavigate }: ServiceRailProps) {
  const location = useLocation();
  const activeServiceId = location.pathname.split('/')[2];

  const isServiceActive = (id: string) => activeServiceId === id;
  const isHome = location.pathname === '/';

  return (
    <aside className="w-64 flex-shrink-0 bg-rail text-stone-300 flex flex-col h-full">
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-rail-border flex-shrink-0">
        <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center flex-shrink-0">
          <Cloud className="w-4 h-4 text-white" strokeWidth={2} />
        </div>
        <div className="flex flex-col leading-none min-w-0">
          <span className="text-[13.5px] font-semibold text-white truncate">Cloud Stimulator</span>
          <span className="text-[11px] text-stone-500 mt-0.5">Local emulator</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-3 custom-scrollbar">
        <Link
          to="/"
          onClick={onNavigate}
          className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm mb-3 transition-colors ${
            isHome ? 'bg-rail-hover text-white' : 'text-stone-300 hover:bg-rail-hover hover:text-white'
          }`}
        >
          <LayoutGrid className="w-4 h-4 flex-shrink-0" />
          Control room
        </Link>

        {serviceCategories.map((category) => (
          <div key={category.id} className="mb-4">
            <p className="px-3 mb-1 text-[11px] font-medium tracking-wide text-stone-500 uppercase">
              {category.name}
            </p>
            <ul>
              {category.services.map((service) => {
                const Icon = service.icon;
                const active = isServiceActive(service.id);
                return (
                  <li key={service.id}>
                    <Link
                      to={`/services/${service.id}`}
                      onClick={onNavigate}
                      aria-disabled={!service.enabled}
                      className={`group flex items-center gap-2.5 px-3 py-[7px] rounded-md text-[13.5px] transition-colors ${
                        active
                          ? 'bg-blue-600/15 text-blue-200 font-medium border-l-2 border-blue-400 -ml-px pl-[11px]'
                          : service.enabled
                          ? 'text-stone-300 hover:bg-rail-hover hover:text-white'
                          : 'text-stone-600 cursor-default pointer-events-none'
                      }`}
                    >
                      <Icon className={`w-4 h-4 flex-shrink-0 ${active ? 'text-blue-300' : ''}`} />
                      <span className="truncate flex-1">{service.name}</span>
                      {!service.enabled && (
                        <span className="text-[10px] text-stone-600 flex-shrink-0">soon</span>
                      )}
                    </Link>

                    {active && service.sidebarLinks && service.sidebarLinks.length > 1 && (
                      <ul className="ml-[26px] mt-0.5 mb-1 border-l border-rail-border">
                        {service.sidebarLinks.map((link) => {
                          const subActive = location.pathname === link.path;
                          return (
                            <li key={link.path}>
                              <Link
                                to={link.path}
                                onClick={onNavigate}
                                className={`block pl-3 pr-2 py-1 text-[12.5px] -ml-px border-l ${
                                  subActive
                                    ? 'border-blue-400 text-blue-200'
                                    : 'border-transparent text-stone-400 hover:text-stone-200'
                                }`}
                              >
                                {link.label}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
