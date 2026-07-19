import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { installFailureSink } from './shell/errorLog.ts';

// Before anything renders, so a failure during the first paint is recorded too. This is the
// production caller `setFailureSink` went without: until now a failed write reached the console
// and an in-memory array that died with the tab.
installFailureSink();

const el = document.getElementById('root');
if (!el) throw new Error('#root not found');

createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
