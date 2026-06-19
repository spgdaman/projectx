'use client'

const COUNTRY_CODES = [
  { code: '+254', flag: '🇰🇪', name: 'Kenya' },
  { code: '+256', flag: '🇺🇬', name: 'Uganda' },
  { code: '+255', flag: '🇹🇿', name: 'Tanzania' },
  { code: '+250', flag: '🇷🇼', name: 'Rwanda' },
  { code: '+251', flag: '🇪🇹', name: 'Ethiopia' },
  { code: '+234', flag: '🇳🇬', name: 'Nigeria' },
  { code: '+233', flag: '🇬🇭', name: 'Ghana' },
  { code: '+27', flag: '🇿🇦', name: 'South Africa' },
  { code: '+260', flag: '🇿🇲', name: 'Zambia' },
  { code: '+263', flag: '🇿🇼', name: 'Zimbabwe' },
  { code: '+267', flag: '🇧🇼', name: 'Botswana' },
  { code: '+1', flag: '🇺🇸', name: 'USA / Canada' },
  { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+91', flag: '🇮🇳', name: 'India' },
  { code: '+971', flag: '🇦🇪', name: 'UAE' },
]

interface Props {
  countryCode: string
  localNumber: string
  onCountryChange: (code: string) => void
  onLocalChange: (num: string) => void
  required?: boolean
}

export function PhoneInput({ countryCode, localNumber, onCountryChange, onLocalChange, required = true }: Props) {
  return (
    <div className="flex">
      <div className="relative flex-shrink-0">
        <select
          value={countryCode}
          onChange={(e) => onCountryChange(e.target.value)}
          aria-label="Country code"
          className="appearance-none h-full border border-gray-200 border-r-0 rounded-l-lg pl-3 pr-7 text-sm bg-gray-50 text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer"
        >
          {COUNTRY_CODES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.flag} {c.code}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-[10px]">▾</span>
      </div>
      <input
        type="tel"
        required={required}
        value={localNumber}
        onChange={(e) => onLocalChange(e.target.value)}
        placeholder="700000000"
        className="flex-1 min-w-0 border border-gray-200 rounded-r-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  )
}

export function buildFullPhone(countryCode: string, localNumber: string): string {
  const local = localNumber.trim()
  return countryCode + (local.startsWith('0') ? local.slice(1) : local)
}
