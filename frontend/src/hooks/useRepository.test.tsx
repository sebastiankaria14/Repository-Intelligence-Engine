import { renderHook, waitFor } from '@testing-library/react';
import { repositoryApi } from '../lib/api';
import { useRepository } from './useRepository';

vi.mock('../lib/api');

const mockedGetSummary = vi.mocked(repositoryApi.getSummary);

describe('useRepository', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('fetches repository and scan job for a given repoId', async () => {
    mockedGetSummary.mockResolvedValue({
      repository: { id: 'repo-1', name: 'acme/webapp', total_files: 42, total_lines: 1337 } as any,
      scan_job: { id: 'scan-1', status: 'completed', progress: 100, current_phase: 'done' } as any,
      architecture: null,
      apis: null,
      database: null,
      dependencies: null,
      git_insights: null,
      security: null,
      performance: null,
      technical_debt: null,
    });

    const { result } = renderHook(() => useRepository('repo-1'));

    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.repository?.id).toBe('repo-1'));

    expect(mockedGetSummary).toHaveBeenCalledWith('repo-1');
    expect(result.current.repository?.name).toBe('acme/webapp');
    expect(result.current.scanJob?.status).toBe('completed');
    expect(result.current.scanJob?.progress).toBe(100);
    expect(result.current.loading).toBe(false);
  });

  test('returns null repository when repoId is null', () => {
    const { result } = renderHook(() => useRepository(null));

    expect(result.current.repository).toBeNull();
    expect(result.current.scanJob).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(mockedGetSummary).not.toHaveBeenCalled();
  });

  test('surfaces an error when the fetch fails', async () => {
    mockedGetSummary.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useRepository('repo-error'));

    await waitFor(() => expect(result.current.error).toBe('Network error'));
    expect(result.current.repository).toBeNull();
  });
});
