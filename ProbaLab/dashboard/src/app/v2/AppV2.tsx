import { Routes, Route } from 'react-router-dom';
import { v2Routes } from './routes';
import { LayoutShell } from '../../components/v2/layout/LayoutShell';

export function AppV2() {
  return (
    <div className="v2-root">
      <LayoutShell>
        <Routes>
          {v2Routes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </LayoutShell>
    </div>
  );
}

export default AppV2;
