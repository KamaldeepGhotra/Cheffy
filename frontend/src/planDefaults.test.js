import { describe, it, expect } from 'vitest'
import { defaultPlanEntry } from './planDefaults.js'

const weekStart = new Date(2026, 8, 7) // Monday Sep 7
const wednesday = new Date(2026, 8, 9)
const entry = (day, assigned_to) => ({ id: day * 10 + 1, day, assigned_to, servings: 1 })

describe('defaultPlanEntry', () => {
  it('lands on today in an empty week, assigned to me, one serving', () => {
    expect(defaultPlanEntry({ entries: [], weekStart, today: wednesday, me: 'Kam' }))
      .toEqual({ day: 2, assignedTo: 'Kam', servings: 1 })
  })

  it('moves to the next free day when I already have a meal today', () => {
    const entries = [entry(2, 'Kam'), entry(3, 'Kam')]
    expect(defaultPlanEntry({ entries, weekStart, today: wednesday, me: 'Kam' }).day).toBe(4)
  })

  it("ignores the other person's meals and planned meals without a day", () => {
    const entries = [entry(2, 'Andreas'), { id: 99, day: null, assigned_to: 'Kam', servings: 1 }]
    expect(defaultPlanEntry({ entries, weekStart, today: wednesday, me: 'Kam' }).day).toBe(2)
  })

  it('falls back to today when every later day is taken', () => {
    const entries = [2, 3, 4, 5, 6].map((d) => entry(d, 'Kam'))
    expect(defaultPlanEntry({ entries, weekStart, today: wednesday, me: 'Kam' }).day).toBe(2)
  })

  it('assigns to the first member when nobody has picked who they are', () => {
    expect(defaultPlanEntry({ entries: [], weekStart, today: wednesday, me: null }).assignedTo).toBe('Andreas')
  })

  it('starts from Monday when the week being planned is not this one', () => {
    const nextWeek = new Date(2026, 8, 14)
    expect(defaultPlanEntry({ entries: [], weekStart: nextWeek, today: wednesday, me: 'Kam' }).day).toBe(0)
  })

  it('accepts the week start as a YYYY-MM-DD string too', () => {
    expect(defaultPlanEntry({ entries: [], weekStart: '2026-09-07', today: wednesday, me: 'Kam' }).day).toBe(2)
  })
})
