async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    // FastAPI 422 errors are a list of {loc, msg}; turn them into readable text
    const message = Array.isArray(detail)
      ? detail.map((d) => `${d.loc?.[d.loc.length - 1] ?? "field"}: ${d.msg}`).join("; ")
      : typeof detail === "string" ? detail : "Request failed";
    throw new Error(message);
  }
  return data;
}

export const api = {
  createOrder: (body) => request("/orders", { method: "POST", body: JSON.stringify(body) }),
  getOrder: (id) => request(`/orders/${id}`),
  outForDelivery: (id) => request(`/orders/${id}/out-for-delivery`, { method: "POST" }),
  getProofUrl: (id) => request(`/orders/${id}/proof-url`),
  uploadProof: (id, file) => {
    const body = new FormData();
    body.append("file", file);
    return request(`/orders/${id}/proof`, { method: "POST", body });
  },
  getAgents: () => request("/agents"),
  updateAgentStatus: (id, status) => request(`/agents/${id}/status`, { method: "POST", body: JSON.stringify({ status }) }),
  getAgentOrders: (id) => request(`/agents/${id}/orders`),
  getAnalytics: () => request("/analytics"),
};
