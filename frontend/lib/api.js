/**
 * Centralized API client and configuration for RAZZZ Frontend.
 * Automatically resolves the backend URL, supporting both standard port 8000 and port 8001.
 */

// Initial default base URL
const DEFAULT_URL = (
  typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : 'http://localhost:8001'
).replace(/\/+$/, '')

export const API_BASE_URL = DEFAULT_URL

/**
 * Returns a fully qualified API URL for a given relative or root path.
 * In the browser, dynamically checks if an alternate local port (e.g. 8001 vs 8000) is saved or active.
 * @param {string} path - e.g. '/auth/login' or 'customers'
 * @returns {string} - e.g. 'http://localhost:8001/auth/login'
 */
export function getApiUrl(path) {
  let base = API_BASE_URL
  if (typeof window !== 'undefined') {
    try {
      const saved = sessionStorage.getItem('razzz_active_api_url') || localStorage.getItem('razzz_active_api_url')
      if (saved) {
        base = saved.replace(/\/+$/, '')
      }
    } catch {}
  }
  if (!path) return base
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${cleanPath}`
}

// In-browser intelligent fallback: if a request to localhost:8000 or localhost:8001 fails with a network error,
// seamlessly retry on the alternate port and remember the working port.
if (typeof window !== 'undefined' && !window.__razzz_fetch_fallback_installed) {
  window.__razzz_fetch_fallback_installed = true
  const originalFetch = window.fetch.bind(window)

  window.fetch = async function (input, init) {
    try {
      return await originalFetch(input, init)
    } catch (err) {
      const url = typeof input === 'string' ? input : (input && input.url ? input.url : '')
      const isLocal8000 = url.includes('localhost:8000') || url.includes('127.0.0.1:8000')
      const isLocal8001 = url.includes('localhost:8001') || url.includes('127.0.0.1:8001')

      if (isLocal8000 || isLocal8001) {
        const targetSearch = isLocal8000 ? /localhost:8000|127\.0\.0\.1:8000/ : /localhost:8001|127\.0\.0\.1:8001/
        const targetReplace = isLocal8000 ? 'localhost:8001' : 'localhost:8000'
        const workingBase = isLocal8000 ? 'http://localhost:8001' : 'http://localhost:8000'
        const altUrl = url.replace(targetSearch, targetReplace)

        try {
          const fallbackInput = typeof input === 'string' ? altUrl : new Request(altUrl, input)
          const res = await originalFetch(fallbackInput, init)
          try {
            sessionStorage.setItem('razzz_active_api_url', workingBase)
            localStorage.setItem('razzz_active_api_url', workingBase)
          } catch {}
          return res
        } catch {
          // If fallback also fails, continue to rethrow original error
        }
      }
      throw err
    }
  }
}

export default getApiUrl
