import { afterEach, describe, expect, it, vi } from 'vitest'
import { addInventoryItem, deleteInventoryItem, listInventory, searchRecipe, updateMealPlanEntry } from './api.js'

function respond(status, body, statusText = '') {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: body === undefined ? () => Promise.reject(new SyntaxError('empty')) : () => Promise.resolve(body),
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('request helper', () => {
  it('reads the base URL from VITE_API_URL', async () => {
    vi.stubEnv('VITE_API_URL', 'https://cheffy-api.example.com')
    vi.resetModules()
    const { listInventory: listInventoryHosted } = await import('./api.js')
    const fetchMock = vi.fn().mockResolvedValue(respond(200, []))
    vi.stubGlobal('fetch', fetchMock)

    await listInventoryHosted('roommates')

    expect(fetchMock.mock.calls[0][0]).toBe('https://cheffy-api.example.com/inventory?household_id=roommates')
  })

  it('sends JSON bodies with the right header and parses the response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(201, { id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await addInventoryItem({ householdId: 'roommates', ingredientName: 'eggs', quantity: 12, unit: 'each' })

    expect(result).toEqual({ id: 1 })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/inventory')
    expect(init.method).toBe('POST')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ household_id: 'roommates', ingredient_name: 'eggs', quantity: 12, unit: 'each' })
  })

  it('encodes query parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, []))
    vi.stubGlobal('fetch', fetchMock)

    await listInventory('room mates&co')

    expect(fetchMock.mock.calls[0][0]).toMatch(/\/inventory\?household_id=room\+mates%26co$/)
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined()
  })

  it('resolves 204 to undefined', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(204, undefined)))

    await expect(deleteInventoryItem(3)).resolves.toBeUndefined()
  })

  it("throws the server's detail message on a non-2xx response", async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(502, { detail: 'Recipe service unavailable, try again' }, 'Bad Gateway')))

    await expect(searchRecipe('pad thai')).rejects.toThrow('Recipe service unavailable, try again')
  })

  it('falls back to the status text when the error body is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(500, undefined, 'Internal Server Error')))

    await expect(listInventory('roommates')).rejects.toThrow('Internal Server Error')
  })

  it('falls back to the status code when the status text is empty, as over HTTP/2', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(503, undefined, '')))

    await expect(listInventory('roommates')).rejects.toThrow('Request failed with status 503')
  })

  it('falls back to the status text when detail is not a string', async () => {
    const validationError = { detail: [{ loc: ['body', 'servings'], msg: 'field required' }] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(422, validationError, 'Unprocessable Entity')))

    await expect(searchRecipe('')).rejects.toThrow('Unprocessable Entity')
  })

  it('sends only the given meal plan fields on PATCH, keeping an explicit null', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, { id: 7, day: null }))
    vi.stubGlobal('fetch', fetchMock)

    await updateMealPlanEntry(7, { day: null })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/meal-plan/7')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ day: null })
  })
})
