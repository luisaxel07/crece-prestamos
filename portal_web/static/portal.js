document.addEventListener('DOMContentLoaded', () => {
  const table = document.getElementById('tablaCuotas');
  if (!table) return;
  const rows = [...table.querySelectorAll('tbody tr[data-id]')];
  const loan = document.getElementById('filtroPrestamo');
  const state = document.getElementById('filtroEstado');
  const count = document.getElementById('conteoCuotas');
  const empty = document.getElementById('sinCoincidencias');
  document.getElementById('filtrosCuotas').hidden = rows.length === 0;

  function filter() {
    let visible = 0;
    for (const row of rows) {
      const matchLoan = !loan.value || row.dataset.prestamo === loan.value;
      const matchState = !state.value || (state.value === 'pendientes' ? row.dataset.estado !== 'PAGADA' : row.dataset.estado === state.value);
      row.hidden = !matchLoan || !matchState;
      if (!row.hidden) visible++;
    }
    count.textContent = `${visible} de ${rows.length} cuotas`;
    empty.hidden = rows.length === 0 || visible > 0;
  }
  loan.addEventListener('change', filter);
  state.addEventListener('change', filter);
  document.getElementById('limpiarFiltros').addEventListener('click', () => { loan.value = ''; state.value = ''; filter(); });
  const params = new URLSearchParams(location.search);
  if ([...loan.options].some(option => option.value === params.get('prestamo'))) loan.value = params.get('prestamo');
  const scopedRows = loan.value ? rows.filter(row => row.dataset.prestamo === loan.value) : rows;
  if (scopedRows.some(row => row.dataset.estado !== 'PAGADA')) state.value = 'pendientes';
  const selected = rows.find(row => row.dataset.id === params.get('cuota'));
  if (selected) {
    selected.classList.add('cuota-seleccionada');
    if (selected.dataset.estado === 'PAGADA') state.value = '';
  }
  filter();

  const dialog = document.getElementById('dialogoPago');
  const form = document.getElementById('formularioPago');
  const amount = document.getElementById('monto');
  const submit = form.querySelector('[type=submit]');
  const submitContent = submit.innerHTML;
  const archivo=document.getElementById('comprobante'),vista=document.getElementById('vistaComprobante'),errorArchivo=document.getElementById('errorComprobante');
  let previewUrl;
  function limpiarVista(){if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;vista.removeAttribute('src');vista.hidden=true;archivo.setCustomValidity('');errorArchivo.textContent='';}
  archivo.addEventListener('change',()=>{
    limpiarVista();const foto=archivo.files[0];if(!foto)return;
    let error=foto.size>5*1024*1024?'La imagen no debe superar 5 MB.':!['image/jpeg','image/png','image/webp'].includes(foto.type)?'Selecciona una imagen JPG, PNG o WebP.':'';
    archivo.setCustomValidity(error);errorArchivo.textContent=error;if(error){archivo.reportValidity();return;}
    previewUrl=URL.createObjectURL(foto);vista.src=previewUrl;vista.hidden=false;
  });
  dialog.addEventListener('close',limpiarVista);
  document.querySelectorAll('[data-cuota]').forEach(button => button.addEventListener('click', () => {
    form.reset();limpiarVista();
    document.getElementById('cuotaId').value = button.dataset.cuota;
    amount.value = Number(button.dataset.saldo).toFixed(2);
    amount.max = button.dataset.saldo;
    document.getElementById('saldoDisponible').textContent = `Saldo de esta cuota: C$ ${Number(button.dataset.saldo).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}.`;
    document.getElementById('nombreCuota').textContent = button.dataset.nombre;
    dialog.showModal();
    amount.focus();
  }));
  document.querySelectorAll('[data-cerrar-dialogo]').forEach(button => button.addEventListener('click', () => dialog.close()));
  form.addEventListener('submit', event => {
    if (form.dataset.submitting === 'true') { event.preventDefault(); return; }
    form.dataset.submitting = 'true';
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    submit.textContent = 'Enviando aviso…';
  });
  window.addEventListener('pageshow', () => {
    delete form.dataset.submitting;
    submit.disabled = false;
    submit.removeAttribute('aria-busy');
    submit.innerHTML = submitContent;
  });
});
