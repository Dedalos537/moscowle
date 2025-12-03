/**
 * URL utilities - returns env URLs or sensible defaults
 * NOTE: .env files are now properly configured with localhost:5001 and localhost:3001
 * These helpers provide consistent fallbacks
 */

export const getBackendUrl = (envUrl: string | undefined): string => {
  return envUrl || 'http://localhost:5001';
};

export const getDashboardUrl = (envUrl: string | undefined): string => {
  return envUrl || 'http://localhost:3001';
};
