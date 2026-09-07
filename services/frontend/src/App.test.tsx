import { render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { vi } from 'vitest'

import App from './App'
import { store } from './app/store'

test('silently attempts session refresh before rendering auth routes', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        success: false,
        message: 'No session',
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
})
