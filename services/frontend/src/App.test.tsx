import { render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { vi } from 'vitest'

import App from './App'
import { store } from './app/store'

test('silently attempts session refresh before rendering auth routes', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Refreshed',
          data: { access: 'expired-access' },
          errors: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          success: false,
          message: 'Unable to load user',
          data: null,
          errors: null,
        }),
      }),
  )

  render(
    <Provider store={store}>
      <App />
    </Provider>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Pensieve' }),
  ).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledWith(
    '/api/v1/auth/refresh/',
    expect.objectContaining({ credentials: 'include' }),
  )
  expect(fetch).toHaveBeenCalledWith(
    '/api/v1/auth/me/',
    expect.objectContaining({
      credentials: 'include',
      headers: expect.any(Headers),
    }),
  )
  expect(store.getState().auth.access).toBeNull()
})
