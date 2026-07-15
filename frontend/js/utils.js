import { BASE_API } from './config.js'

export async function request(path, options = {}) {
  const response = await fetch(`${BASE_API}${path}`, {
    ...options,
    headers: {
      "Content-type": "application/json",
      ...options.headers,
    },
  });

  const hasBody = response.status !== 204;
  const data = hasBody ? await response.json() : null;

  if(!response.ok) {
    const error = new Error(`API request failed: ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
