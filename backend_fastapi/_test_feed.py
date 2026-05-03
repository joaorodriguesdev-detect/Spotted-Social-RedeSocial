const token = localStorage.getItem("access_token"); // ou do AuthContext

const res = await fetch(`${API_BASE}/api/feed/`, {
  method: "POST",
  credentials: "include",
  headers: {
    Authorization: `Bearer ${token}`,   // ← ESSENCIAL
  },
  body: formData,
});