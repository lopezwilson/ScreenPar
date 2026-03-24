import pyautogui
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageDraw
import threading
import time
from pynput import keyboard

class FullScreenSelector:
    """Ventana para seleccionar cualquier zona de la pantalla completa."""
    def __init__(self):
        self.record_region = None

    def select(self):
        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.3)
        root.overrideredirect(True)  # sin bordes
        root.configure(bg='black')

        self.start_x = None
        self.start_y = None
        self.rect = None

        canvas = tk.Canvas(root, bg='black', highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        def start_draw(event):
            self.start_x, self.start_y = event.x, event.y
            self.rect = canvas.create_rectangle(self.start_x, self.start_y,
                                                self.start_x, self.start_y,
                                                outline="red", width=2, dash=(2,2))

        def drawing(event):
            canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

        def end_draw(event):
            x1, y1, x2, y2 = self.start_x, self.start_y, event.x, event.y
            self.record_region = (min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
            root.destroy()

        canvas.bind("<ButtonPress-1>", start_draw)
        canvas.bind("<B1-Motion>", drawing)
        canvas.bind("<ButtonRelease-1>", end_draw)

        root.mainloop()
        return self.record_region

class GifRecorder:
    """Clase para grabar GIF con cursor grande, semi-transparente y velocidad ajustable."""
    def __init__(self, region, duration=200):
        self.record_region = region
        self.frames = []
        self.recording = False
        self.thread = None
        self.duration = duration  # duración de cada frame en ms
        self.keyboard_listener = None
        self.shift_pressed = False
        self.root = None

    def set_root(self, root):
        self.root = root

    def on_key_press(self, key):
        if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self.shift_pressed = True
        elif key == keyboard.Key.print_screen and self.shift_pressed:
            self.stop_recording(self.root)

    def on_key_release(self, key):
        if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self.shift_pressed = False

    def record_screen(self):
        cursor_radius = 15
        cursor_color = (255, 0, 0, 128)  # rojo semi-transparente

        while self.recording:
            frame = pyautogui.screenshot(region=self.record_region)
            img = frame.convert("RGBA")

            overlay = Image.new("RGBA", img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)

            x, y = pyautogui.position()
            left, top = self.record_region[0], self.record_region[1]

            draw.ellipse((x-cursor_radius-left, y-cursor_radius-top,
                          x+cursor_radius-left, y+cursor_radius-top),
                         fill=cursor_color)

            img = Image.alpha_composite(img, overlay)
            self.frames.append(img.convert("RGB"))
            time.sleep(0.2)

    def start_recording(self):
        if not self.record_region:
            print("⚠️ Zona de grabación no definida")
            return
        self.frames = []
        self.recording = True
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.keyboard_listener.start()
        self.thread = threading.Thread(target=self.record_screen, daemon=True)
        self.thread.start()
        print("🎥 Grabación iniciada. Presiona Shift + PrintScreen para detener.")

    def stop_recording(self, root=None):
        self.recording = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.thread:
            self.thread.join()
        if root:
            root.deiconify()
        if self.frames:
            file_path = filedialog.asksaveasfilename(defaultextension=".gif",
                                                     filetypes=[("GIF files","*.gif")])
            if file_path:
                self.frames[0].save(file_path, save_all=True, append_images=self.frames[1:],
                                    duration=self.duration, loop=0)
                print(f"✅ GIF guardado en: {file_path}")

def main():
    selector = FullScreenSelector()
    region = selector.select()
    if not region:
        print("⚠️ No se seleccionó ninguna zona. Saliendo...")
        return

    root = tk.Tk()
    root.title("Control de Grabación")

    tk.Label(root, text="Velocidad del GIF (ms por frame):").pack(pady=5)
    duration_entry = tk.Entry(root)
    duration_entry.insert(0, "200")  # valor por defecto
    duration_entry.pack(pady=5)

    recorder = GifRecorder(region)
    recorder.set_root(root)

    def start():
        try:
            recorder.duration = int(duration_entry.get())
        except ValueError:
            recorder.duration = 200
        root.withdraw()
        root.after(2000, lambda: recorder.start_recording())

    start_btn = tk.Button(root, text="🎥 Iniciar Grabación", command=start)
    start_btn.pack(padx=10, pady=10)

    stop_btn = tk.Button(root, text="⏹️ Finalizar Grabación", command=lambda: recorder.stop_recording(root))
    stop_btn.pack(padx=10, pady=10)

    quit_btn = tk.Button(root, text="❌ Salir", command=root.quit)
    quit_btn.pack(padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
