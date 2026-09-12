import { describe, it, expect } from 'vitest'
import { parseInventoryInput, parseInventoryItems } from './parseInventoryInput.js'

describe('parseInventoryInput', () => {
  it('parses quantity, unit, and multi-word name', () => {
    expect(parseInventoryInput('2 lb chicken breast')).toEqual({
      quantity: 2, unit: 'lb', name: 'chicken breast', unitRecognized: true,
    })
  })

  it('normalizes unit aliases', () => {
    expect(parseInventoryInput('3 lbs ground beef').unit).toBe('lb')
    expect(parseInventoryInput('2 cups rice').unit).toBe('cup')
    expect(parseInventoryInput('4 Tablespoons butter').unit).toBe('tbsp')
  })

  it('defaults to 1 each when only a name is given', () => {
    expect(parseInventoryInput('eggs')).toEqual({
      quantity: 1, unit: 'each', name: 'eggs', unitRecognized: true,
    })
  })

  it('treats a bare number as each', () => {
    expect(parseInventoryInput('12 eggs')).toEqual({
      quantity: 12, unit: 'each', name: 'eggs', unitRecognized: true,
    })
  })

  it('flags unrecognized units and keeps the word in the name', () => {
    expect(parseInventoryInput('2 sacks flour')).toEqual({
      quantity: 2, unit: 'each', name: 'sacks flour', unitRecognized: false,
    })
  })

  it('handles decimals, fractions, and mixed numbers', () => {
    expect(parseInventoryInput('1.5 kg potatoes').quantity).toBe(1.5)
    expect(parseInventoryInput('1/2 cup sugar').quantity).toBe(0.5)
    expect(parseInventoryInput('1 1/2 cups rice')).toMatchObject({ quantity: 1.5, unit: 'cup', name: 'rice' })
  })

  it('splits a number glued to a known unit', () => {
    expect(parseInventoryInput('500g sugar')).toEqual({
      quantity: 500, unit: 'g', name: 'sugar', unitRecognized: true,
    })
    expect(parseInventoryInput('2lb chicken')).toMatchObject({ quantity: 2, unit: 'lb', name: 'chicken' })
    expect(parseInventoryInput('1.5kg potatoes')).toMatchObject({ quantity: 1.5, unit: 'kg' })
    expect(parseInventoryInput('3Cups rice')).toMatchObject({ quantity: 3, unit: 'cup' })
  })

  it('leaves a number glued to a non-unit alone', () => {
    expect(parseInventoryInput('7up')).toEqual({
      quantity: 1, unit: 'each', name: '7up', unitRecognized: true,
    })
  })

  it('drops a leading "of" after the unit', () => {
    expect(parseInventoryInput('2 cups of rice').name).toBe('rice')
  })

  it('returns null for empty, name-less, or zero-quantity input', () => {
    expect(parseInventoryInput('')).toBeNull()
    expect(parseInventoryInput('   ')).toBeNull()
    expect(parseInventoryInput('2 lb')).toBeNull()
    expect(parseInventoryInput('0 lb chicken')).toBeNull()
  })
})

describe('parseInventoryItems', () => {
  it('splits comma separated items and keeps each raw segment', () => {
    const { items, invalid } = parseInventoryItems('2 lb chicken, 12 eggs, cilantro')
    expect(items.map((i) => [i.name, i.quantity, i.unit])).toEqual([
      ['chicken', 2, 'lb'], ['eggs', 12, 'each'], ['cilantro', 1, 'each'],
    ])
    expect(items.map((i) => i.raw)).toEqual(['2 lb chicken', '12 eggs', 'cilantro'])
    expect(invalid).toEqual([])
  })

  it('still handles a single item', () => {
    const { items } = parseInventoryItems('2 lb chicken breast')
    expect(items).toHaveLength(1)
    expect(items[0].name).toBe('chicken breast')
  })

  it('skips empty segments and accepts newlines as separators', () => {
    const { items } = parseInventoryItems('eggs,, \n milk ,')
    expect(items.map((i) => i.name)).toEqual(['eggs', 'milk'])
  })

  it('reports segments it cannot read instead of dropping them', () => {
    const { items, invalid } = parseInventoryItems('2 lb chicken, 3 lb')
    expect(items.map((i) => i.name)).toEqual(['chicken'])
    expect(invalid).toEqual(['3 lb'])
  })

  it('returns nothing for blank input', () => {
    expect(parseInventoryItems('   ')).toEqual({ items: [], invalid: [] })
  })
})
