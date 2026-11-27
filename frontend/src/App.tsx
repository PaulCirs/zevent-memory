import { useEffect, useState } from 'react'

type Health = { status: 'loading' } | { status: 'ok' } | { status: 'error' }

export default function App() {
  const [health, setHealth] = useState<Health>({ status: 'loading' })

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        setHealth(response.ok ? { status: 'ok' } : { status: 'error' })
      })
      .catch(() => {
        setHealth({ status: 'error' })
      })
  }, [])

  return (
    <main>
      <h1>ZEvent Memory</h1>
      <p>
        API :{' '}
        {health.status === 'loading'
          ? 'vérification…'
          : health.status === 'ok'
            ? 'OK'
            : 'injoignable'}
      </p>
    </main>
  )
}
