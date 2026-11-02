import { Card } from '../components/Card'

export function EthicsPage() {
  return (
    <main className="page-shell">
      <div className="page-title-row"><div><p className="eyebrow">SAFETY & RESPONSIBLE USE</p><h1>Use the signal carefully</h1><p className="page-subtitle">TruthLens is an educational demonstration, not a forensic service.</p></div></div>
      <div className="content-grid">
        <Card><h2>Security measures</h2><ul><li>Image type is validated by decoding its content on the server.</li><li>Uploads are size-limited and analysis requests are rate-limited.</li><li>Images are processed in memory and are not saved as uploads.</li><li>Security response headers and a restricted CORS allowlist are configured.</li></ul></Card>
        <Card><h2>Responsible use</h2><p>A score is not proof of editing or synthetic origin. Do not use it to accuse, shame, or harass someone. Human review and independent corroboration are required before drawing conclusions.</p></Card>
        <Card><h2>Known limitations</h2><p>Unseen generators, compression, cropping, and image editing can affect accuracy. CIFAKE images are low resolution, and face-only data can introduce population and content bias. Always consider the model’s training dataset and evaluation results.</p></Card>
      </div>
    </main>
  )
}
