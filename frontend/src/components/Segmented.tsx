export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly T[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="segmented" role="group">
      {options.map((option) => (
        <button key={option} type="button" aria-pressed={option === value} className={option === value ? 'selected' : ''} onClick={() => onChange(option)}>{option}</button>
      ))}
    </div>
  )
}
