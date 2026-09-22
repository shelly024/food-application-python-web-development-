const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("delivery_token"); //? not safe
  let response;
  let data;

  try {
    response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },})
  } catch {
    const error = new Error("Connection lost. Please check your network and try again.")
    error.code = "NETWORK_ERROR"
    throw error
  }

  try {
    data = await response.json(); //解析失败，response不是json格式
  } catch {
    const error = new Error("Unexpected error. Please try again in a moment.")
    error.code = "PARSE_ERROR"
    throw error
  }

  if (!response.ok) {
    const msg = data.error?.message || "Something went wrong"; //safe expression what?
    const code = data.error?.code;
    const error = new Error(msg);
    error.code = code
    throw error
  }
  return data;
}

export const api = {
  login: (payload) => request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  read_user: () => request("/api/auth/users/me"),
  register: (payload) => request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  stores: () => request("/api/stores"),
  store: (id) => request(`/api/stores/${id}`),
  createOrder: (items) => request("/api/orders", { method: "POST", body: JSON.stringify({ items }) }),
  recommendations:(payload) => request("/api/recommendations",{method:"POST", body:JSON.stringify(payload) }),
};
