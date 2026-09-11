const UNIT_ALIASES = {
  lb: ['lb', 'lbs', 'pound', 'pounds'],
  oz: ['oz', 'ounce', 'ounces'],
  g: ['g', 'gram', 'grams'],
  kg: ['kg', 'kilo', 'kilos', 'kilogram', 'kilograms'],
  cup: ['cup', 'cups'],
  tbsp: ['tbsp', 'tbsps', 'tablespoon', 'tablespoons'],
  tsp: ['tsp', 'tsps', 'teaspoon', 'teaspoons'],
  ml: ['ml', 'milliliter', 'milliliters', 'millilitre', 'millilitres'],
  l: ['l', 'liter', 'liters', 'litre', 'litres'],
  each: ['each', 'ea', 'whole'],
  clove: ['clove', 'cloves'],
  can: ['can', 'cans'],
  bag: ['bag', 'bags'],
  box: ['box', 'boxes'],
  bunch: ['bunch', 'bunches'],
  pack: ['pack', 'packs', 'package', 'packages'],
  slice: ['slice', 'slices'],
  piece: ['piece', 'pieces', 'pc', 'pcs'],
}

const ALIAS_TO_UNIT = Object.fromEntries(
  Object.entries(UNIT_ALIASES).flatMap(([unit, aliases]) => aliases.map((a) => [a, unit])),
)

export const UNITS = Object.keys(UNIT_ALIASES)
export const DEFAULT_UNIT = 'each'

export function normalizeUnit(token) {
  if (!token) return null
  return ALIAS_TO_UNIT[token.toLowerCase().replace(/\.$/, '')] ?? null
}
