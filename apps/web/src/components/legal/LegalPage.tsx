import { ReactNode } from 'react'

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b border-gray-100">
        {title}
      </h2>
      {children}
    </section>
  )
}

export function LegalParagraph({ children }: { children: ReactNode }) {
  return <p className="text-gray-600 leading-relaxed mb-3 text-sm">{children}</p>
}

export function LegalList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc list-inside space-y-1.5 mb-3 text-gray-600 text-sm">
      {items.map((item, i) => (
        <li key={i} className="leading-relaxed pl-1">
          {item}
        </li>
      ))}
    </ul>
  )
}

export function LegalOrderedList({ items }: { items: string[] }) {
  return (
    <ol className="list-decimal list-inside space-y-1.5 mb-3 text-gray-600 text-sm">
      {items.map((item, i) => (
        <li key={i} className="leading-relaxed pl-1">
          {item}
        </li>
      ))}
    </ol>
  )
}

export function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm mb-1.5">
      <span className="font-semibold text-gray-700 min-w-[120px]">{label}:</span>
      <span className="text-gray-600">{value}</span>
    </div>
  )
}

export function LegalNote({ children }: { children: ReactNode }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-4 text-sm text-amber-900 leading-relaxed">
      {children}
    </div>
  )
}

export function LegalSubSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-5">
      <h3 className="text-base font-semibold text-gray-800 mb-2">{title}</h3>
      {children}
    </div>
  )
}

export function RetentionTable({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden mb-4">
      {rows.map((row, i) => (
        <div
          key={i}
          className={`flex text-sm ${i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}`}
        >
          <div className="font-medium text-gray-700 px-4 py-2.5 w-48 shrink-0 border-r border-gray-200">
            {row.label}
          </div>
          <div className="text-gray-600 px-4 py-2.5 flex-1">{row.value}</div>
        </div>
      ))}
    </div>
  )
}
