export const pywebviewReady = new Promise((resolve) => {
  if (window.pywebview) resolve()
  else window.addEventListener('pywebviewready', () => resolve(), { once: true })
})

export async function call(method, ...args) {
  await pywebviewReady
  return window.pywebview.api[method](...args)
}
