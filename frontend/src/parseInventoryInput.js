import { normalizeUnit, DEFAULT_UNIT } from './units.js'

const NUMBER = /^(\d+(?:\.\d+)?|\d+\/\d+)$/
const GLUED_UNIT = /^(\d+(?:\.\d+)?)([a-z]+)$/i

function toNumber(token) {
  if (token.includes('/')) {
    const [num, den] = token.split('/').map(Number)
    return den ? num / den : NaN
  }
  return Number(token)
}

// "2 lb chicken breast" -> { quantity: 2, unit: 'lb', name: 'chicken breast', unitRecognized: true }
// "1 1/2 cups rice"      -> { quantity: 1.5, unit: 'cup', name: 'rice', unitRecognized: true }
// "eggs"                 -> { quantity: 1, unit: 'each', name: 'eggs', unitRecognized: true }
// "2 sacks flour"        -> { quantity: 2, unit: 'each', name: 'sacks flour', unitRecognized: false }
export function parseInventoryInput(text) {
  const tokens = text.trim().split(/\s+/).filter(Boolean)
  if (tokens.length === 0) return null

  // "500g" / "2lb" / "1.5kg" -> "500 g" / "2 lb" / "1.5 kg", only when the suffix is a known unit
  const glued = tokens[0].match(GLUED_UNIT)
  if (glued && normalizeUnit(glued[2])) {
    tokens.splice(0, 1, glued[1], glued[2])
  }

  let quantity = 1
  let quantityGiven = false

  if (NUMBER.test(tokens[0])) {
    quantity = toNumber(tokens.shift())
    quantityGiven = true
    if (tokens.length && /^\d+\/\d+$/.test(tokens[0])) {
      quantity += toNumber(tokens.shift())
    }
  }

  let unit = DEFAULT_UNIT
  let unitRecognized = true
  if (quantityGiven && tokens.length) {
    const normalized = normalizeUnit(tokens[0])
    if (normalized) {
      if (tokens.length === 1) return null
      unit = normalized
      tokens.shift()
    } else if (tokens.length > 1) {
      unitRecognized = false
    }
  }

  if (tokens[0]?.toLowerCase() === 'of') tokens.shift()

  const name = tokens.join(' ').trim()
  if (!name || Number.isNaN(quantity) || quantity <= 0) return null

  return { quantity, unit, name, unitRecognized }
}
