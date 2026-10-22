// Los límites, patrones y ejemplos se leen del mismo archivo usado por Python y Qt.
const response = await fetch(new URL('./reglas-formularios.json', import.meta.url));
if (!response.ok) throw new Error('No se pudieron cargar las reglas de los formularios.');
const reglas = JSON.parse((await response.text()).replace(/^\uFEFF/, ''));
const letras = /^[\p{L} ]*$/u;
const correo = /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$/;
const esNumero = key=>['monto','tasa','meses'].includes(key);
const esNombre = key => ['nombres','apellidos','name','cargo'].includes(key);
export function formatearCedula(value) {
  const raw = value.replaceAll('-','').toUpperCase();
  return raw.slice(0,3)+(raw.length>=3?'-':'')+raw.slice(3,9)+(raw.length>=9?'-':'')+raw.slice(9);
}
export function errorCampo(key,value,requerido=true) {
  const rule = reglas[key]; if (!rule) return '';
  value=value.normalize('NFC');value=esNombre(key)?value.replace(/^ +| +$/g,''):value.trim();
  if (!value) return requerido?'Completa este campo.':'';
  if (value.length>rule.maxlength) return `Usa como máximo ${rule.maxlength} caracteres.`;
  if (esNombre(key) && (!letras.test(value) || !/\p{L}/u.test(value))) return 'Usa solo letras y espacios; se permiten tildes y ñ.';
  if(key==='cedula') {
    if(!/^[0-9]{3}-[0-9]{6}-[0-9]{4}[A-Z]$/.test(value)) return 'Completa la cédula: 000-DDMMAA-0000A.';
    const raw=value.replaceAll('-',''),d=Number(raw.slice(3,5)),m=Number(raw.slice(5,7)),y=2000+Number(raw.slice(7,9));
    const date=new Date(Date.UTC(y,m-1,d));
    if(date.getUTCFullYear()!==y || date.getUTCMonth()!==m-1 || date.getUTCDate()!==d) return 'Los seis dígitos centrales deben ser una fecha de nacimiento válida (DDMMAA).';
  }
  if(esNumero(key) && (!new RegExp('^(?:'+rule.pattern+')$').test(value) || Number(value)<(key==='monto'||key==='meses'?1e-2:0) || key==='meses'&&Number(value)>600))return rule.ayuda;
  if(key==='telefono' && !/^[0-9]{8,15}$/.test(value)) return reglas.telefono.ayuda;
  if(key==='correo' && (!correo.test(value) || value.includes('..') || value.startsWith('.') || value.includes('.@'))) return 'Ingresa un correo válido, por ejemplo nombre@correo.com.';
  return '';
}
export function prepararCampos(form) {
  for (const input of form.querySelectorAll('input,textarea')) {
    const key=input.name==='email'?'correo':input.name;
    const rule=reglas[key]; if(!rule) continue;
    input.placeholder=rule.placeholder;input.maxLength=rule.maxlength;
    if(rule.pattern) input.pattern=rule.pattern;
    if(esNumero(key))input.addEventListener('keydown',event=>{if(!event.ctrlKey&&!event.metaKey&&event.key.length===1&&!/[0-9.]/.test(event.key))event.preventDefault();});
    const error=document.getElementById(`${input.id}-error`);
    let previo=input.value;
    function mensaje(texto) {
      input.setAttribute('aria-invalid',String(Boolean(texto)));
      input.setCustomValidity(texto);
      if(error)error.textContent=texto;
    }
    function permitido(value) {
      if(esNombre(key))return letras.test(value.normalize('NFC'));
      if(esNumero(key))return key==='meses'?/^[0-9]*$/.test(value):/^[0-9]*(?:\.[0-9]*)?$/.test(value);
      if(key==='telefono')return /^[0-9]*$/.test(value);
      if(key==='cedula')return /^[0-9-]*$/.test(value) && value.replaceAll('-','').length<=13 || /^[0-9]{13}[A-Za-z]$/.test(value.replaceAll('-',''));
      return true;
    }
    // Rechaza una inserción completa inválida, incluso al pegar; no cambia un nombre
    // con números por otro nombre diferente eliminando los números silenciosamente.
    input.addEventListener('beforeinput',event=>{
      if(key==='cedula' && input.selectionStart===input.selectionEnd){
        const pos=input.selectionStart;
        if(event.inputType==='deleteContentBackward' && input.value[pos-1]==='-')input.setSelectionRange(Math.max(0,pos-2),pos);
        if(event.inputType==='deleteContentForward' && input.value[pos]==='-')input.setSelectionRange(pos,pos+2);
      }
      if(event.isComposing || event.inputType.startsWith('delete') || event.data==null)return;
      if(esNumero(key)){if(!/^[0-9.]+$/.test(event.data)||key==='meses'&&event.data.includes('.')){event.preventDefault();mensaje(rule.ayuda);}return;}
      const candidate=input.value.slice(0,input.selectionStart)+event.data+input.value.slice(input.selectionEnd);
      if(!permitido(candidate)){event.preventDefault();mensaje(rule.ayuda);}
    });
    input.addEventListener('input',event=>{
      if(event.isComposing)return;
      if(!permitido(input.value)){input.value=previo;mensaje(rule.ayuda);return;}
      if(key==='cedula') {
        const logical=input.value.slice(0,input.selectionStart).replaceAll('-','').length;
        input.value=formatearCedula(input.value);
        const cursor=logical+(logical>=3?1:0)+(logical>=9?1:0);
        input.setSelectionRange(cursor,cursor);
      } else if(esNombre(key))input.value=input.value.normalize('NFC');
      previo=input.value;mensaje('');
    });
    input.addEventListener('blur',()=>{
      if(esNombre(key))input.value=input.value.normalize('NFC').replace(/^ +| +$/g,'').replace(/ +/g,' ');
      if(key==='cedula' && permitido(input.value))input.value=formatearCedula(input.value);
      mensaje(errorCampo(key,input.value,input.required));previo=input.value;
    });
    input.addEventListener('invalid',()=>mensaje(errorCampo(key,input.value,input.required)||input.validationMessage));
  }
}
export function validarCampos(form) {
  let first=null;
  for (const input of form.querySelectorAll('input,textarea,select')) {
    const key=input.name==='email'?'correo':input.name;
    const message=errorCampo(key,input.value,input.required);
    input.setCustomValidity(message);
    if(message){input.setAttribute('aria-invalid','true');const node=document.getElementById(`${input.id}-error`);if(node)node.textContent=message;first ||= input;}
  }
  first?.focus();return !first;
}
