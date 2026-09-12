import { MEMBERS } from './me.js'
import { startOfWeek, toISODate, todayIndex } from './week.js'

// Where a one-tap "add to this week" lands: today (or Monday when the week being
// planned is not this one) unless `me` already has a meal that day, then the next
// free day later in the week, then today again if every later day is taken.
export function defaultPlanEntry({ entries, weekStart, today = new Date(), me }) {
  const assignedTo = me ?? MEMBERS[0]
  const weekKey = typeof weekStart === 'string' ? weekStart : toISODate(weekStart)
  const start = toISODate(startOfWeek(today)) === weekKey ? todayIndex(today) : 0
  const taken = new Set(
    entries.filter((e) => e.assigned_to === assignedTo && e.day != null).map((e) => e.day),
  )

  let day = start
  for (let d = start; d <= 6; d += 1) {
    if (!taken.has(d)) {
      day = d
      break
    }
  }
  return { day, assignedTo, servings: 1 }
}
