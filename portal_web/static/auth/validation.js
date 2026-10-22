import {errorCampo,prepararCampos} from '../validaciones.js';
const authForm=document.querySelector('#auth-form');if(authForm)prepararCampos(authForm);
export function validate(form, page) {
  let firstInvalid = null;
  for (const input of form.querySelectorAll('input:not([type=checkbox])')) {
    let message = errorCampo(input.name==='email'?'correo':input.name,input.value,input.required);
    if (!input.value.trim()) message = 'Completa este campo.';
    else if (!message && input.type === 'email' && input.validity.typeMismatch) message = 'Ingresa un correo electrónico válido.';
    else if (input.minLength > 0 && input.value.length < input.minLength) message = `Usa al menos ${input.minLength} caracteres.`;
    else if (input.maxLength > 0 && input.value.length > input.maxLength) message = `Usa como máximo ${input.maxLength} caracteres.`;
    if (input.name === 'confirm' && input.value !== form.elements.password.value) message = 'Las contraseñas no coinciden.';
    input.setAttribute('aria-invalid', String(Boolean(message)));
    document.getElementById(`${input.id}-error`).textContent = message;
    if (message && !firstInvalid) firstInvalid = input;
  }
  firstInvalid?.focus();
  return !firstInvalid;
}
