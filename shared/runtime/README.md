# Cascarón de servicio (runtime)

Pieza genérica que cada componente reutiliza para funcionar como servicio desplegable. Con su adaptador, hace siempre lo mismo:

1. Recibe una tarea según `shared/contracts/task-contract.md`.
2. Valida las precondiciones declaradas en `agent/capabilities.md`, antes de ejecutar.
3. Obtiene los artefactos de entrada por `shared/data_access`.
4. Llama al adaptador del componente.
5. Verifica que existan las salidas declaradas (no confía en el código de retorno).
6. Registra los artefactos producidos, también los de una tarea fallida, con su estado.
7. Responde con estado, salidas, error y avisos, sin caerse ante un fallo.

Reglas: no importa nada de `components/` ni de `legacy/`. El transporte por el que llegan las tareas (cola, HTTP u otro) se decide en el paso 6; el cascarón lo oculta al adaptador.
