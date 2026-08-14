import api, { repositoryApi } from './api';

describe('api client', () => {
  test('is configured with the API base URL', () => {
    expect(api.defaults.baseURL).toBe('http://localhost:8000/api');
  });

  test('sends default JSON content-type and API key headers', async () => {
    let captured: any;
    const originalAdapter = api.defaults.adapter;
    api.defaults.adapter = (config: any) => {
      captured = config;
      return Promise.resolve({
        data: {},
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      });
    };
    try {
      await api.get('/health');
    } finally {
      api.defaults.adapter = originalAdapter;
    }
    const headers = captured.headers;
    const getHeader = (name: string) =>
      typeof headers.get === 'function' ? headers.get(name) : headers[name];
    expect(getHeader('Content-Type')).toBe('application/json');
    expect(getHeader('X-API-Key')).toBe('rie_dev_api_key');
  });

  test('exposes typed repository endpoints', () => {
    expect(typeof repositoryApi.create).toBe('function');
    expect(typeof repositoryApi.list).toBe('function');
    expect(typeof repositoryApi.get).toBe('function');
    expect(typeof repositoryApi.getStatus).toBe('function');
    expect(typeof repositoryApi.getArchitecture).toBe('function');
    expect(typeof repositoryApi.getApis).toBe('function');
    expect(typeof repositoryApi.getDatabase).toBe('function');
    expect(typeof repositoryApi.getDependencies).toBe('function');
    expect(typeof repositoryApi.getGitInsights).toBe('function');
    expect(typeof repositoryApi.getSecurity).toBe('function');
    expect(typeof repositoryApi.getPerformance).toBe('function');
    expect(typeof repositoryApi.getTechnicalDebt).toBe('function');
    expect(typeof repositoryApi.getGraph).toBe('function');
    expect(typeof repositoryApi.chat).toBe('function');
    expect(typeof repositoryApi.getSummary).toBe('function');
  });
});
