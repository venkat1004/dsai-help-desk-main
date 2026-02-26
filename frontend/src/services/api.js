const BASE_URL = "https://dsai-help-desk-main.onrender.com";
export const apiPost = async (endpoint, body) => {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) throw new Error("API Error");

  return res.json();
};

export const apiGet = async (endpoint) => {
  const res = await fetch(`${BASE_URL}${endpoint}`);

  if (!res.ok) throw new Error("API Error");

  return res.json();
};