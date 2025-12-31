import React, { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

// Button
export const Button: React.FC<ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'success' | 'error' }> = ({ variant = 'primary', className = '', ...props }) => (
  <button className={`btn btn-${variant} ${className}`} {...props} />
)

// Card
export const Card: React.FC<{ children: ReactNode; hover?: boolean; className?: string }> = ({ children, className = '', ...props }) => (
  <div className={`card ${className}`} {...props}>{children}</div>
)

// Input
export const Input: React.FC<InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }> = ({ label, error, className = '', ...props }) => (
  <div className="w-full">
    {label && <label className="text-sm font-semibold mb-2 block">{label}</label>}
    <input className={`input ${className}`} {...props} />
    {error && <p className="text-error text-sm mt-1">{error}</p>}
  </div>
)

// Badge
export const Badge: React.FC<{ children: ReactNode; variant?: 'primary' | 'success' | 'error' }> = ({ children, variant = 'primary' }) => (
  <span className={`badge badge-${variant}`}>{children}</span>
)

// Alert
export const Alert: React.FC<{ children: ReactNode; variant?: 'success' | 'error' | 'warning'; title?: string }> = ({ children, variant = 'success', title }) => (
  <div className={`bg-${variant}-50 border-l-4 border-${variant} p-4 rounded`}>
    {title && <p className="font-semibold text-sm">{title}</p>}
    <p className="text-sm mt-1">{children}</p>
  </div>
)

// Modal
export const Modal: React.FC<{ isOpen: boolean; onClose: () => void; title?: string; children: ReactNode }> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null
  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full">
          {title && (
            <div className="border-b p-6 flex justify-between items-center">
              <h2 className="text-2xl font-bold">{title}</h2>
              <button onClick={onClose} className="text-gray-400 text-2xl">×</button>
            </div>
          )}
          <div className="p-6">{children}</div>
        </div>
      </div>
    </>
  )
}

// Spinner
export const Spinner: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizeMap = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className={`animate-spin ${sizeMap[size]} text-primary`}>
      <svg fill="none" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" opacity={0.25} />
        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity={0.75} />
      </svg>
    </div>
  )
}

// Table
export const Table: React.FC<{ columns: { key: string; label: string }[]; data: any[] }> = ({ columns, data }) => (
  <div className="overflow-x-auto">
    <table className="w-full border-collapse">
      <thead className="bg-gray-50">
        <tr>
          {columns.map(col => (
            <th key={col.key} className="px-6 py-3 text-left text-sm font-semibold">{col.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i} className="border-b hover:bg-gray-50">
            {columns.map(col => (
              <td key={col.key} className="px-6 py-4 text-sm">{row[col.key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

// Grid
export const Grid: React.FC<{ cols?: number; gap?: string; children: ReactNode; className?: string }> = ({ cols = 3, gap = '4', children, className = '' }) => (
  <div className={`grid gap-${gap} ${className}`} style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>{children}</div>
)

// Flex
export const Flex: React.FC<{ gap?: string; justify?: 'start' | 'center' | 'end' | 'between'; align?: 'start' | 'center' | 'end'; direction?: 'row' | 'col'; children: ReactNode; className?: string }> = ({ gap = '4', justify = 'start', align = 'center', direction = 'row', children, className = '' }) => (
  <div className={`flex flex-${direction} gap-${gap} justify-${justify} items-${align} ${className}`}>{children}</div>
)
