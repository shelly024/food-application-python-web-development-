const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("delivery_token");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {    //login need Authorization header?
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}), //auth flow need to review,token is nessiry?
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({})); //how to catch the error and present on frontend in the readable way?
  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong");
  }
  return data;
}

export const api = {
  login: (payload) => request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  register: (payload) => request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  stores: () => request("/api/stores"),
  store: (id) => request(`/api/stores/${id}`),
  createOrder: (items) => request("/api/orders", { method: "POST", body: JSON.stringify({ items }) }),
  recommendations:(payload) => request("/api/recommendations",{method:"POST", body:JSON.stringify(payload) }),
};
