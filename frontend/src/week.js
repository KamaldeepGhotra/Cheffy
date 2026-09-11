export const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// Index of `date` within a Monday-start week: 0 = Monday ... 6 = Sunday, local time.
export function todayIndex(date = new Date()) {
  return (date.getDay() + 6) % 7
}

// Monday of the week containing `date`, as a local-time Date at midnight.
export function startOfWeek(date) {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  d.setDate(d.getDate() - todayIndex(d))
  return d
}

export function shiftWeeks(weekStart, count) {
  const d = new Date(weekStart)
  d.setDate(d.getDate() + count * 7)
  return d
}

export function dayOfWeek(weekStart, dayIndex) {
  const d = new Date(weekStart)
  d.setDate(d.getDate() + dayIndex)
  return d
}

// YYYY-MM-DD in local time, which is what the API expects for week_start.
export function toISODate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function formatDay(date) {
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
