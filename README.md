# ERP Despacho Contable Mexicano 🇲🇽📊

Un sistema integral (ERP/CRM) diseñado específicamente para despachos contables en México. Construido con Python y Streamlit, permite administrar clientes, leer Constancias de Situación Fiscal (PDF), procesar facturas (XML CFDI), generar papeles de trabajo, administrar honorarios, enviar notificaciones y organizar el trabajo del equipo mediante un tablero Kanban.

## Características Principales

1.  **Directorio y Multiusuario:** Gestión de Personas Físicas y Morales. Roles de Administrador (visibilidad total) y Auxiliar (solo clientes asignados).
2.  **Carga Masiva y Extracción Inteligente:** Carga masiva de clientes vía Excel o autocompletado leyendo el PDF de la Constancia de Situación Fiscal.
3.  **Calculadora de Impuestos (RESICO/Actividad Empresarial):** Lectura masiva de XMLs (Ingresos, Egresos, Nómina) y cálculo preliminar de ISR e IVA mensual.
4.  **Tablero Kanban (Staff):** Organización de tareas del equipo (Por Revisar, En Proceso, Finalizada).
5.  **Finanzas del Despacho:** Dashboard ejecutivo interactivo (Plotly) para el control de honorarios cobrados y morosidad.
6.  **Portal del Cliente y Notificaciones:** Acceso seguro (encriptado con `bcrypt`) para que el cliente vea su estatus, descargue sus líneas de captura y reciba recordatorios por correo simulado.
7.  **IA Asistente Fiscal:** Un bot integrado para responder preguntas rápidas sobre la Ley del ISR e IVA en México.
8.  **Simulador de Facturación CFDI:** Generación de PDF y XML para cobrar honorarios.
9.  **Exportación CONTPAQi y DIOT:** Generación de layouts TXT para pólizas masivas y carga de la DIOT.

## Requisitos de Instalación

1.  Asegúrate de tener **Python 3.9 o superior** instalado.
2.  Clona este repositorio en tu computadora o en tu servidor (VPS/Render).
3.  Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

## Ejecución Local

Para correr la aplicación en tu computadora, abre tu terminal en la carpeta del proyecto y ejecuta:

```bash
streamlit run app.py
```

El navegador se abrirá automáticamente en `http://localhost:8501`.

### Credenciales de Acceso Inicial
*   **Pestaña:** Acceso Despacho (Staff)
*   **Usuario:** `admin`
*   **Contraseña:** `admin`

*(Se recomienda crear un nuevo administrador y eliminar este usuario por seguridad).*

## Despliegue en la Nube (Deploy)

La plataforma está lista para hospedarse en servicios como **Render**, **Heroku** o **Streamlit Community Cloud**. 
Asegúrate de agregar un "Persistent Disk" a tu servicio (ej. Render) si deseas que la base de datos `despacho.db` y la carpeta `archivos_clientes/` no se borren en cada reinicio del servidor.

## Tecnologías Utilizadas
*   **Frontend y Servidor:** Streamlit, st-aggrid, Plotly.
*   **Base de Datos y Seguridad:** SQLite3, Pandas, Bcrypt.
*   **Procesamiento de Documentos:** pdfplumber, xml.etree, fpdf2, openpyxl, ColorThief.
