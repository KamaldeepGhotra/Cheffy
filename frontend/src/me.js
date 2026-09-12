export const MEMBERS = ['Andreas', 'Kam']

const KEY = 'cheffy.me'

// 'Andreas' | 'Kam' | null. Anything else in storage is treated as not chosen.
export function getMe() {
  try {
    const value = localStorage.getItem(KEY)
    return MEMBERS.includes(value) ? value : null
  } catch {
    return null
  }
}

export function setMe(name) {
  try {
    localStorage.setItem(KEY, name)
  } catch {}
}
