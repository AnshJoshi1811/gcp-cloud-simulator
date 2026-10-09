import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import CloudConsoleTopNav from '../components/navigation/CloudConsoleTopNav';
import ServiceRail from '../components/navigation/ServiceRail';

const CloudConsoleLayout = () => {
  const [railOpen, setRailOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Below md, the rail becomes an overlay toggled from the top bar
          instead of a fixed 256px column — on a phone-width screen that
          column alone would eat most of the viewport. */}
      <div className={`${railOpen ? 'fixed inset-0 z-40 flex md:static md:z-auto' : 'hidden md:flex'}`}>
        {railOpen && (
          <div
            className="fixed inset-0 bg-black/40 md:hidden"
            onClick={() => setRailOpen(false)}
          />
        )}
        <div className="relative z-10">
          <ServiceRail onNavigate={() => setRailOpen(false)} />
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <CloudConsoleTopNav onMenuClick={() => setRailOpen(true)} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default CloudConsoleLayout;
