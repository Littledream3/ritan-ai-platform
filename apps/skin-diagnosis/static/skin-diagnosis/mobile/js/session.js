const TOKEN_KEY = 'lanjiao_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function isLoggedIn() {
  return Boolean(getToken());
}
