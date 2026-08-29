import { $ } from './dom.js';
import { login, register, sendCode } from './api.js';

export function createAuthModal(onAuthSuccess) {
  const modal = {
    overlay: $('authModal'),
    loginForm: $('loginForm'),
    registerForm: $('registerForm'),
    loginError: $('loginError'),
    registerError: $('registerError'),
    sendCodeBtn: $('sendCodeBtn'),
    codeCooldown: 0,
    open() {
      this.overlay.classList.add('active');
      this.switchTab('login');
    },
    close() {
      this.overlay.classList.remove('active');
    },
    switchTab(tab) {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
      this.loginForm.classList.toggle('active', tab === 'login');
      this.registerForm.classList.toggle('active', tab === 'register');
      this.loginError.textContent = '';
      this.registerError.textContent = '';
    },
    async sendRegisterCode() {
      const email = this.registerForm.email.value.trim();
      if (!email) {
        this.registerError.textContent = '请先输入邮箱';
        return;
      }
      this.sendCodeBtn.disabled = true;
      this.sendCodeBtn.textContent = '发送中...';
      try {
        const data = await sendCode(email);
        this.registerError.textContent = data.message || '验证码已发送，请查收邮件';
        this.registerError.style.color = '#30d158';
        this.codeCooldown = 60;
        this.tickCooldown();
      } catch (err) {
        this.registerError.textContent = err.message;
        this.registerError.style.color = '#a43a2f';
        this.sendCodeBtn.disabled = false;
        this.sendCodeBtn.textContent = '获取验证码';
      }
    },
    tickCooldown() {
      if (this.codeCooldown <= 0) {
        this.sendCodeBtn.disabled = false;
        this.sendCodeBtn.textContent = '获取验证码';
        return;
      }
      this.sendCodeBtn.textContent = `${this.codeCooldown}s`;
      this.codeCooldown--;
      setTimeout(() => this.tickCooldown(), 1000);
    },
  };

  $('authClose').addEventListener('click', () => modal.close());
  $('authSkip').addEventListener('click', () => {
    modal.close();
    onAuthSuccess();
  });
  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => modal.switchTab(tab.dataset.tab));
  });
  modal.sendCodeBtn.addEventListener('click', () => modal.sendRegisterCode());
  modal.loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    modal.loginError.textContent = '';
    try {
      await login(modal.loginForm.email.value.trim(), modal.loginForm.password.value);
      modal.close();
      onAuthSuccess();
    } catch (err) {
      modal.loginError.textContent = err.message;
    }
  });
  modal.registerForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    modal.registerError.textContent = '';
    modal.registerError.style.color = '#a43a2f';
    try {
      await register(
        modal.registerForm.email.value.trim(),
        modal.registerForm.code.value.trim(),
        modal.registerForm.password.value,
      );
      modal.close();
      onAuthSuccess();
    } catch (err) {
      modal.registerError.textContent = err.message;
    }
  });

  return modal;
}
