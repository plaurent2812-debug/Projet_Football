import { FRONTEND_V2_ENABLED } from './lib/v2/featureFlag';
import AppLegacy from './AppLegacy';
import { AppV2 } from './app/v2/AppV2';

export default function App() {
  return FRONTEND_V2_ENABLED ? <AppV2 /> : <AppLegacy />;
}
