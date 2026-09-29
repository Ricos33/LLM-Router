import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export const classifyPrompt = async (messages) => {
  const { data } = await api.post('/v1/classify', { messages });
  return data;
};

export const chatCompletion = async (messages) => {
  const { data, headers } = await api.post('/v1/chat/completions', { messages });
  return { data, headers };
};

export const getMetricsSummary = async () => {
  const { data } = await api.get('/v1/metrics/summary');
  return data;
};

export const getRecentMetrics = async (limit = 50) => {
  const { data } = await api.get(`/v1/metrics/recent?limit=${limit}`);
  return data;
};

export const getTierModels = async () => {
  const { data } = await api.get('/v1/models/tiers');
  return data;
};

export const getHealth = async () => {
  const { data } = await api.get('/health');
  return data;
};


export const getModels = async () => {
  const { data } = await api.get('/v1/models');
  return data.data; // ModelListResponse format
};

export const compareModels = async (messages, models = null, providerKeys = null) => {
  const headers = providerKeys ? { 'X-Provider-Keys': JSON.stringify(providerKeys) } : {};
  const payload = { messages };
  if (models && models.length > 0) payload.models = models;
  const { data } = await api.post('/v1/compare', payload, { headers });
  return data;
};

