# ScreenPar

ScreenPar permite capturar una zona de la pantalla como imagen o grabarla como GIF.

## Uso

1. Ejecuta `main.py`.
2. Elige `Capturar imagen` o `Iniciar grabación`.
3. Arrastra sobre la pantalla para seleccionar la zona. Pulsa `Esc` para cancelar.
4. Para una captura, escribe directamente el nombre del archivo.
5. Para un GIF, detén con el botón o con `Shift + PrintScreen`.
6. Cambia el intervalo del GIF si necesitas más fluidez o archivos más pequeños.

El GIF usa el cursor predeterminado del sistema, incluyendo sus cursores personalizados y cambios de forma (por ejemplo, la mano sobre un enlace). También puedes activar o desactivar el parpadeo al hacer clic y mostrar opcionalmente el texto que escribes junto al cursor.

La duración de cada tecla mostrada se puede configurar en milisegundos; el valor predeterminado es `1000 ms`.

También se muestran teclas especiales como `F4` y combinaciones como `Ctrl + K`; cada indicación desaparece después del tiempo configurado, que por defecto es un segundo.

La selección se puede cambiar en cualquier momento desde `Cambiar zona`.
