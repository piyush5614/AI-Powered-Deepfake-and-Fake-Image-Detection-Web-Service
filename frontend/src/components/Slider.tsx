export function Slider({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="slider-control">
      <span>{label}</span>
      <input type="range" min={0} max={100} value={value} onChange={(event) => onChange(Number(event.target.value))} aria-label={label} />
      <span className="mono">{value}%</span>
    </label>
  )
}
