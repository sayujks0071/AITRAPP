/**
 * MSW browser setup
 * Import this in your app entry point when using mock mode
 */

import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);



