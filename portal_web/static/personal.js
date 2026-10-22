import {prepararCampos,validarCampos} from './validaciones.js';
// Evita dobles pulsaciones mientras el servidor procesa una operación.
document.querySelectorAll('form[data-guardado]').forEach(form => {
  prepararCampos(form);
  form.addEventListener('submit', event => {
    if(!validarCampos(form) || !form.reportValidity()){event.preventDefault();return;}
    if (form.dataset.enviando === '1') { event.preventDefault(); return; }
    form.dataset.enviando = '1';
    form.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = true; });
    const status = form.querySelector('[role="status"]');
    if (status) status.textContent = 'Procesando…';
  });
});
window.addEventListener('pageshow', () => document.querySelectorAll('form[data-guardado]').forEach(form => {
  delete form.dataset.enviando;
  form.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = false; });
  const status = form.querySelector('[role="status"]'); if (status) status.textContent = '';
}));
