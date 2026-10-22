import { auth, AuthError } from './auth.service.js';
import { validate } from './validation.js';

const form = document.querySelector('form');
const page = document.body.dataset.page;
const feedback = document.getElementById('feedback');
document.querySelectorAll('.reveal').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.getAttribute('aria-controls'));
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', `${visible ? 'Ocultar' : 'Mostrar'} ${input.name === 'confirm' ? 'confirmación de contraseña' : 'contraseña'}`);
  });
});
form?.addEventListener('submit', async event => {
  event.preventDefault();
  if (form.getAttribute('aria-busy') === 'true' || !validate(form, page)) return;
  const submit = form.querySelector('[type=submit]');
  const label = submit.querySelector('span');
  const original = label.textContent;
  form.setAttribute('aria-busy', 'true'); submit.disabled = true; submit.setAttribute('aria-busy', 'true');
  label.textContent = page === 'login' ? 'Verificando…' : 'Enviando…';
  feedback.textContent = ''; delete feedback.dataset.kind;
  try {
    const data = Object.fromEntries(new FormData(form));
    if (page !== 'recuperar') delete data.confirm;
    data.remember = Boolean(form.elements.remember?.checked);
    const result = await auth[page === 'login' ? 'login' : page === 'registro' ? 'register' : 'recover'](data);
    if (page === 'login') {
      if (result.authenticated !== true) throw new AuthError('El servidor no confirmó la autenticación.');
      // Independently verify the server session before allowing navigation.
      const session = await auth.session();
      if (session.authenticated !== true) throw new AuthError('No se pudo verificar la sesión.');
      const destination = session.redirectUrl || result.redirectUrl || window.CRECE_AUTH.dashboard;
      if (destination) {
        const url = new URL(destination, location.href);
        if (url.origin !== location.origin) throw new AuthError('El destino de acceso no pertenece a este portal.');
        location.assign(url.href);
      } else { feedback.textContent = 'Tu sesión fue verificada correctamente.'; }
    } else {
      if (result.accepted !== true || typeof result.message !== 'string') throw new AuthError('El servidor no confirmó la solicitud.');
      feedback.textContent = result.message;
      form.reset();
    }
  } catch (error) {
    feedback.dataset.kind = 'error'; feedback.textContent = error.message || 'Ocurrió un problema. Intenta nuevamente.';
    feedback.focus();
  } finally {
    // Never persist credentials or sensitive tokens in browser storage.
    form.querySelectorAll('input[type=password], input[autocomplete=current-password], input[autocomplete=new-password]').forEach(input => { input.value = ''; input.type = 'password'; });
    document.querySelectorAll('.reveal').forEach(button => { button.setAttribute('aria-pressed', 'false'); button.setAttribute('aria-label', 'Mostrar contraseña'); });
    form.setAttribute('aria-busy', 'false'); submit.disabled = false; submit.setAttribute('aria-busy', 'false'); label.textContent = original;
  }
});
