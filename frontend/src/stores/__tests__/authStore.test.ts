import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '../authStore';

// Mock the auth API
vi.mock('@/api/services', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    getMe: vi.fn(),
  },
}));

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state between tests
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('clears state on logout', () => {
    // Set some state first
    useAuthStore.setState({
      user: { id: '1', email: 'test@test.com', full_name: 'Test', created_at: '' },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    });
    localStorage.setItem('access_token', 'token');
    localStorage.setItem('refresh_token', 'refresh');

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('clears error with clearError', () => {
    useAuthStore.setState({ error: 'some error' });
    useAuthStore.getState().clearError();
    expect(useAuthStore.getState().error).toBeNull();
  });

  it('login sets loading state', async () => {
    const { authApi } = await import('@/api/services');
    (authApi.login as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('fail'));

    const promise = useAuthStore.getState().login('a@b.com', 'pass');

    // isLoading should have been set before the await
    // After rejection it should be false again
    await expect(promise).rejects.toThrow('fail');
    expect(useAuthStore.getState().isLoading).toBe(false);
    expect(useAuthStore.getState().error).toBe('fail');
  });

  it('register sets loading state', async () => {
    const { authApi } = await import('@/api/services');
    (authApi.register as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

    await useAuthStore.getState().register('a@b.com', 'pass', 'Name');

    expect(useAuthStore.getState().isLoading).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(false); // registration doesn't auto-login
  });
});
