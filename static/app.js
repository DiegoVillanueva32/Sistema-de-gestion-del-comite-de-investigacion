/* ==========================================================================
   Comité I+D — Interactividad del cliente (JavaScript puro, sin librerías)

   Cada módulo se activa solo si encuentra en la página los elementos que usa,
   así un único archivo sirve para todas las plantillas.

    1. Menú móvil                 7. Contador de caracteres
    2. Alertas (cerrar / ocultar) 8. Filtro instantáneo y orden de tablas
    3. Modal de confirmación      9. Buscador global (Fetch API)
    4. Validación en el cliente  10. Notificaciones en vivo (Fetch API)
    5. Mostrar / ocultar clave   11. Animaciones de KPIs y barras
    6. Requisitos según el tipo  12. Aviso de cambios sin guardar
   ========================================================================== */
(function () {
  "use strict";

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const normalizar = (t) => (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const escapar = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* 1. Menú móvil ---------------------------------------------------------- */
  const botonMenu = $("[data-menu-toggle]");
  if (botonMenu) {
    botonMenu.addEventListener("click", () => {
      const abierto = document.body.classList.toggle("nav-open");
      botonMenu.setAttribute("aria-expanded", String(abierto));
    });
  }

  /* 2. Alertas: botón cerrar y las de éxito se ocultan solas --------------- */
  $$(".alert").forEach((alerta) => {
    const cerrar = document.createElement("button");
    cerrar.type = "button";
    cerrar.className = "alert-close";
    cerrar.setAttribute("aria-label", "Cerrar mensaje");
    cerrar.textContent = "×";
    cerrar.addEventListener("click", () => ocultar(alerta));
    alerta.appendChild(cerrar);
    if (alerta.classList.contains("alert-success")) setTimeout(() => ocultar(alerta), 6000);
  });
  function ocultar(el) {
    el.classList.add("is-leaving");
    setTimeout(() => el.remove(), 250);
  }

  /* 3. Modal de confirmación para acciones destructivas -------------------- */
  const modal = $("#confirm-modal");
  let formularioPendiente = null;
  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (form.dataset.confirmado === "1" || !modal) return;
      e.preventDefault();
      formularioPendiente = form;
      $("[data-confirm-text]", modal).textContent = form.dataset.confirm;
      modal.showModal();
      $("[data-confirm-ok]", modal).focus();
    });
  });
  if (modal) {
    $("[data-confirm-ok]", modal).addEventListener("click", () => {
      modal.close();
      if (formularioPendiente) {
        formularioPendiente.dataset.confirmado = "1";
        formularioPendiente.requestSubmit();
      }
    });
    $("[data-confirm-cancel]", modal).addEventListener("click", () => modal.close());
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.close(); });
  }

  /* 4. Validación en el cliente ---------------------------------------------
     Usa las reglas de HTML5 (required, type, minlength, pattern) con mensajes
     propios en español, más reglas extra declaradas con atributos data-*:
       data-match="id"        debe coincidir con otro campo (confirmar clave)
       data-min-date="today"  la fecha no puede ser anterior a hoy
       data-max-mb / data-ext tamaño y extensión del archivo a cargar        */
  function mensajeError(campo) {
    const v = campo.validity;
    const valor = campo.value.trim();
    if (campo.required && !valor) return "Este campo es obligatorio.";
    if (!valor && campo.type !== "file") return "";
    if (v.typeMismatch && campo.type === "email") return "Escriba un correo válido, por ejemplo nombre@universidad.edu.co.";
    if (v.tooShort || (campo.minLength > 0 && valor.length < campo.minLength)) return `Debe tener al menos ${campo.minLength} caracteres.`;
    if (v.patternMismatch) return campo.dataset.msg || "El formato no es válido.";
    if (campo.dataset.match) {
      const otro = document.getElementById(campo.dataset.match);
      if (otro && otro.value !== campo.value) return "Las contraseñas no coinciden.";
    }
    if (campo.dataset.minDate === "today" && campo.value) {
      const hoy = new Date().toISOString().slice(0, 10);
      if (campo.value < hoy) return "La fecha no puede ser anterior a hoy.";
    }
    if (campo.type === "file" && campo.files.length) {
      const archivo = campo.files[0];
      const maxMb = Number(campo.dataset.maxMb || 0);
      if (maxMb && archivo.size > maxMb * 1024 * 1024) return `El archivo pesa ${(archivo.size / 1048576).toFixed(1)} MB; el máximo es ${maxMb} MB.`;
      const permitidas = (campo.dataset.ext || "").split(",").filter(Boolean);
      const ext = archivo.name.split(".").pop().toLowerCase();
      if (permitidas.length && !permitidas.includes(ext)) return `Formato .${ext} no permitido. Use: ${permitidas.join(", ")}.`;
    }
    if (!v.valid) return campo.validationMessage;
    return "";
  }

  function pintarError(campo, mensaje) {
    const ancla = campo.closest(".pw-wrap") || campo;
    let nodo = ancla.nextElementSibling && ancla.nextElementSibling.classList.contains("field-error") ? ancla.nextElementSibling : null;
    if (mensaje) {
      if (!nodo) {
        nodo = document.createElement("small");
        nodo.className = "field-error";
        nodo.id = `error-${campo.name || "campo"}-${Math.random().toString(36).slice(2, 7)}`;
        nodo.setAttribute("role", "alert");
        ancla.insertAdjacentElement("afterend", nodo);
        campo.setAttribute("aria-describedby", nodo.id);
      }
      nodo.textContent = mensaje;
      campo.classList.add("invalid");
      campo.setAttribute("aria-invalid", "true");
    } else {
      if (nodo) nodo.remove();
      campo.classList.remove("invalid");
      campo.removeAttribute("aria-invalid");
    }
    return !mensaje;
  }

  $$("form").forEach((form) => {
    if (form.method.toLowerCase() !== "post") return;
    const campos = $$("input:not([type=hidden]):not([type=checkbox]), select, textarea", form);
    if (!campos.length) return;
    form.noValidate = true; // reemplazamos las burbujas del navegador por mensajes propios
    campos.forEach((campo) => {
      campo.addEventListener("blur", () => pintarError(campo, mensajeError(campo)));
      campo.addEventListener("input", () => { if (campo.classList.contains("invalid")) pintarError(campo, mensajeError(campo)); });
      campo.addEventListener("change", () => pintarError(campo, mensajeError(campo)));
    });
    form.addEventListener("submit", (e) => {
      const invalidos = campos.filter((c) => !pintarError(c, mensajeError(c)));
      if (invalidos.length) {
        e.preventDefault();
        e.stopImmediatePropagation();
        invalidos[0].focus();
        return;
      }
      const boton = e.submitter || $("button[type=submit]", form);
      if (boton && !form.dataset.confirm) {
        boton.classList.add("is-loading");
        setTimeout(() => { boton.disabled = true; }, 0); // evita envíos dobles
      }
    }, true);
  });

  /* 5. Mostrar / ocultar contraseña ---------------------------------------- */
  $$("input[type=password]").forEach((campo) => {
    const envoltura = document.createElement("div");
    envoltura.className = "pw-wrap";
    campo.parentNode.insertBefore(envoltura, campo);
    envoltura.appendChild(campo);
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "pw-toggle";
    boton.textContent = "Ver";
    boton.setAttribute("aria-label", "Mostrar contraseña");
    boton.addEventListener("click", () => {
      const visible = campo.type === "text";
      campo.type = visible ? "password" : "text";
      boton.textContent = visible ? "Ver" : "Ocultar";
      boton.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
    });
    envoltura.appendChild(boton);
  });

  /* 6. Requisitos del tipo de solicitud elegido ---------------------------- */
  const selectorTipo = $("[data-req-select]");
  if (selectorTipo) {
    const mostrar = () => $$(".req-box").forEach((caja) => { caja.hidden = caja.dataset.tipo !== selectorTipo.value; });
    selectorTipo.addEventListener("change", mostrar);
    mostrar();
  }

  /* 7. Contador de caracteres ---------------------------------------------- */
  $$("[data-counter][maxlength]").forEach((campo) => {
    const contador = document.createElement("small");
    contador.className = "counter";
    campo.insertAdjacentElement("afterend", contador);
    const actualizar = () => {
      const max = Number(campo.maxLength);
      contador.textContent = `${campo.value.length} / ${max}`;
      contador.classList.toggle("near", campo.value.length > max * 0.9);
    };
    campo.addEventListener("input", actualizar);
    actualizar();
  });

  /* 8. Filtro instantáneo y orden de columnas en tablas -------------------- */
  $$("[data-filter-table]").forEach((entrada) => {
    const tabla = document.getElementById(entrada.dataset.filterTable);
    if (!tabla) return;
    const filas = $$("tbody tr", tabla);
    const salida = entrada.parentElement.querySelector("[data-filter-count]");
    const vacio = document.createElement("p");
    vacio.className = "text-muted m-0 px-4 py-3.5";
    vacio.textContent = "Ninguna fila coincide con el filtro.";
    vacio.hidden = true;
    tabla.insertAdjacentElement("afterend", vacio);
    const filtrar = () => {
      const texto = normalizar(entrada.value.trim());
      let visibles = 0;
      filas.forEach((fila) => {
        const coincide = !texto || normalizar(fila.textContent).includes(texto);
        fila.hidden = !coincide;
        if (coincide) visibles += 1;
      });
      vacio.hidden = visibles > 0;
      if (salida) salida.textContent = texto ? `${visibles} de ${filas.length}` : `${filas.length} registros`;
    };
    entrada.addEventListener("input", filtrar);
    entrada.addEventListener("keydown", (e) => { if (e.key === "Escape") { entrada.value = ""; filtrar(); } });
    filtrar();
  });

  $$("table[data-sortable]").forEach((tabla) => {
    $$("thead th", tabla).forEach((th, columna) => {
      if (th.dataset.nosort !== undefined) return;
      th.classList.add("sortable");
      th.tabIndex = 0;
      th.setAttribute("aria-sort", "none");
      const ordenar = () => {
        const asc = th.getAttribute("aria-sort") !== "ascending";
        $$("thead th", tabla).forEach((o) => o.setAttribute("aria-sort", "none"));
        th.setAttribute("aria-sort", asc ? "ascending" : "descending");
        const cuerpo = $("tbody", tabla);
        const filas = $$("tr", cuerpo);
        const valor = (fila) => (fila.children[columna] ? fila.children[columna].textContent.trim() : "");
        filas.sort((a, b) => {
          const x = valor(a), y = valor(b);
          const nx = parseFloat(x), ny = parseFloat(y);
          const r = !isNaN(nx) && !isNaN(ny) && /^[\d.]+$/.test(x) && /^[\d.]+$/.test(y)
            ? nx - ny
            : x.localeCompare(y, "es", { numeric: true, sensitivity: "base" });
          return asc ? r : -r;
        });
        filas.forEach((f) => cuerpo.appendChild(f));
      };
      th.addEventListener("click", ordenar);
      th.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ordenar(); } });
    });
  });

  /* 9. Buscador global con Fetch API --------------------------------------- */
  const buscador = $("[data-global-search]");
  if (buscador) {
    const lista = $("[data-search-results]");
    let temporizador = null;
    let controlador = null;
    let activo = -1;

    const cerrarLista = () => { lista.hidden = true; activo = -1; buscador.setAttribute("aria-expanded", "false"); };
    const marcar = (i) => {
      const items = $$("a", lista);
      if (!items.length) return;
      activo = (i + items.length) % items.length;
      items.forEach((a, j) => a.classList.toggle("is-active", j === activo));
      items[activo].scrollIntoView({ block: "nearest" });
    };

    async function buscar(texto) {
      if (controlador) controlador.abort(); // cancela la búsqueda anterior si el usuario sigue escribiendo
      controlador = new AbortController();
      lista.hidden = false;
      lista.innerHTML = '<p class="search-msg">Buscando…</p>';
      try {
        const resp = await fetch(`/api/buscar?q=${encodeURIComponent(texto)}`, { signal: controlador.signal, headers: { Accept: "application/json" } });
        if (!resp.ok) throw new Error(resp.status);
        const { resultados } = await resp.json();
        if (!resultados.length) {
          lista.innerHTML = `<p class="search-msg">Sin resultados para «${escapar(texto)}».</p>`;
          return;
        }
        lista.innerHTML = resultados.map((r) => `
          <a href="${r.url}" role="option">
            <span class="code">${escapar(r.codigo)}</span>
            <span class="search-title">${escapar(r.titulo)}</span>
            <span class="status ${r.clase}">${escapar(r.estado)}</span>
          </a>`).join("");
        buscador.setAttribute("aria-expanded", "true");
        activo = -1;
      } catch (err) {
        if (err.name !== "AbortError") lista.innerHTML = '<p class="search-msg">No se pudo buscar. Revise la conexión.</p>';
      }
    }

    buscador.addEventListener("input", () => {
      clearTimeout(temporizador);
      const texto = buscador.value.trim();
      if (texto.length < 2) { cerrarLista(); return; }
      temporizador = setTimeout(() => buscar(texto), 250); // debounce: espera a que deje de escribir
    });
    buscador.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); marcar(activo + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); marcar(activo - 1); }
      else if (e.key === "Enter") {
        const items = $$("a", lista);
        const destino = items[activo] || items[0];
        if (destino) { e.preventDefault(); window.location.href = destino.href; }
      } else if (e.key === "Escape") { cerrarLista(); buscador.blur(); }
    });
    document.addEventListener("click", (e) => { if (!e.target.closest(".global-search")) cerrarLista(); });
    // Atajo de teclado: "/" o Ctrl+K enfoca el buscador desde cualquier página.
    document.addEventListener("keydown", (e) => {
      const escribiendo = /input|textarea|select/i.test(document.activeElement.tagName);
      if ((e.key === "/" && !escribiendo) || (e.key.toLowerCase() === "k" && (e.ctrlKey || e.metaKey))) {
        e.preventDefault();
        if (document.body.classList.contains("nav-open") === false && window.innerWidth <= 900) document.body.classList.add("nav-open");
        buscador.focus();
      }
    });
  }

  /* 10. Notificaciones en vivo con Fetch API -------------------------------- */
  const campana = $("[data-bell]");
  if (campana) {
    const panel = $("[data-notif-panel]");
    const listaNotif = $("[data-notif-list]");

    function pintarContador(n) {
      let globo = $(".badge", campana);
      if (n > 0) {
        if (!globo) { globo = document.createElement("span"); globo.className = "badge"; campana.appendChild(globo); }
        if (globo.textContent !== String(n)) { globo.textContent = n; globo.classList.remove("pop"); void globo.offsetWidth; globo.classList.add("pop"); }
      } else if (globo) {
        globo.remove();
      }
      document.title = document.title.replace(/^\(\d+\) /, "") ;
      if (n > 0) document.title = `(${n}) ${document.title}`;
    }

    async function actualizar() {
      try {
        const resp = await fetch("/api/notificaciones", { headers: { Accept: "application/json" } });
        if (!resp.ok) return;
        const datos = await resp.json();
        pintarContador(datos.pendientes);
        listaNotif.innerHTML = datos.ultimas.length
          ? datos.ultimas.map((n) => `<a href="${n.url}" class="${n.leida ? "" : "unread"}"><span>${escapar(n.mensaje)}</span><small>${escapar(n.fecha)}</small></a>`).join("")
          : '<p class="search-msg">No tiene notificaciones.</p>';
      } catch (_) { /* sin conexión: se intenta en el siguiente ciclo */ }
    }

    campana.addEventListener("click", (e) => {
      e.preventDefault();
      const abrir = panel.hidden;
      panel.hidden = !abrir;
      campana.setAttribute("aria-expanded", String(abrir));
      if (abrir) actualizar();
    });
    document.addEventListener("click", (e) => { if (!e.target.closest(".notif-wrap")) panel.hidden = true; });
    $("[data-notif-read]", panel).addEventListener("click", async () => {
      await fetch("/api/notificaciones/leer", { method: "POST", headers: { Accept: "application/json" } });
      actualizar();
    });

    actualizar();
    setInterval(() => { if (!document.hidden) actualizar(); }, 30000); // consulta cada 30 s si la pestaña está visible
  }

  /* 11. Animaciones: KPIs que cuentan y barras que crecen ------------------- */
  const sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!sinMovimiento) {
    $$(".kpi strong").forEach((nodo) => {
      const final = Number(nodo.textContent.trim());
      if (!Number.isInteger(final) || final <= 0) return;
      const inicio = performance.now();
      const paso = (t) => {
        const avance = Math.min((t - inicio) / 700, 1);
        nodo.textContent = Math.round(final * (1 - Math.pow(1 - avance, 3)));
        if (avance < 1) requestAnimationFrame(paso);
      };
      nodo.textContent = "0";
      requestAnimationFrame(paso);
    });
    $$(".bar-fill").forEach((barra, i) => {
      const ancho = barra.style.width;
      barra.style.width = "0";
      setTimeout(() => { barra.style.width = ancho; }, 80 + i * 40);
    });
  }

  /* 12. Aviso de cambios sin guardar en formularios largos ------------------ */
  $$("form[data-warn-unsaved]").forEach((form) => {
    let modificado = false;
    form.addEventListener("input", () => { modificado = true; });
    form.addEventListener("submit", () => { modificado = false; });
    window.addEventListener("beforeunload", (e) => { if (modificado) { e.preventDefault(); e.returnValue = ""; } });
  });

  /* Botones de impresión (acta y reportes) */
  $$("[data-print]").forEach((b) => b.addEventListener("click", () => window.print()));
})();
