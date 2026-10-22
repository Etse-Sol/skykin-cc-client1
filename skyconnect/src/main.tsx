import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { SoftphoneProvider } from './softphone/SoftphoneContext';
import './index.css';

/** Same headset file as the sign-in page. Do not use /favicon.ico (old SkyKin cloud). */
function applySkyConnectFavicon() {
  const href = '/app/agent_dashboard/assets/skykin-favicon.png?v=6';
  document
    .querySelectorAll('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]')
    .forEach((el) => el.parentElement?.removeChild(el));
  const icon = document.createElement('link');
  icon.rel = 'icon';
  icon.type = 'image/png';
  icon.href = href;
  document.head.appendChild(icon);
  const apple = document.createElement('link');
  apple.rel = 'apple-touch-icon';
  apple.href = '/app/agent_dashboard/assets/apple-touch-icon.png?v=6';
  document.head.appendChild(apple);
}
applySkyConnectFavicon();

const basename = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') || undefined;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <SoftphoneProvider>
        <App />
      </SoftphoneProvider>
    </BrowserRouter>
  </StrictMode>,
);
