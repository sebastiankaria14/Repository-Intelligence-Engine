import { renderHook, waitFor } from '@testing-library/react';
import { repositoryApi } from '../lib/api';
import { useRepository } from './useRepository';

vi.mock('../lib/api');

const mockedGet = vi.mocked(repositoryApi.get);
const mockedGetStatus = vi.mocked(repositoryApi.getStatus);

describe('useRepository', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('fetches repository and scan job for a given repoId', async () => {
    mockedGet.mockResolvedValue({
      data: { id: 'repo-1', name: 'acme/webapp', total_files: 42, total_lines: 1337 },
    });
    mockedGetStatus.mockResolvedValue({
      data: { id: 'scan-1', status: 'completed', progress: 100, current_phase: 'done' },
    });

    const { result } = renderHook(() => useRepository('repo-1'));

    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.repository?.id).toBe('repo-1'));

    expect(mockedGet).toHaveBeenCalledWith('repo-1');
    expect(mockedGetStatus).toHaveBeenCalledWith('repo-1');
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
    expect(mockedGet).not.toHaveBeenCalled();
  });

  test('surfaces an error when the fetch fails', async () => {
    mockedGet.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useRepository('repo-1'));

    await waitFor(() => expect(result.current.error).toBe('Network error'));
    expect(result.current.repository).toBeNull();
  });
});
