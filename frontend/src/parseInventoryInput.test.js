import { describe, it, expect } from 'vitest'
import { parseInventoryInput } from './parseInventoryInput.js'

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
