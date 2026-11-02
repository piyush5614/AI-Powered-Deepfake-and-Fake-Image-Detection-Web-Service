import metrics from '../data/metrics.json'
import { Card } from '../components/Card'

type ModelMetrics = {
  accuracy?: number
  precision?: { macro?: number }
  recall?: { macro?: number }
  f1?: { macro?: number }
  confusion_matrix?: number[][]
}

const availableMetrics = metrics as { models?: Record<string, ModelMetrics>; note?: string }

export function AboutPage() {
  return (
    <main className="page-shell">
      <div className="page-title-row"><div><p className="eyebrow">ABOUT TRUTHLENS</p><h1>How it works</h1><p className="page-subtitle">A model-assisted signal, presented with its limits in view.</p></div></div>
      <div className="content-grid">
        <Card><h2>Transfer learning</h2><p>TruthLens fine-tunes an ImageNet-pretrained image classifier on labeled real and AI-generated images. It reports the model’s most likely class and its softmax confidence.</p></Card>
        <Card><h2>What the heatmap means</h2><p>Grad-CAM highlights image regions that influenced a model prediction. It is an explanation of the model’s attention, not proof that an image is edited or synthetic.</p></Card>
        <Card className="metrics-card"><h2>Measured performance</h2>
          {availableMetrics.models && Object.keys(availableMetrics.models).length > 0 ? Object.entries(availableMetrics.models).map(([name, model]) => (
            <div className="metrics-block" key={name}><h3>{name.replaceAll('_', ' ')}</h3><div className="metric-list">{[['Accuracy', model.accuracy], ['Precision (macro)', model.precision?.macro], ['Recall (macro)', model.recall?.macro], ['F1 (macro)', model.f1?.macro]].map(([label, value]) => <div key={String(label)}><span>{label}</span><strong>{typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'}</strong></div>)}</div>
              {model.confusion_matrix && <table><caption>Confusion matrix · actual rows, predicted columns</caption><thead><tr><th></th><th>REAL</th><th>FAKE</th></tr></thead><tbody>{model.confusion_matrix.map((row, index) => <tr key={index}><th>{index === 0 ? 'REAL' : 'FAKE'}</th>{row.map((count, cell) => <td key={cell}>{count}</td>)}</tr>)}</tbody></table>}
            </div>
          )) : <p>{availableMetrics.note ?? 'No trained model metrics are available yet. Train and evaluate the model to populate this table.'}</p>}
        </Card>
        <Card><h2>Limitations and responsible use</h2><p>New image generators, heavy compression, and editing can reduce reliability. Training data may not represent every image source. Treat a result as one uncertain signal; do not use it to accuse, harass, or make consequential decisions about a person.</p><p>Uploaded files are processed in memory. The local history database retains only a small thumbnail and result metadata.</p></Card>
      </div>
    </main>
  )
}
