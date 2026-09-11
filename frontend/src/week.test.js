import { describe, it, expect } from 'vitest'
import { DAY_NAMES, dayOfWeek, shiftWeeks, startOfWeek, toISODate, todayIndex } from './week.js'

describe('week helpers', () => {
  it('finds the Monday of a mid-week date', () => {
    expect(toISODate(startOfWeek(new Date(2026, 8, 10)))).toBe('2026-09-07')
  })

  it('treats Monday as its own week start', () => {
    expect(toISODate(startOfWeek(new Date(2026, 8, 7)))).toBe('2026-09-07')
  })

  it('puts Sunday at the end of the previous Monday-start week', () => {
    expect(toISODate(startOfWeek(new Date(2026, 8, 13)))).toBe('2026-09-07')
  })

  it('strips the time of day', () => {
    const start = startOfWeek(new Date(2026, 8, 10, 23, 59))
    expect(start.getHours()).toBe(0)
  })

  it('shifts whole weeks across a month boundary', () => {
    const start = startOfWeek(new Date(2026, 8, 28))
    expect(toISODate(shiftWeeks(start, 1))).toBe('2026-10-05')
    expect(toISODate(shiftWeeks(start, -1))).toBe('2026-09-21')
  })

  it('resolves a day index within the week', () => {
    const start = startOfWeek(new Date(2026, 8, 7))
    expect(toISODate(dayOfWeek(start, 6))).toBe('2026-09-13')
  })
})

describe('todayIndex', () => {
  it('maps Monday to 0', () => {
    expect(todayIndex(new Date(2026, 8, 7))).toBe(0)
  })

  it('maps Sunday to 6, not 0 like Date.getDay()', () => {
    expect(todayIndex(new Date(2026, 8, 13))).toBe(6)
  })

  it('maps a mid-week day', () => {
    expect(todayIndex(new Date(2026, 8, 10))).toBe(3)
  })

  it('ignores the time of day', () => {
    expect(todayIndex(new Date(2026, 8, 13, 23, 59, 59))).toBe(6)
  })

  it('lines up with DAY_NAMES', () => {
    expect(DAY_NAMES[todayIndex(new Date(2026, 8, 11))]).toBe('Fri')
  })

  it('defaults to now', () => {
    expect(todayIndex()).toBe(todayIndex(new Date()))
  })
})
