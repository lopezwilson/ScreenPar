import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk
import threading
import time
from pynput import keyboard, mouse

class FullScreenSelector:
    """Ventana para seleccionar cualquier zona de la pantalla completa."""
    def __init__(self):
        self.record_region = None

    def select(self, parent=None):
        root = tk.Toplevel(parent) if parent else tk.Tk()
        root.title("Seleccionar zona")
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.3)
        root.overrideredirect(True)  # sin bordes
        root.configure(bg='black')

        self.start_x = None
        self.start_y = None
        self.rect = None

        canvas = tk.Canvas(root, bg='black', highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)
        canvas.create_text(
            20, 20, anchor="nw",
            text="Arrastra para seleccionar una zona  |  Esc para cancelar",
            fill="white", font=("Arial", 16, "bold")
        )

        def start_draw(event):
            self.start_x, self.start_y = event.x, event.y
            self.rect = canvas.create_rectangle(self.start_x, self.start_y,
                                                self.start_x, self.start_y,
                                                outline="red", width=2, dash=(2,2))

        def drawing(event):
            if self.rect:
                canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

        def end_draw(event):
            x1, y1, x2, y2 = self.start_x, self.start_y, event.x, event.y
            width, height = abs(x2 - x1), abs(y2 - y1)
            if width > 2 and height > 2:
                self.record_region = (min(x1, x2), min(y1, y2), width, height)
                root.destroy()

        def cancel(event=None):
            self.record_region = None
            root.destroy()

        canvas.bind("<ButtonPress-1>", start_draw)
        canvas.bind("<B1-Motion>", drawing)
        canvas.bind("<ButtonRelease-1>", end_draw)
        root.bind("<Escape>", cancel)
        root.focus_force()

        root.wait_window()
        return self.record_region

class ScreenshotCapture:
    """Clase para capturar pantalla y guardar en PNG o JPEG."""
    def __init__(self, region, parent=None, on_closed=None):
        self.record_region = region
        self.parent = parent
        self.on_closed = on_closed
        self.image = None
        self.edit_window = None
        self.drawing_canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.text_entries = []
        self.current_color = "red"

    def capture_and_save(self):
        if self.capture_image():
            self.show_editor()

    def capture_image(self):
        if not self.record_region:
            messagebox.showwarning("Zona no definida", "Selecciona una zona antes de capturar.", parent=self.parent)
            return False

        try:
            self.image = pyautogui.screenshot(region=self.record_region)
            return True
        except Exception as error:
            messagebox.showerror("No se pudo capturar", f"Ocurrió un error al capturar la pantalla:\n{error}", parent=self.parent)
            if self.on_closed:
                self.on_closed(False)
            return False

    def save_direct_image(self):
        if self.parent:
            self.parent.deiconify()
            self.parent.lift()
            self.parent.focus_force()
            self.parent.update()

        file_path = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Guardar captura",
            initialfile="captura.png",
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg")
            ]
        )
        if not file_path:
            if self.on_closed:
                self.on_closed(False)
            return

        try:
            if file_path.lower().endswith((".jpg", ".jpeg")):
                self.image.convert("RGB").save(file_path, "JPEG", quality=95)
            else:
                self.image.save(file_path, "PNG")
        except Exception as error:
            messagebox.showerror("No se pudo guardar", f"Ocurrió un error al guardar la imagen:\n{error}", parent=self.parent)
            if self.on_closed:
                self.on_closed(False)
            return

        if self.on_closed:
            self.on_closed(True)

    def show_editor(self):
        self.edit_window = tk.Toplevel(self.parent)
        self.edit_window.title("Editor de Captura")
        if self.parent:
            self.edit_window.transient(self.parent)
        self.edit_window.protocol("WM_DELETE_WINDOW", self.close_editor)
        
        img_width, img_height = self.image.size
        
        help_label = tk.Label(
            self.edit_window,
            text="Elige una herramienta y haz clic o arrastra sobre la imagen. Puedes mover el texto después.",
            anchor="w"
        )
        help_label.pack(fill="x", padx=10, pady=(10, 0))

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
        self.drawing_canvas.tag_bind("draggable", "<ButtonRelease-1>", self.stop_drag)
        
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

        self.mode_var = tk.StringVar()
        tk.Label(self.edit_window, textvariable=self.mode_var, anchor="w").pack(fill="x", padx=10, pady=(0, 10))
        
        self.mode = "rect"
        self.rects = []
        self.text_items = []
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.enable_rectangle_mode()
        self.edit_window.bind("<Control-s>", lambda event: self.save_image())

    def enable_rectangle_mode(self):
        self.mode = "rect"
        if hasattr(self, "mode_var"):
            self.mode_var.set("Herramienta activa: rectángulo. Arrastra sobre la imagen.")

    def enable_text_mode(self):
        self.mode = "text"
        if hasattr(self, "mode_var"):
            self.mode_var.set("Herramienta activa: texto. Haz clic en la imagen.")

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
        item = self.drawing_canvas.find_withtag("current")
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
        input_win.grab_set()
        
        tk.Label(input_win, text="Texto:").pack(pady=5)
        text_entry = tk.Entry(input_win, width=40)
        text_entry.pack(pady=5)
        
        def add_text():
            text = text_entry.get()
            if text:
                text_id = self.drawing_canvas.create_text(x, y, text=text, fill=self.current_color, font=("Arial", 16, "bold"), tags="draggable")
                self.text_entries.append((x, y, text, self.current_color, text_id))
            input_win.destroy()

        actions = tk.Frame(input_win)
        actions.pack(pady=5)
        tk.Button(actions, text="Agregar", command=add_text).pack(side="left", padx=4)
        tk.Button(actions, text="Cancelar", command=input_win.destroy).pack(side="left", padx=4)
        input_win.bind("<Return>", lambda event: add_text())
        input_win.bind("<Escape>", lambda event: input_win.destroy())
        input_win.protocol("WM_DELETE_WINDOW", input_win.destroy)
        text_entry.focus()

    def close_editor(self, saved=False):
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.destroy()
        if self.on_closed:
            self.on_closed(saved)

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
            try:
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    rgb_image = edit_img.convert("RGB")
                    rgb_image.save(file_path, "JPEG", quality=95)
                else:
                    edit_img.save(file_path, "PNG")
            except Exception as error:
                messagebox.showerror("No se pudo guardar", f"Ocurrió un error al guardar la imagen:\n{error}", parent=self.edit_window)
                return
            self.close_editor(saved=True)

class GifRecorder:
    """Clase para grabar GIF con cursor grande, semi-transparente y velocidad ajustable."""
    def __init__(self, region, duration=200):
        self.record_region = region
        self.frames = []
        self.recording = False
        self.thread = None
        self.duration = duration
        self.keyboard_listener = None
        self.mouse_listener = None
        self.shift_pressed = False
        self.root = None
        self.status_callback = None
        self.finished_callback = None
        self.stop_lock = threading.Lock()
        self.click_lock = threading.Lock()
        self.click_started = 0
        self.click_effect_until = 0
        self.cursor_style = "highlight"
        self.click_blink = True

    def set_root(self, root):
        self.root = root

    def set_callbacks(self, status_callback=None, finished_callback=None):
        self.status_callback = status_callback
        self.finished_callback = finished_callback

    def set_cursor_options(self, style="highlight", click_blink=True):
        self.cursor_style = style
        self.click_blink = click_blink

    def notify(self, message):
        if self.status_callback:
            if self.root:
                self.root.after(0, lambda: self.status_callback(message))
            else:
                self.status_callback(message)

    def on_key_press(self, key):
        if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self.shift_pressed = True
        elif key == keyboard.Key.print_screen and self.shift_pressed:
            self.stop_recording()

    def on_key_release(self, key):
        if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self.shift_pressed = False

    def on_mouse_click(self, x, y, button, pressed):
        if not pressed or not self.click_blink or not self.record_region:
            return

        left, top, width, height = self.record_region
        if left <= x <= left + width and top <= y <= top + height:
            now = time.monotonic()
            with self.click_lock:
                self.click_started = now
                self.click_effect_until = now + 0.6

    def click_effect(self):
        with self.click_lock:
            now = time.monotonic()
            if now >= self.click_effect_until:
                return None
            elapsed = now - self.click_started
        return elapsed

    def draw_cursor(self, overlay, x, y, left, top):
        draw = ImageDraw.Draw(overlay)
        cursor_x, cursor_y = x - left, y - top
        click_elapsed = self.click_effect()

        if self.cursor_style == "arrow":
            points = [
                (cursor_x, cursor_y), (cursor_x, cursor_y + 29),
                (cursor_x + 8, cursor_y + 21), (cursor_x + 15, cursor_y + 34),
                (cursor_x + 21, cursor_y + 31), (cursor_x + 14, cursor_y + 18),
                (cursor_x + 27, cursor_y + 18)
            ]
            draw.polygon(points, fill=(255, 255, 255, 235))
            draw.line(points + [points[0]], fill=(0, 0, 0, 255), width=2)
        elif self.cursor_style == "hand":
            points = [
                (cursor_x + 8, cursor_y), (cursor_x + 12, cursor_y),
                (cursor_x + 12, cursor_y + 13), (cursor_x + 16, cursor_y + 10),
                (cursor_x + 20, cursor_y + 13), (cursor_x + 16, cursor_y + 20),
                (cursor_x + 14, cursor_y + 25), (cursor_x + 8, cursor_y + 27),
                (cursor_x + 3, cursor_y + 25), (cursor_x, cursor_y + 20),
                (cursor_x, cursor_y + 14), (cursor_x + 4, cursor_y + 13),
                (cursor_x + 5, cursor_y + 18), (cursor_x + 5, cursor_y + 5),
                (cursor_x + 8, cursor_y + 5)
            ]
            draw.polygon(points, fill=(255, 255, 255, 235))
            draw.line(points + [points[0]], fill=(0, 0, 0, 255), width=2)
        else:
            radius = 15
            draw.ellipse(
                (cursor_x - radius, cursor_y - radius,
                 cursor_x + radius, cursor_y + radius),
                fill=(255, 0, 0, 150)
            )

        if click_elapsed is not None:
            blink_on = int(click_elapsed / 0.1) % 2 == 0
            if blink_on:
                pulse_radius = 22 + int(min(click_elapsed, 0.4) * 35)
                draw.ellipse(
                    (cursor_x - pulse_radius, cursor_y - pulse_radius,
                     cursor_x + pulse_radius, cursor_y + pulse_radius),
                    outline=(255, 220, 0, 240), width=4
                )

    def record_screen(self):
        try:
            while self.recording:
                frame = pyautogui.screenshot(region=self.record_region)
                img = frame.convert("RGBA")

                overlay = Image.new("RGBA", img.size, (0,0,0,0))

                x, y = pyautogui.position()
                left, top = self.record_region[0], self.record_region[1]
                self.draw_cursor(overlay, x, y, left, top)

                img = Image.alpha_composite(img, overlay)
                self.frames.append(img.convert("RGB"))
                time.sleep(max(self.duration, 50) / 1000)
        except Exception:
            self.notify("La grabación se detuvo por un error de captura.")
            self.stop_recording()

    def start_recording(self):
        if not self.record_region:
            self.notify("Selecciona una zona antes de grabar.")
            return False
        if self.recording:
            return False
        self.frames = []
        self.recording = True
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.keyboard_listener.start()
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.mouse_listener.start()
        self.thread = threading.Thread(target=self.record_screen, daemon=True)
        self.thread.start()
        self.notify("Grabando. Usa el botón de detener o Shift + PrintScreen.")
        return True

    def stop_recording(self):
        with self.stop_lock:
            if not self.recording:
                return False
            self.recording = False

        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join()

        self.keyboard_listener = None
        self.mouse_listener = None
        self.thread = None
        frames = self.frames
        self.notify("Grabación detenida. Elige dónde guardar el GIF.")
        if self.finished_callback:
            if self.root:
                self.root.after(0, lambda: self.finished_callback(frames))
            else:
                self.finished_callback(frames)
        return True

def main():
    root = tk.Tk()
    root.title("ScreenPar")
    root.resizable(False, False)

    recorder = GifRecorder(None)
    recorder.set_root(root)

    status_var = tk.StringVar(value="Elige Capturar imagen o Iniciar grabación para comenzar.")
    region_var = tk.StringVar()

    def format_region(selected_region):
        x, y, width, height = selected_region
        return f"{width} x {height} px  (posición: {x}, {y})"

    region_var.set("No definida. Se solicitará al iniciar una grabación.")

    header = ttk.Frame(root, padding=(18, 16, 18, 8))
    header.pack(fill="x")
    ttk.Label(header, text="ScreenPar", font=("Arial", 18, "bold")).pack(anchor="w")
    ttk.Label(header, text="Captura y grabación de una zona de tu pantalla").pack(anchor="w", pady=(2, 0))

    region_frame = ttk.LabelFrame(root, text="Zona de grabación", padding=10)
    region_frame.pack(fill="x", padx=18, pady=(4, 10))
    ttk.Label(region_frame, textvariable=region_var).pack(side="left", fill="x", expand=True)

    controls = ttk.Frame(root, padding=(18, 0, 18, 8))
    controls.pack(fill="x")
    ttk.Label(controls, text="Intervalo del GIF (ms por imagen):").grid(row=0, column=0, sticky="w")
    duration_entry = ttk.Spinbox(controls, from_=50, to=2000, increment=10, width=8)
    duration_entry.set("200")
    duration_entry.grid(row=0, column=1, padx=(10, 0), sticky="w")
    ttk.Label(controls, text="Menor valor = más fluidez", foreground="#666666").grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))

    cursor_frame = ttk.LabelFrame(root, text="Cursor en el GIF", padding=10)
    cursor_frame.pack(fill="x", padx=18, pady=(0, 8))
    ttk.Label(cursor_frame, text="Mostrar como:").grid(row=0, column=0, sticky="w")
    cursor_style_var = tk.StringVar(value="Resaltado")
    cursor_combo = ttk.Combobox(
        cursor_frame,
        textvariable=cursor_style_var,
        values=["Resaltado", "Mano", "Flecha"],
        state="readonly",
        width=12
    )
    cursor_combo.grid(row=0, column=1, padx=(10, 0), sticky="w")
    click_blink_var = tk.BooleanVar(value=True)
    click_check = ttk.Checkbutton(
        cursor_frame,
        text="Parpadear al hacer clic",
        variable=click_blink_var
    )
    click_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 0))

    action_frame = ttk.Frame(root, padding=(18, 4, 18, 8))
    action_frame.pack(fill="x")

    screenshot_capture = ScreenshotCapture(None, parent=root)

    screenshot_btn = ttk.Button(action_frame, text="Capturar imagen", command=lambda: take_screenshot())
    screenshot_btn.grid(row=0, column=0, sticky="ew", pady=3)
    start_btn = ttk.Button(action_frame, text="Iniciar grabación", command=lambda: start())
    start_btn.grid(row=1, column=0, sticky="ew", pady=3)
    stop_btn = ttk.Button(action_frame, text="Detener y guardar GIF", command=lambda: recorder.stop_recording())
    stop_btn.grid(row=2, column=0, sticky="ew", pady=3)
    region_btn = ttk.Button(action_frame, text="Definir zona de grabación", command=lambda: choose_region())
    region_btn.grid(row=3, column=0, sticky="ew", pady=3)
    action_frame.columnconfigure(0, weight=1)

    status_frame = ttk.Frame(root, padding=(18, 0, 18, 12))
    status_frame.pack(fill="x")
    ttk.Separator(status_frame).pack(fill="x", pady=(0, 8))
    ttk.Label(status_frame, textvariable=status_var, wraplength=360).pack(anchor="w")
    ttk.Label(status_frame, text="Atajo: Shift + PrintScreen para detener una grabación", foreground="#666666", wraplength=360).pack(anchor="w", pady=(5, 0))

    footer = ttk.Frame(root, padding=(18, 0, 18, 16))
    footer.pack(fill="x")
    quit_btn = ttk.Button(footer, text="Salir", command=root.destroy)
    quit_btn.pack(side="right")

    def set_status(message):
        status_var.set(message)

    def set_recording_state(recording):
        screenshot_btn.configure(state="disabled" if recording else "normal")
        start_btn.configure(state="disabled" if recording else "normal")
        stop_btn.configure(state="normal" if recording else "disabled")
        region_btn.configure(state="disabled" if recording else "normal")
        duration_entry.configure(state="disabled" if recording else "normal")
        cursor_combo.configure(state="disabled" if recording else "readonly")
        click_check.configure(state="disabled" if recording else "normal")

    def finish_recording(frames):
        set_recording_state(False)
        root.deiconify()
        root.lift()
        if not frames:
            set_status("No se obtuvieron imágenes. Inténtalo de nuevo.")
            return

        file_path = filedialog.asksaveasfilename(
            parent=root,
            title="Guardar grabación",
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif")]
        )
        if not file_path:
            set_status("Grabación descartada.")
            return
        try:
            frames[0].save(file_path, save_all=True, append_images=frames[1:],
                           duration=recorder.duration, loop=0)
            set_status(f"GIF guardado: {file_path}")
        except Exception as error:
            messagebox.showerror("No se pudo guardar", f"Ocurrió un error al guardar el GIF:\n{error}", parent=root)
            set_status("No se pudo guardar la grabación.")

    recorder.set_callbacks(set_status, finish_recording)

    def choose_region():
        root.withdraw()
        selected_region = FullScreenSelector().select(root)
        root.deiconify()
        root.lift()
        if selected_region:
            recorder.record_region = selected_region
            screenshot_capture.record_region = selected_region
            region_var.set(format_region(selected_region))
            set_status("Zona actualizada. Ya puedes capturar o grabar.")
            return True
        else:
            set_status("Selección cancelada. Se conserva la zona anterior.")
            return False

    def take_screenshot():
        set_status("Selecciona el área de la captura.")
        root.withdraw()

        def select_and_save():
            selected_region = FullScreenSelector().select(root)
            if not selected_region:
                root.deiconify()
                root.lift()
                set_status("Captura cancelada. Se conserva la zona de grabación.")
                return

            screenshot_capture.record_region = selected_region
            screenshot_capture.on_closed = None
            if not screenshot_capture.capture_image():
                root.deiconify()
                root.lift()
                return

            root.deiconify()
            root.lift()
            root.update_idletasks()

            def image_saved(saved):
                set_status("Captura guardada." if saved else "Captura cancelada.")

            screenshot_capture.on_closed = image_saved
            set_status("Indica el nombre de la captura para guardarla.")
            root.after(100, screenshot_capture.save_direct_image)

        root.after(300, select_and_save)

    def start():
        try:
            duration = int(duration_entry.get())
            if not 50 <= duration <= 2000:
                raise ValueError
        except ValueError:
            messagebox.showerror("Intervalo no válido", "Usa un valor entre 50 y 2000 milisegundos.", parent=root)
            duration_entry.focus_set()
            return

        if not recorder.record_region and not choose_region():
            return

        recorder.duration = duration
        cursor_styles = {
            "Resaltado": "highlight",
            "Mano": "hand",
            "Flecha": "arrow"
        }
        recorder.set_cursor_options(
            cursor_styles[cursor_style_var.get()],
            click_blink_var.get()
        )
        set_recording_state(True)
        set_status("La grabación comenzará en 2 segundos. Mueve el cursor a la zona deseada.")
        root.withdraw()
        root.after(2000, recorder.start_recording)

    def close_app():
        recorder.stop_recording()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_app)
    set_recording_state(False)
    root.mainloop()

if __name__ == "__main__":
    main()
