# Autenticación de identidad

## AUTH-20261021-01 — pantalla de condiciones sin formulario HTML

Estado: **verificado** en cliente real y Home Assistant 2026.10.2.

### Síntoma y reproducción

La integración queda en `setup_error`. Error saneado:
`Identity terms form missing required fields: _csrf, hmac, relayState; available fields:`.
No era el HTTP 403 de sesiones/cabeceras reparado en `5623de4`.

### Causa confirmada

El proveedor devuelve HTTP 200 con una pantalla de condiciones renderizada por
JavaScript, sin etiquetas `form` ni `input`. El modelo JSON está en
`window._IDK.templateModel`; los valores CSRF están en propiedades del objeto
externo. El parser anterior solo reconocía formularios HTML.

Se inspeccionó la estructura de la respuesta y el bundle público del proveedor.
El formulario renderizado publica al endpoint de identidad de condiciones y
envía CSRF, hmac, relayState, país y siete propiedades por documento legal. Los
enlaces `saveLink` dentro del documento son destinos internos del proveedor:
**no deben utilizarse como endpoints de la integración**.

### Corrección

`terms.py` conserva el formulario HTML como primera opción. Solo cuando no existe
ese formulario lee una única asignación `window._IDK`, decodifica el JSON del
modelo y extrae literales de cadena. No ejecuta JavaScript. Rechaza modelos,
clientes, CSRF y documentos incompletos o ambiguos y construye los mismos inputs
que el frontend oficial. La conexión mantiene su comprobación de mismo origen.
No se cambian el tratamiento independiente del consentimiento de marketing ni
las credenciales, configuración del vehículo o lógica de datos parciales.

### Evidencia y límites

Diecinueve pruebas aprobadas; parser comprobado sobre la respuesta real sin
persistir sus valores. Tras autorización expresa para las condiciones obligatorias
v4.0, login real correcto y un vehículo recuperado. La aceptación legal es un
efecto externo: revisar y autorizar los cambios de condiciones antes de repetir
esta comprobación; no asumir que una autorización para una versión cubre futuras.

Despliegue limitado a `terms.py`, con copia previa y SHA256. No se recomienda
reemplazar toda la integración a partir de una copia histórica. La restauración
del servicio HA se registra en el perfil de validación: entrada cargada y
dieciocho entidades disponibles tras el reinicio, sin errores de autenticación.
La calefacción se releyó y restituyó a su estado previo. No se alteró su automatización.

## DEV-20261021-01 — limpieza del diagnóstico en Windows

Estado: verificado. El primer diagnóstico permanecía dentro del directorio
temporal al limpiarlo; Windows lo bloqueó y tempfile produjo errores repetidos.
Se restituyó el directorio de trabajo en `finally` antes de la limpieza. Las
siguientes ejecuciones concluyeron correctamente. Era un fallo del diagnóstico,
no del componente instalado. No se almacenaron secretos en el directorio temporal.

## AUTH-20261029-01 — formulario universal de identidad

Estado: **verificado** en Home Assistant 2026.10.4 durante el arranque.
El proveedor devolvió una redirección relativa a `/u/login` y un formulario
con usuario y contraseña; el cliente anterior esperaba el flujo `signin-service`.
Se resuelven las redirecciones y se envía el formulario solo al origen de
identidad. Tras instalar el archivo y reiniciar, la integración cargó y sus
18 entidades estuvieron disponibles. Se conserva copia previa en Home Assistant.
Pendiente: verificar el formulario interactivo de reautenticación y la
renovación tras una caducidad natural. No se almacenaron credenciales ni URLs
de sesión. Un primer intento de instalación falló antes de sustituir el archivo
por incompatibilidad de `chmod --reference` con BusyBox; se usó modo 644.
