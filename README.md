# ScreenPar

ScreenPar permite capturar una zona de la pantalla como imagen o grabarla como GIF.

## Uso

1. Ejecuta `main.py`.
2. Elige `Capturar imagen` o `Iniciar grabación`.
3. Arrastra sobre la pantalla para seleccionar la zona. Pulsa `Esc` para cancelar.
4. Para una captura, usa el editor para agregar recuadros, círculos, flechas o texto antes de guardarla.
5. La captura se copia automáticamente al portapapeles. Usa `Copiar imagen` después de editarla y luego `Ctrl + V` para pegarla en otra aplicación.
6. Elegí el tamaño de fuente entre `8` y `72` antes de agregar texto; también podés aplicarlo a un texto seleccionado.
7. Hacé clic en una anotación para moverla; usa `Editar texto` o `Eliminar` para modificarla.
8. Activa `Rellenar rectángulos` y ajusta `Transparencia del fondo`: `0%` es opaco y `100%` es completamente transparente.
9. Si la imagen es grande, usa las barras de desplazamiento del editor para recorrerla.
10. Las imágenes grandes se ajustan automáticamente para verse completas en el editor; las anotaciones se guardan conservando la resolución original.
11. Usa los controles nativos de la barra superior para maximizar, restaurar o minimizar el editor.
12. Usa `Seleccionar ventana con mouse`, cerrá el aviso y mové el cursor: la ventana bajo el mouse se resaltará; hacé clic para elegirla.
13. Para un GIF, detén con el botón o con `Shift + PrintScreen`.
14. Cambia el intervalo del GIF si necesitas más fluidez o archivos más pequeños.

El GIF usa el cursor predeterminado del sistema, incluyendo sus cursores personalizados y cambios de forma (por ejemplo, la mano sobre un enlace). También puedes activar o desactivar el parpadeo al hacer clic y mostrar opcionalmente el texto que escribes junto al cursor.

La duración de cada tecla mostrada se puede configurar en milisegundos; el valor predeterminado es `1000 ms`.

También se muestran teclas especiales como `F4` y combinaciones como `Ctrl + K`; cada indicación desaparece después del tiempo configurado, que por defecto es un segundo.

La selección se puede cambiar en cualquier momento desde `Cambiar zona`.
