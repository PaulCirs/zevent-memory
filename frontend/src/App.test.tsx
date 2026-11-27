import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("affiche OK quand l'API répond", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{"status":"ok"}')),
    )

    render(<App />)

    expect(await screen.findByText('API : OK')).toBeInTheDocument()
  })

  it("affiche injoignable quand l'API ne répond pas", async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('réseau')))

    render(<App />)

    expect(await screen.findByText('API : injoignable')).toBeInTheDocument()
  })
})
