import { useEffect, useState } from 'react'

async function get(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${path} -> ${r.status}`)
  return r.json()
}

function usePoll(fn, ms) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      fn()
        .then((d) => alive && (setData(d), setError(null)))
        .catch((e) => alive && setError(String(e)))
    tick()
    const h = setInterval(tick, ms)
    return () => { alive = false; clearInterval(h) }
  }, [])
  return [data, error]
}

function Pill({ v }) {
  return <span className={`pill ${v}`}>{v}</span>
}

export default function App() {
  const [sit, sitErr] = usePoll(() => get('/api/situation'), 4000)
  const [orders] = usePoll(() => get('/api/orders?limit=8'), 4000)
  const [products] = usePoll(() => get('/api/products'), 8000)
  const [scores] = usePoll(() => get('/api/scores?limit=5'), 10000)

  return (
    <>
      <header>
        <h1>WORK_RES Dashboard</h1>
        <p>React + Vite · live from the same API · {sitErr ? <span className="err">{sitErr} (is the API on :8000?)</span> : 'connected'}</p>
      </header>
      <main>
        <div className="grid">
          <div className="card"><h3>Availability</h3>
            <div className="big">{sit ? `${sit.traffic.availability_pct}%` : '…'}</div>
            <div className="sub">target 99.9 · RPS {sit?.traffic.rps ?? '…'}</div></div>
          <div className="card"><h3>p95 latency</h3>
            <div className="big">{sit ? `${sit.traffic.p95_ms}ms` : '…'}</div>
            <div className="sub">target ≤ 500ms</div></div>
          <div className="card"><h3>Revenue</h3>
            <div className="big">{sit ? `$${(sit.revenue_cents / 100).toFixed(2)}` : '…'}</div>
            <div className="sub">done orders</div></div>
          <div className="card"><h3>Queue</h3>
            <div className="big">{sit ? sit.dependencies.queue_depth : '…'}</div>
            <div className="sub">{sit?.dependencies.queue_provider}</div></div>
        </div>

        <div className="card"><h2>Situation</h2>
          {sit ? <p>{sit.summary}</p> : <p className="sub">collecting…</p>}
          {sit?.checks.map((c) => (
            <div key={c.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
              <span>{c.name} <span className="sub">{c.value}{c.unit ? ` ${c.unit}` : ''}</span></span>
              <Pill v={c.verdict} />
            </div>
          ))}
        </div>

        <div className="card"><h2>Recent orders</h2>
          <table><thead><tr><th>ID</th><th>Item</th><th>Total</th><th>Status</th></tr></thead>
            <tbody>{orders?.items.map((o) => (
              <tr key={o.id}><td>{o.id}</td><td>{o.item} ×{o.qty}</td>
                <td>${((o.total_cents || 0) / 100).toFixed(2)}</td>
                <td><span className={`pill ${o.status}`}>{o.status}</span></td></tr>
            ))}</tbody></table></div>

        <div className="card"><h2>Products</h2>
          <table><thead><tr><th>Name</th><th>Price</th><th>Stock</th></tr></thead>
            <tbody>{products?.items.map((p) => (
              <tr key={p.id}><td>{p.name}</td><td>${(p.price_cents / 100).toFixed(2)}</td>
                <td>{p.stock}{p.low ? ' · LOW' : ''}</td></tr>
            ))}</tbody></table></div>

        <div className="card"><h2>Top operators</h2>
          <table><thead><tr><th>#</th><th>Name</th><th>Score</th></tr></thead>
            <tbody>{scores?.items.map((s, i) => (
              <tr key={i}><td>{i + 1}</td><td>{s.name}</td><td>{s.score}</td></tr>
            ))}</tbody></table></div>
      </main>
    </>
  )
}
