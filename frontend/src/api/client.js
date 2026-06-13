export async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(detailMessage(body) || response.statusText);
  }
  return body;
}

export function detailMessage(body) {
  if (!body) return "";
  if (typeof body === "string") return body;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  if (body.detail?.errors) {
    return body.detail.errors.map((item) => item.message || JSON.stringify(item)).join("; ");
  }
  if (body.error) return String(body.error);
  return JSON.stringify(body);
}

