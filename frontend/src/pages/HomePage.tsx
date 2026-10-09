import { Link } from 'react-router-dom';
import { serviceCategories } from '../config/serviceCatalog';
import { ArrowUpRight } from 'lucide-react';

const HomePage = () => {
  const allServices = serviceCategories.flatMap((category) => category.services);
  const enabledServices = allServices.filter((service) => service.enabled);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-6xl mx-auto px-8 py-10">
        {/* Header + status strip */}
        <div className="flex items-start justify-between gap-8 mb-10 pb-8 border-b border-gray-200">
          <div>
            <h1 className="text-[22px] font-semibold text-gray-900 mb-1.5">Control room</h1>
            <p className="text-sm text-gray-500 max-w-md">
              Local GCP emulator. Resources you create here run as real Docker containers
              and networks on this machine — nothing touches a real cloud account.
            </p>
          </div>

          <dl className="flex items-stretch gap-6 flex-shrink-0 text-sm">
            <div className="text-right">
              <dt className="text-gray-500 text-xs mb-1">Backend</dt>
              <dd className="flex items-center justify-end gap-1.5 font-medium text-gray-900">
                <span className="w-1.5 h-1.5 rounded-full bg-success" />
                localhost:8080
              </dd>
            </div>
            <div className="text-right">
              <dt className="text-gray-500 text-xs mb-1">Services implemented</dt>
              <dd className="font-medium text-gray-900">{enabledServices.length} of {allServices.length}</dd>
            </div>
          </dl>
        </div>

        {/* Service directory, grouped by category */}
        <div className="space-y-10">
          {serviceCategories.map((category) => (
            <section key={category.id}>
              <h2 className="text-[13px] font-medium text-gray-500 uppercase tracking-wide mb-3">
                {category.name}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {category.services.map((service) => {
                  const Icon = service.icon;
                  if (!service.enabled) {
                    return (
                      <div
                        key={service.id}
                        className="flex items-start gap-3 rounded-lg border border-dashed border-gray-200 p-4 opacity-60"
                      >
                        <div className="p-2 rounded-md bg-gray-100 flex-shrink-0">
                          <Icon className="w-4 h-4 text-gray-400" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="text-sm font-medium text-gray-500">{service.name}</h3>
                          <p className="text-xs text-gray-400 mt-0.5">Coming soon</p>
                        </div>
                      </div>
                    );
                  }
                  return (
                    <Link
                      key={service.id}
                      to={`/services/${service.id}`}
                      className="group flex items-start gap-3 rounded-lg border border-gray-200 p-4 hover:border-blue-300 hover:bg-blue-50/40 transition-colors"
                    >
                      <div className="p-2 rounded-md bg-gray-100 group-hover:bg-blue-100 transition-colors flex-shrink-0">
                        <Icon className="w-4 h-4 text-gray-600 group-hover:text-blue-700" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-medium text-gray-900 flex items-center gap-1">
                          {service.name}
                          <ArrowUpRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-blue-500 flex-shrink-0" />
                        </h3>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{service.description}</p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HomePage;
