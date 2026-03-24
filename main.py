import pyautogui
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageDraw, ImageTk
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

class ScreenshotCapture:
    """Clase para capturar pantalla y guardar en PNG o JPEG."""
    def __init__(self, region):
        self.record_region = region
        self.image = None
        self.edit_window = None
        self.drawing_canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.text_entries = []
        self.current_color = "red"

    def capture_and_save(self):
        if not self.record_region:
            print("⚠️ Zona de captura no definida")
            return
        
        self.image = pyautogui.screenshot(region=self.record_region)
        self.show_editor()

    def show_editor(self):
        self.edit_window = tk.Toplevel()
        self.edit_window.title("Editor de Captura")
        
        img_width, img_height = self.image.size
        
        canvas_frame = tk.Frame(self.edit_window)
        canvas_frame.pack(padx=10, pady=10)
        
        self.drawing_canvas = tk.Canvas(canvas_frame, width=img_width, height=img_height)
        self.drawing_canvas.pack()
        
        self.photo = ImageTk.PhotoImage(self.image)
        self.drawing_canvas.create_image(0, 0, anchor="nw", image=self.photo)
        
        self.drawing_canvas.bind("<ButtonPress-1>", self.start_draw)
        self.drawing_canvas.bind("<B1-Motion>", self.drawing)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.end_draw)
        
        self.drawing_canvas.tag_bind("draggable", "<ButtonPress-1>", self.start_drag)
        self.drawing_canvas.tag_bind("draggable", "<B1-Motion>", self.drag)
        self.drawing_canvas.tag_bind("draggable>", "<ButtonRelease-1>", self.stop_drag)
        
        btn_frame = tk.Frame(self.edit_window)
        btn_frame.pack(pady=10)
        
        color_frame = tk.Frame(btn_frame)
        color_frame.pack(side="left", padx=5)
        
        tk.Label(color_frame, text="Color:").pack(side="left")
        self.color_var = tk.StringVar(value="red")
        color_combo = ttk.Combobox(color_frame, textvariable=self.color_var, values=["red", "blue", "green", "black", "yellow"], state="readonly", width=10)
        color_combo.pack(side="left", padx=5)
        color_combo.bind("<<ComboboxSelected>>", lambda e: setattr(self, 'current_color', self.color_var.get()))
        
        rect_btn = tk.Button(btn_frame, text="⬜ Dibujar Rectángulo", command=self.enable_rectangle_mode)
        rect_btn.pack(side="left", padx=5)
        
        text_btn = tk.Button(btn_frame, text="📝 Agregar Texto", command=self.enable_text_mode)
        text_btn.pack(side="left", padx=5)
        
        save_btn = tk.Button(btn_frame, text="💾 Guardar", command=self.save_image)
        save_btn.pack(side="left", padx=5)
        
        self.mode = "rect"
        self.rects = []
        self.text_items = []
        self.drag_data = {"x": 0, "y": 0, "item": None}

    def enable_rectangle_mode(self):
        self.mode = "rect"

    def enable_text_mode(self):
        self.mode = "text"

    def start_draw(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.mode == "rect":
            self.rect = self.drawing_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=self.current_color, width=3)
        elif self.mode == "text":
            self.show_text_input(event.x, event.y)

    def drawing(self, event):
        if self.mode == "rect" and self.rect:
            self.drawing_canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def end_draw(self, event):
        if self.mode == "rect" and self.rect:
            x1, y1, x2, y2 = self.start_x, self.start_y, event.x, event.y
            self.rects.append((min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1), self.current_color))
            self.rect = None

    def start_drag(self, event):
        item = self.drawing_canvas.find_closest(event.x, event.y)
        if item:
            self.drag_data["item"] = item[0]
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def drag(self, event):
        if self.drag_data["item"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.drawing_canvas.move(self.drag_data["item"], dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def stop_drag(self, event):
        if self.drag_data["item"]:
            coords = self.drawing_canvas.coords(self.drag_data["item"])
            for i, (tx, ty, text, color, text_id) in enumerate(self.text_entries):
                if text_id == self.drag_data["item"]:
                    self.text_entries[i] = (coords[0], coords[1], text, color, text_id)
                    break
            self.drag_data["item"] = None

    def show_text_input(self, x, y):
        input_win = tk.Toplevel(self.edit_window)
        input_win.title("Agregar Texto")
        input_win.geometry("300x100")
        input_win.transient(self.edit_window)
        
        tk.Label(input_win, text="Texto:").pack(pady=5)
        text_entry = tk.Entry(input_win, width=40)
        text_entry.pack(pady=5)
        
        def add_text():
            text = text_entry.get()
            if text:
                text_id = self.drawing_canvas.create_text(x, y, text=text, fill=self.current_color, font=("Arial", 16, "bold"), tags="draggable")
                self.text_entries.append((x, y, text, self.current_color, text_id))
            input_win.destroy()
        
        tk.Button(input_win, text="Agregar", command=add_text).pack(pady=5)
        text_entry.focus()

    def save_image(self):
        edit_img = self.image.copy()
        draw = ImageDraw.Draw(edit_img)
        
        for rx, ry, rw, rh, color in self.rects:
            draw.rectangle([rx, ry, rx + rw, ry + rh], outline=color, width=3)
        
        for tx, ty, text, color, text_id in self.text_entries:
            draw.text((tx, ty), text, fill=color)
        
        file_path = filedialog.asksaveasfilename(
            parent=self.edit_window,
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg")
            ]
        )
        
        if file_path:
            if file_path.lower().endswith(('.jpg', '.jpeg')):
                rgb_image = edit_img.convert("RGB")
                rgb_image.save(file_path, "JPEG", quality=95)
            else:
                edit_img.save(file_path, "PNG")
            print(f"✅ Captura guardada en: {file_path}")
            self.edit_window.destroy()

class GifRecorder:
    """Clase para grabar GIF con cursor grande, semi-transparente y velocidad ajustable."""
    def __init__(self, region, duration=200):
        self.record_region = region
        self.frames = []
        self.recording = False
        self.thread = None
        self.duration = duration
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

    screenshot_capture = ScreenshotCapture(region)

    def take_screenshot():
        root.withdraw()
        root.after(500, screenshot_capture.capture_and_save)
        root.after(1000, root.deiconify)

    def start():
        try:
            recorder.duration = int(duration_entry.get())
        except ValueError:
            recorder.duration = 200
        root.withdraw()
        root.after(2000, lambda: recorder.start_recording())

    screenshot_btn = tk.Button(root, text="📷 Captura de Pantalla", command=take_screenshot)
    screenshot_btn.pack(padx=10, pady=10)

    start_btn = tk.Button(root, text="🎥 Iniciar Grabación", command=start)
    start_btn.pack(padx=10, pady=10)

    stop_btn = tk.Button(root, text="⏹️ Finalizar Grabación", command=lambda: recorder.stop_recording(root))
    stop_btn.pack(padx=10, pady=10)

    quit_btn = tk.Button(root, text="❌ Salir", command=root.quit)
    quit_btn.pack(padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
