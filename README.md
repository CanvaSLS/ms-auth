# CanvaSLS · ms-auth

Servicio de autenticación con Lambda (Python 3.11), API Gateway REST y DynamoDB.
Preparado para AWS Academy con **LabRole**, Serverless Framework 3.40.0 y los
contratos actuales de los otros cinco microservicios, `frontend-kit` y `datos-seed`.

## Clonar y desplegar

Requisitos: Node.js/npm y credenciales del Learner Lab activo. Python es necesario
solo para cargar cuentas demo. No se necesitan Docker, AWS CLI, Cognito, RDS,
layers, plugins externos ni una cuenta de Serverless Dashboard.

En PowerShell, desde la carpeta clonada:

```powershell
$env:AWS_ACCESS_KEY_ID = '<access key del laboratorio>'
$env:AWS_SECRET_ACCESS_KEY = '<secret key del laboratorio>'
$env:AWS_SESSION_TOKEN = '<session token del laboratorio>'
$env:AWS_DEFAULT_REGION = 'us-east-1'

$env:FRONTEND_ORIGIN = 'http://localhost:5173' # cambiar por el origen exacto de Amplify
$env:TOKEN_TTL_SECONDS = '3600'
```

Configurar las invitaciones institucionales antes del despliegue. Este bloque genera
códigos aleatorios; conservar sus valores para no rotarlos en cada despliegue:

```powershell
function New-InviteCode {
  $bytes = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  [Convert]::ToBase64String($bytes)
}
$env:TENANT_INVITE_CODES = @{
  UTEC = (New-InviteCode)
  NORTE = (New-InviteCode)
  ANDINO = (New-InviteCode)
} | ConvertTo-Json -Compress

npx.cmd --yes serverless@3.40.0 deploy --stage dev --region us-east-1
npx.cmd --yes serverless@3.40.0 info --stage dev --verbose
```

`npx.cmd` evita el bloqueo de scripts `.ps1` en Windows. En Bash usar `npx` y exportar
las mismas variables. `.env.example` es una referencia, no se carga automáticamente.
Las credenciales temporales se renuevan cuando vence la sesión de Academy.
`FRONTEND_ORIGIN` admite un único origen exacto, sin rutas ni `/` final.

Se reutiliza `arn:aws:iam::<cuenta actual>:role/LabRole`. Si tiene otro path,
configurar `LAB_ROLE_ARN` con su ARN real. No se crean ni modifican roles/policies
IAM. El stack crea seis Lambdas, API REST, permisos de invocación, dos tablas,
logs Lambda (14 días) y el bucket de artefactos de Serverless. El rol del despliegue
debe poder crear estos recursos y pasar LabRole; LabRole debe permitir logs y las
lecturas, consultas, escrituras transaccionales, actualización y borrado de DynamoDB.
Los permisos efectivos dependen del laboratorio y deben verificarse al desplegar.

Los outputs son `AuthApiUrl`, `AuthorizerArn`, `UsersTableName`, `TokensTableName`.
Asignar `AuthApiUrl` a `VITE_API_AUTH` en Amplify y recompilar el frontend.
Compartir cada invitación solo con su institución; nunca incluirla en `VITE_*`.
Los códigos están en el entorno de la Lambda de registro y en los artefactos de
CloudFormation; no publicar `.serverless` ni la salida de `serverless print`.

## Compatibilidad con la infraestructura del proyecto

Se revisaron `infra-base`, Cursos, Evaluaciones, Analítica, Notificaciones,
Práctica, el frontend, los datos seed y los scripts operativos del directorio padre.
Estos contratos prevalecen sobre los nombres propuestos en la especificación inicial:

| Contrato existente | Implementación de auth |
|---|---|
| Tenants `UTEC`, `NORTE`, `ANDINO` | Lista permitida explícita, sin crear instituciones dinámicas |
| Roles `alumno`, `docente`, `admin` | El registro solo crea `alumno`; acepta `estudiante` como alias de entrada |
| IDs `D001`, `A00001`, `A00003`, `X01` del seed | Se conservan: coinciden con cursos, matrículas, entregas y notificaciones |
| IDs SQL `VARCHAR(20)` | Nuevas cuentas reciben ID aleatorio de 20 caracteres; no se usa el email como ID |
| Authorizer `ms-auth-<stage>-autorizar` | Nombre físico explícito y output ARN reutilizable |
| Contexto de negocio | `tenant_id`, `user_id`, `rol`, `nombre`, leídos de la cuenta vigente |
| Frontend login | Devuelve `token`, `expira_epoch`, `expira_en`, `usuario`, además del contrato `access_token` |
| `/auth/registro`, `/auth/usuarios` | Ambas rutas se conservan; `/auth/register` sigue disponible |
| Seed global escribe `sp_usuarios` | Tabla con PK `tenant_id`, SK `user_id` y GSI `gsi_email` |
| Password del seed en `salt` + `pwd_hash` | Se verifica y migra a PBKDF2 de 600 000 iteraciones al primer login válido |
| Integración TOKEN de los cinco APIs | Política IAM para `methodArn`, contexto escalar y caché en cero |

`infra-base` proporciona SNS, S3 y RDS a los servicios de negocio. Auth no depende
de esos recursos ni necesita `DB_PASSWORD`, VPC o configuración de eventos.
Para desplegar el conjunto: `infra-base` → `ms-auth` → servicios de negocio → seed
global → frontend. También se puede desplegar auth de forma independiente.

Los otros `serverless.yml` ya apuntan al nombre correcto del Authorizer y Serverless
crea sus permisos de invocación. No es necesario modificarlos para integrar auth.
El ejemplo [examples/business-serverless.yml](examples/business-serverless.yml)
muestra la alternativa que resuelve el ARN desde el output de CloudFormation.

**Un stack de auth por cuenta/región:** `sp_usuarios` tiene nombre fijo para que
funcione el seed global, igual que las tablas de los demás servicios. No desplegar
otro stage en paralelo en esa cuenta/región. Si la tabla ya pertenece a un despliegue
anterior, actualizar su mismo stack `ms-auth-<stage>`; crear otro stack con ese nombre
de tabla fallará. No se elimina ni se importa automáticamente una tabla ajena.

Las sesiones se guardan en `ms-auth-<stage>-t_tokens_acceso`, PK `token_hash` y TTL
`expires_at`. La antigua tabla de tokens en texto plano no se consulta ni se migra;
los usuarios deben volver a iniciar sesión. No cambiar manualmente su clave primaria.

`docs-ops/deploy-all.sh` necesita que las variables de invitación y origen también
estén exportadas antes de ejecutarlo. Los generadores OpenAPI y el emulador local
del proyecto describen el contrato antiguo: su ejemplo de registro debe añadir
`invite_code` y cumplir la política de contraseña. Las copias externas de `common.py`
y las herramientas de pruebas generales no se modificaron; este `common.py` es
específico de auth y no se debe copiar a los otros servicios.

El pin de Serverless 3.40.0 y el runtime Python 3.11 corresponden a **este** repositorio.
Los otros repositorios aún declaran Python 3.12; su compatibilidad con la versión del
framework que utilicen debe revisarse al desplegarlos (3.40.0 no acepta ese runtime
en su esquema de validación). Esto no cambia el contrato del Authorizer.

## Rutas y contratos

Todas las rutas son relativas a `AuthApiUrl`.

| Método | Ruta | Acceso |
|---|---|---|
| POST | `/auth/register` o `/auth/registro` | Invitación; crea alumno, responde 201 |
| POST | `/auth/login` | Credenciales, responde 200 |
| GET | `/auth/me` | Bearer; perfil público |
| POST | `/auth/logout` | Bearer; revoca solo la sesión presentada |
| GET | `/auth/usuarios?limit=25&cursor=...` | Bearer; docente/admin del tenant |

Registro:

```json
{
  "tenant_id": "UTEC",
  "nombre": "Ana Torres",
  "email": "ana@utec.edu.pe",
  "password": "UnaClaveLarga2026!",
  "invite_code": "CODIGO_INSTITUCIONAL_REAL"
}
```

Política de registro: 12–128 caracteres, con mayúscula, minúscula y número. El email
se recorta y pasa a minúsculas; la contraseña conserva sus espacios. No se otorgan
roles privilegiados desde el registro público. Los roles administrativos se crean
con un operador autorizado. La cuenta no inicia sesión automáticamente.

Login requiere `tenant_id`, `email`, `password`. La respuesta incluye:

```json
{
  "access_token": "TOKEN_OPACO",
  "token": "MISMO_TOKEN_OPACO",
  "token_type": "Bearer",
  "expires_in": 3600,
  "expira_epoch": 1800000000,
  "expira_en": "2027-01-15T08:00:00Z",
  "usuario": {
    "tenant_id": "UTEC",
    "user_id": "A00001",
    "email": "ana.torres@utec.edu.pe",
    "nombre": "Ana Torres",
    "rol": "alumno"
  }
}
```

Fechas ilustrativas: los valores reales se calculan al emitir cada sesión.
Enviar `Authorization: Bearer <token>` a las rutas protegidas. Errores:
400 entrada inválida; 401 credenciales/token inválidos; 403 invitación, rol, tenant
o cuenta sin acceso; 409 duplicado; 429 throttling; 500 error interno controlado.
Los errores JSON tienen `error` y `mensaje`. Un fallo de DynamoDB en el Authorizer
produce error del gateway y nunca una autorización.

## Seguridad y datos

El registro crea atómicamente el usuario y una reserva `EMAIL#<email>` dentro del
mismo tenant para impedir duplicados concurrentes. Estas reservas no se exponen en
`/auth/usuarios` ni forman parte del índice de emails. Las cuentas del seed se
buscan por `gsi_email` y luego se releen con consistencia fuerte. El GSI es eventual:
justo después de una carga masiva puede ser necesario reintentar el login.
El seed es una operación administrativa: no ejecutarlo a la vez que registros
públicos ni usarlo para modificar cuentas de usuarios reales.

Los hashes antiguos de 10 000 iteraciones solo se aceptan para migrar las cuentas
existentes del seed; al autenticar se guardan con sal nueva y 600 000 iteraciones,
eliminando `salt` y `pwd_hash`. No se cambia la contraseña ni el ID. Las nuevas
cuentas ya usan el formato seguro. Si se vuelve a cargar el seed, sus filas antiguas
se migrarán otra vez en el siguiente login.

Los tokens tienen 32 bytes aleatorios y solo se guarda su SHA-256. La expiración se
comprueba explícitamente, además del TTL de limpieza eventual. El Authorizer relee
la cuenta para reflejar cambios de rol y desactivaciones. No se cachean decisiones.
Las respuestas usan `Cache-Control: no-store`, no devuelven hashes y los logs no
incluyen contraseñas ni tokens. Throttling del stage: 10 solicitudes/s y ráfaga de 20,
como límite global de mejor esfuerzo, sin bloqueo por IP/usuario.

Los servicios de negocio reciben el contexto autenticado y deben comprobar además
la propiedad/asignación del recurso. Auth no convierte esos APIs en endpoints de
red PRIVATE. No compartir permisos directos sobre las tablas de auth con los otros
servicios. El uso obligatorio de LabRole limita el mínimo privilegio por función.

## Cuentas demo

Si se carga `datos-seed/seed.py`, auth puede utilizar sus cuentas directamente.
Para una demo pequeña, sin clonar ningún otro repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/seed_demo.py --region us-east-1 --demo
```

Crea `profe`, `ana.torres`, `valeria.mendoza` y `admin` en los dominios
`utec.edu.pe`, `inorte.edu.pe`, `andino.edu.pe`, con los IDs del seed global y
contraseña **Demo2026!**, utilizada por el frontend de laboratorio. Las cuentas
existentes quedan intactas. Sin `--demo`, pide una contraseña que cumpla la política.
La excepción de contraseña corta solo pertenece a la carga administrativa demo.
Crear usuarios no crea cursos ni matrículas: esos datos pertenecen al seed global.

## Estructura y validación realizada

`auth/handlers/` contiene los seis handlers. `auth/storage.py` implementa el acceso
a DynamoDB; `auth/security.py`, contraseñas y tokens; `common.py`, HTTP y contexto.
`handler.py` conserva aliases locales. `plugins/academy-stage.cjs` es un ajuste local
sin dependencias que declara throttling en el Deployment de API Gateway de Serverless v3.

Antes de limpiar el repositorio se aprobaron 16 comprobaciones locales: aceptación
de auth, contrato del SDK, migración del seed y ejecución de handlers reales de los
cinco servicios con persistencia simulada. Se verificó además el paquete generado:
seis Lambdas, rol existente, GSI de usuarios, TTL, rutas y Authorizer sin caché.
Se retiraron pruebas, dependencias de validación, bytecode y artefactos de empaquetado
para entregar solo código, configuración y documentación. No se desplegó ni se
validaron permisos/endpoints en AWS; esa comprobación requiere el laboratorio activo.
