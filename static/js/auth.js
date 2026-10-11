
// Accessible, distinctive show/hide password controls on login and register pages.
document.querySelectorAll('.password-toggle[data-password-target]').forEach((toggle) => {
  toggle.addEventListener('click', () => {
    const input = document.getElementById(toggle.dataset.passwordTarget);
    if (!input) return;
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(reveal));
    toggle.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
    const label = toggle.querySelector('.toggle-label');
    const icon = toggle.querySelector('.toggle-icon');
    if (label) label.textContent = reveal ? 'Hide' : 'Show';
    if (icon) icon.textContent = reveal ? '◉' : '◎';
  });
});

async function post(url, data) {
  const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
  return [r.ok, await r.json()];
}

const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const [ok, d] = await post('/api/login', {email, password});
    document.getElementById('message').textContent = d.message || '';
    if (ok) location.href = d.role === 'admin' ? '/admin' : '/';
  });
}

const registerForm = document.getElementById('registerForm');
if (registerForm) {
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const phone = document.getElementById('phone').value.replace(/\s/g, '');
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const msg = document.getElementById('message');
    if (!/^[6-9]\d{9}$/.test(phone)) { msg.textContent = 'Enter a valid 10-digit Indian mobile number'; return; }
    if (!/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/\d/.test(password) || password.length < 8) { msg.textContent = 'Password needs 8+ characters, uppercase, lowercase and number'; return; }
    if (password !== confirmPassword) { msg.textContent = 'Passwords do not match'; return; }
    const [ok, d] = await post('/api/register', {name, phone, email, password});
    msg.textContent = d.message || '';
    if (ok) location.href = '/';
  });
}


const forgotForm = document.getElementById('forgotForm');
const resetConfirmForm = document.getElementById('resetConfirmForm');
if (resetConfirmForm) resetConfirmForm.classList.add('hidden');
if (forgotForm) forgotForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('message');
  const email = document.getElementById('resetEmail').value.trim();
  msg.textContent = 'Sending secure OTP…';
  const [ok, data] = await post('/api/forgot-password/request', {email});
  msg.textContent = data.message || 'Could not send OTP.';
  if (ok) resetConfirmForm.classList.remove('hidden');
});
if (resetConfirmForm) resetConfirmForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('message');
  const email = document.getElementById('resetEmail').value.trim();
  const otp = document.getElementById('resetOtp').value.trim();
  const password = document.getElementById('newPassword').value;
  const confirm = document.getElementById('confirmNewPassword').value;
  if (!/^[0-9]{6}$/.test(otp)) { msg.textContent = 'Enter the 6-digit OTP.'; return; }
  if (!/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/\d/.test(password) || password.length < 8) { msg.textContent = 'Use 8+ characters with uppercase, lowercase and a number.'; return; }
  if (password !== confirm) { msg.textContent = 'Passwords do not match.'; return; }
  const [ok, data] = await post('/api/forgot-password/reset', {email, otp, password});
  msg.textContent = data.message || '';
  if (ok) setTimeout(() => location.href = '/login', 1300);
});
