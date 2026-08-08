import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import ctypes
import sys
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
    """Clase para grabar GIF usando el cursor configurado en el sistema."""
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
        self.click_blink = True
        self.show_typed_text = False
        self.typed_text_duration = 1000
        self.cursor_cache_handle = None
        self.cursor_cache_image = None
        self.cursor_cache_hotspot = (0, 0)
        self.typed_text = ""
        self.typed_text_until = 0
        self.typed_text_lock = threading.Lock()
        self.pressed_modifiers = set()
        self.modifier_labels = {}
        for key_name, label in (
            ("ctrl_l", "Ctrl"), ("ctrl_r", "Ctrl"),
            ("shift_l", "Shift"), ("shift_r", "Shift"),
            ("alt_l", "Alt"), ("alt_r", "Alt"),
            ("alt_gr", "AltGr"), ("cmd", "Win"),
            ("cmd_l", "Win"), ("cmd_r", "Win")
        ):
            key_value = getattr(keyboard.Key, key_name, None)
            if key_value is not None:
                self.modifier_labels[key_value] = label

    def set_root(self, root):
        self.root = root

    def set_callbacks(self, status_callback=None, finished_callback=None):
        self.status_callback = status_callback
        self.finished_callback = finished_callback

    def set_cursor_options(self, click_blink=True, show_typed_text=False, typed_text_duration=1000):
        self.click_blink = click_blink
        self.show_typed_text = show_typed_text
        self.typed_text_duration = typed_text_duration

    def notify(self, message):
        if self.status_callback:
            if self.root:
                self.root.after(0, lambda: self.status_callback(message))
            else:
                self.status_callback(message)

    def on_key_press(self, key):
        modifier = self.modifier_labels.get(key)
        if modifier:
            self.pressed_modifiers.add(modifier)
            if modifier == "Shift":
                self.shift_pressed = True
        elif key == keyboard.Key.print_screen and self.shift_pressed:
            self.stop_recording()
        elif self.show_typed_text:
            self.update_typed_text(key)

    def on_key_release(self, key):
        modifier = self.modifier_labels.get(key)
        if modifier:
            self.pressed_modifiers.discard(modifier)
            if modifier == "Shift":
                self.shift_pressed = False

    def key_label(self, key):
        char = getattr(key, "char", None)
        if char and char.isprintable():
            return char

        virtual_key = getattr(key, "vk", None)
        if virtual_key is not None:
            if 65 <= virtual_key <= 90:
                return chr(virtual_key)
            if 48 <= virtual_key <= 57:
                return chr(virtual_key)
            if 112 <= virtual_key <= 123:
                return f"F{virtual_key - 111}"

        special_labels = {
            keyboard.Key.f1: "F1", keyboard.Key.f2: "F2",
            keyboard.Key.f3: "F3", keyboard.Key.f4: "F4",
            keyboard.Key.f5: "F5", keyboard.Key.f6: "F6",
            keyboard.Key.f7: "F7", keyboard.Key.f8: "F8",
            keyboard.Key.f9: "F9", keyboard.Key.f10: "F10",
            keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
            keyboard.Key.esc: "Esc", keyboard.Key.home: "Home",
            keyboard.Key.end: "End", keyboard.Key.page_up: "PageUp",
            keyboard.Key.page_down: "PageDown", keyboard.Key.insert: "Insert",
            keyboard.Key.up: "Up", keyboard.Key.down: "Down",
            keyboard.Key.left: "Left", keyboard.Key.right: "Right",
            keyboard.Key.caps_lock: "CapsLock"
        }
        return special_labels.get(key)

    def update_typed_text(self, key):
        with self.typed_text_lock:
            token = None
            if self.pressed_modifiers:
                key_name = self.key_label(key)
                if key_name:
                    if len(key_name) == 1 and key_name.isalpha():
                        key_name = key_name.upper()
                    modifier_order = ["Ctrl", "Alt", "AltGr", "Shift", "Win"]
                    modifiers = [name for name in modifier_order if name in self.pressed_modifiers]
                    token = " + ".join(modifiers + [key_name])
            elif key == keyboard.Key.space:
                token = "Space"
            elif key == keyboard.Key.enter:
                token = "Enter"
            elif key == keyboard.Key.tab:
                token = "Tab"
            elif key == keyboard.Key.backspace:
                token = "Backspace"
            elif key == keyboard.Key.delete:
                token = "Delete"
            else:
                token = self.key_label(key)

            if token:
                self.typed_text = token
                self.typed_text_until = time.monotonic() + self.typed_text_duration / 1000

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
        try:
            system_cursor = self.get_system_cursor()
        except Exception:
            system_cursor = None
        if system_cursor:
            cursor_image, x, y, hotspot_x, hotspot_y = system_cursor
            overlay.paste(
                cursor_image,
                (x - left - hotspot_x, y - top - hotspot_y),
                cursor_image
            )
        else:
            # Fallback para sistemas que no exponen un cursor como imagen.
            draw = ImageDraw.Draw(overlay)
            cursor_x, cursor_y = x - left, y - top
            draw.ellipse(
                (cursor_x - 12, cursor_y - 12, cursor_x + 12, cursor_y + 12),
                fill=(255, 0, 0, 150)
            )

        draw = ImageDraw.Draw(overlay)
        cursor_x, cursor_y = x - left, y - top
        click_elapsed = self.click_effect()

        if click_elapsed is not None:
            blink_on = int(click_elapsed / 0.1) % 2 == 0
            if blink_on:
                pulse_radius = 22 + int(min(click_elapsed, 0.4) * 35)
                draw.ellipse(
                    (cursor_x - pulse_radius, cursor_y - pulse_radius,
                     cursor_x + pulse_radius, cursor_y + pulse_radius),
                    outline=(255, 220, 0, 240), width=4
                )

        self.draw_typed_text(draw, cursor_x, cursor_y, overlay.size)

    def get_system_cursor(self):
        """Obtiene el cursor visible de Windows junto con su punto activo."""
        if sys.platform != "win32":
            return None

        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class CursorInfo(ctypes.Structure):
            _fields_ = [
                ("size", ctypes.c_uint), ("flags", ctypes.c_uint),
                ("cursor", ctypes.c_void_p), ("position", Point)
            ]

        class IconInfo(ctypes.Structure):
            _fields_ = [
                ("fIcon", ctypes.c_int), ("xHotspot", ctypes.c_uint),
                ("yHotspot", ctypes.c_uint), ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p)
            ]

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [
                ("size", ctypes.c_uint), ("width", ctypes.c_long),
                ("height", ctypes.c_long), ("planes", ctypes.c_ushort),
                ("bit_count", ctypes.c_ushort), ("compression", ctypes.c_uint),
                ("image_size", ctypes.c_uint), ("x_pixels_per_meter", ctypes.c_long),
                ("y_pixels_per_meter", ctypes.c_long), ("colors_used", ctypes.c_uint),
                ("colors_important", ctypes.c_uint)
            ]

        class BitmapInfo(ctypes.Structure):
            _fields_ = [("header", BitmapInfoHeader), ("colors", ctypes.c_uint * 3)]

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        user32.GetCursorInfo.argtypes = [ctypes.POINTER(CursorInfo)]
        user32.GetCursorInfo.restype = ctypes.c_bool
        user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(IconInfo)]
        user32.GetIconInfo.restype = ctypes.c_bool
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.DrawIconEx.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint
        ]
        user32.DrawIconEx.restype = ctypes.c_bool
        gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
        gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
        gdi32.CreateDIBSection.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(BitmapInfo), ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.c_uint
        ]
        gdi32.CreateDIBSection.restype = ctypes.c_void_p
        gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        gdi32.SelectObject.restype = ctypes.c_void_p
        gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
        gdi32.DeleteObject.restype = ctypes.c_bool
        gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
        gdi32.DeleteDC.restype = ctypes.c_bool
        cursor_info = CursorInfo(ctypes.sizeof(CursorInfo))
        if not user32.GetCursorInfo(ctypes.byref(cursor_info)) or not cursor_info.cursor:
            return None

        if cursor_info.cursor == self.cursor_cache_handle and self.cursor_cache_image:
            hotspot_x, hotspot_y = self.cursor_cache_hotspot
            return (self.cursor_cache_image, cursor_info.position.x,
                    cursor_info.position.y, hotspot_x, hotspot_y)

        icon_info = IconInfo()
        if not user32.GetIconInfo(cursor_info.cursor, ctypes.byref(icon_info)):
            return None

        width = user32.GetSystemMetrics(13) or 32
        height = user32.GetSystemMetrics(14) or 32
        bitmap_info = BitmapInfo()
        bitmap_info.header = BitmapInfoHeader(
            ctypes.sizeof(BitmapInfoHeader), width, -height, 1, 32, 0,
            width * height * 4, 0, 0, 0, 0
        )
        bits = ctypes.c_void_p()
        device_context = gdi32.CreateCompatibleDC(None)
        bitmap = gdi32.CreateDIBSection(
            device_context, ctypes.byref(bitmap_info), 0,
            ctypes.byref(bits), None, 0
        )
        if not device_context or not bitmap or not bits:
            if icon_info.hbmMask:
                gdi32.DeleteObject(icon_info.hbmMask)
            if icon_info.hbmColor:
                gdi32.DeleteObject(icon_info.hbmColor)
            return None

        previous_bitmap = gdi32.SelectObject(device_context, bitmap)
        try:
            if not user32.DrawIconEx(device_context, 0, 0, cursor_info.cursor,
                                     width, height, 0, None, 3):
                return None
            raw = ctypes.string_at(bits, width * height * 4)
            image = Image.frombuffer("RGBA", (width, height), raw, "raw", "BGRA", 0, 1).copy()
            self.cursor_cache_handle = cursor_info.cursor
            self.cursor_cache_image = image
            self.cursor_cache_hotspot = (icon_info.xHotspot, icon_info.yHotspot)
            return image, cursor_info.position.x, cursor_info.position.y, icon_info.xHotspot, icon_info.yHotspot
        finally:
            gdi32.SelectObject(device_context, previous_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(device_context)
            if icon_info.hbmMask:
                gdi32.DeleteObject(icon_info.hbmMask)
            if icon_info.hbmColor:
                gdi32.DeleteObject(icon_info.hbmColor)

    def draw_typed_text(self, draw, cursor_x, cursor_y, image_size):
        if not self.show_typed_text:
            return
        with self.typed_text_lock:
            if time.monotonic() >= self.typed_text_until:
                return
            text = self.typed_text
        if not text:
            return

        font = ImageFont.load_default(size=18)
        text = text[-40:]
        text_bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=2)
        padding = 5
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = cursor_x + 25
        text_y = cursor_y + 25
        if text_x + text_width + padding * 2 > image_size[0]:
            text_x = max(padding, cursor_x - text_width - 25)
        if text_y + text_height + padding * 2 > image_size[1]:
            text_y = max(padding, cursor_y - text_height - 25)

        draw.rounded_rectangle(
            (text_x, text_y, text_x + text_width + padding * 2,
             text_y + text_height + padding * 2),
            radius=4, fill=(0, 0, 0, 200)
        )
        draw.multiline_text(
            (text_x + padding, text_y + padding), text,
            font=font, fill=(255, 255, 255, 255), spacing=2
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
        except Exception as error:
            self.notify(f"La grabación se detuvo por un error de captura: {error}")
            self.stop_recording()

    def start_recording(self):
        if not self.record_region:
            self.notify("Selecciona una zona antes de grabar.")
            return False
        if self.recording:
            return False
        self.frames = []
        with self.typed_text_lock:
            self.typed_text = ""
            self.typed_text_until = 0
        self.pressed_modifiers.clear()
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
    root.geometry("500x720")
    root.resizable(False, False)

    colors = {
        "canvas": "#f1f5f9",
        "surface": "#ffffff",
        "navy": "#0f172a",
        "blue": "#2563eb",
        "blue_active": "#1d4ed8",
        "red": "#dc2626",
        "red_active": "#b91c1c",
        "text": "#1e293b",
        "muted": "#64748b",
        "border": "#dbe3ee",
        "status": "#eff6ff"
    }
    root.configure(background=colors["canvas"])
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("App.TFrame", background=colors["canvas"])
    style.configure("Header.TFrame", background=colors["navy"])
    style.configure("Brand.TLabel", background=colors["navy"], foreground="white", font=("Arial", 22, "bold"))
    style.configure("Eyebrow.TLabel", background=colors["navy"], foreground="#93c5fd", font=("Arial", 9, "bold"))
    style.configure("HeaderSub.TLabel", background=colors["navy"], foreground="#cbd5e1", font=("Arial", 10))
    style.configure("Card.TLabelframe", background=colors["surface"], bordercolor=colors["border"], relief="solid", borderwidth=1)
    style.configure("Card.TLabelframe.Label", background=colors["surface"], foreground=colors["navy"], font=("Arial", 10, "bold"))
    style.configure("Card.TLabel", background=colors["surface"], foreground=colors["text"], font=("Arial", 10))
    style.configure("Muted.TLabel", background=colors["surface"], foreground=colors["muted"], font=("Arial", 9))
    style.configure("Card.TCheckbutton", background=colors["surface"], foreground=colors["text"], font=("Arial", 10))
    style.configure("Status.TFrame", background=colors["status"])
    style.configure("Status.TLabel", background=colors["status"], foreground=colors["text"], font=("Arial", 10))
    style.configure("StatusMuted.TLabel", background=colors["status"], foreground=colors["muted"], font=("Arial", 9))
    style.configure("Primary.TButton", background=colors["blue"], foreground="white", padding=(14, 10), font=("Arial", 10, "bold"), borderwidth=0)
    style.map("Primary.TButton", background=[("active", colors["blue_active"]), ("disabled", "#cbd5e1")], foreground=[("disabled", "#64748b")])
    style.configure("Secondary.TButton", background=colors["surface"], foreground=colors["text"], padding=(14, 9), font=("Arial", 10), borderwidth=1)
    style.map("Secondary.TButton", background=[("active", "#f8fafc"), ("disabled", "#e2e8f0")], foreground=[("disabled", "#94a3b8")])
    style.configure("Danger.TButton", background=colors["red"], foreground="white", padding=(14, 9), font=("Arial", 10, "bold"), borderwidth=0)
    style.map("Danger.TButton", background=[("active", colors["red_active"]), ("disabled", "#cbd5e1")], foreground=[("disabled", "#64748b")])

    recorder = GifRecorder(None)
    recorder.set_root(root)

    status_var = tk.StringVar(value="Elige Capturar imagen o Iniciar grabación para comenzar.")
    region_var = tk.StringVar()

    def format_region(selected_region):
        x, y, width, height = selected_region
        return f"{width} x {height} px  (posición: {x}, {y})"

    region_var.set("No definida. Se solicitará al iniciar una grabación.")

    header = ttk.Frame(root, style="Header.TFrame", padding=(28, 20, 28, 20))
    header.pack(fill="x")
    ttk.Label(header, text="SCREEN CAPTURE TOOL", style="Eyebrow.TLabel").pack(anchor="w")
    ttk.Label(header, text="ScreenPar", style="Brand.TLabel").pack(anchor="w", pady=(3, 0))
    ttk.Label(header, text="Captura imágenes y crea GIFs de forma sencilla", style="HeaderSub.TLabel").pack(anchor="w", pady=(3, 0))

    region_frame = ttk.LabelFrame(root, text="Zona de grabación", style="Card.TLabelframe", padding=12)
    region_frame.pack(fill="x", padx=24, pady=(16, 10))
    ttk.Label(region_frame, textvariable=region_var, style="Card.TLabel", wraplength=420).pack(side="left", fill="x", expand=True)

    controls = ttk.LabelFrame(root, text="Configuración del GIF", style="Card.TLabelframe", padding=12)
    controls.pack(fill="x", padx=24, pady=(0, 10))
    ttk.Label(controls, text="Intervalo entre imágenes (ms):", style="Card.TLabel").grid(row=0, column=0, sticky="w")
    duration_entry = ttk.Spinbox(controls, from_=50, to=2000, increment=10, width=8)
    duration_entry.set("200")
    duration_entry.grid(row=0, column=1, padx=(10, 0), sticky="w")
    ttk.Label(controls, text="Menor valor = más fluidez", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    cursor_frame = ttk.LabelFrame(root, text="Cursor y teclado", style="Card.TLabelframe", padding=12)
    cursor_frame.pack(fill="x", padx=24, pady=(0, 10))
    ttk.Label(cursor_frame, text="Se usa el cursor predeterminado del sistema.", style="Card.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    click_blink_var = tk.BooleanVar(value=True)
    click_check = ttk.Checkbutton(
        cursor_frame,
        text="Parpadear al hacer clic",
        variable=click_blink_var,
        style="Card.TCheckbutton"
    )
    click_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 0))
    show_typed_text_var = tk.BooleanVar(value=True)
    show_typed_text_check = ttk.Checkbutton(
        cursor_frame,
        text="Mostrar teclas junto al cursor",
        variable=show_typed_text_var,
        style="Card.TCheckbutton"
    )
    show_typed_text_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
    ttk.Label(cursor_frame, text="Mostrar teclas durante (ms):", style="Card.TLabel").grid(
        row=3, column=0, sticky="w", pady=(7, 0)
    )
    typed_text_duration_entry = ttk.Spinbox(
        cursor_frame, from_=100, to=5000, increment=100, width=8
    )
    typed_text_duration_entry.set("1000")
    typed_text_duration_entry.grid(row=3, column=1, padx=(10, 0), sticky="w", pady=(7, 0))

    action_frame = ttk.LabelFrame(root, text="Acciones", style="Card.TLabelframe", padding=12)
    action_frame.pack(fill="x", padx=24, pady=(0, 10))

    screenshot_capture = ScreenshotCapture(None, parent=root)

    screenshot_btn = ttk.Button(action_frame, text="Capturar imagen", style="Primary.TButton", command=lambda: take_screenshot())
    screenshot_btn.grid(row=0, column=0, sticky="ew", pady=3)
    start_btn = ttk.Button(action_frame, text="Iniciar grabación GIF", style="Secondary.TButton", command=lambda: start())
    start_btn.grid(row=1, column=0, sticky="ew", pady=3)
    stop_btn = ttk.Button(action_frame, text="Detener y guardar GIF", style="Danger.TButton", command=lambda: recorder.stop_recording())
    stop_btn.grid(row=2, column=0, sticky="ew", pady=3)
    region_btn = ttk.Button(action_frame, text="Definir zona de grabación", style="Secondary.TButton", command=lambda: choose_region())
    region_btn.grid(row=3, column=0, sticky="ew", pady=3)
    action_frame.columnconfigure(0, weight=1)

    status_frame = ttk.Frame(root, style="Status.TFrame", padding=(14, 11))
    status_frame.pack(fill="x", padx=24, pady=(0, 10))
    ttk.Label(status_frame, text="ESTADO", style="StatusMuted.TLabel").pack(anchor="w")
    ttk.Label(status_frame, textvariable=status_var, style="Status.TLabel", wraplength=420).pack(anchor="w", pady=(3, 0))
    ttk.Label(status_frame, text="Atajo de grabación: Shift + PrintScreen", style="StatusMuted.TLabel", wraplength=420).pack(anchor="w", pady=(5, 0))

    footer = ttk.Frame(root, style="App.TFrame", padding=(24, 0, 24, 18))
    footer.pack(fill="x")
    quit_btn = ttk.Button(footer, text="Salir", style="Secondary.TButton", command=lambda: close_app())
    quit_btn.pack(side="right")

    def set_status(message):
        status_var.set(message)

    def set_recording_state(recording):
        screenshot_btn.configure(state="disabled" if recording else "normal")
        start_btn.configure(state="disabled" if recording else "normal")
        stop_btn.configure(state="normal" if recording else "disabled")
        region_btn.configure(state="disabled" if recording else "normal")
        duration_entry.configure(state="disabled" if recording else "normal")
        click_check.configure(state="disabled" if recording else "normal")
        show_typed_text_check.configure(state="disabled" if recording else "normal")
        typed_text_duration_entry.configure(state="disabled" if recording else "normal")

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

    def choose_region(show_main=True):
        root.withdraw()
        selected_region = FullScreenSelector().select(root)
        if show_main:
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

        try:
            typed_text_duration = int(typed_text_duration_entry.get())
            if not 100 <= typed_text_duration <= 5000:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Duración no válida",
                "Usa un valor entre 100 y 5000 milisegundos.",
                parent=root
            )
            typed_text_duration_entry.focus_set()
            return

        if not recorder.record_region and not choose_region(show_main=False):
            return

        recorder.duration = duration
        recorder.set_cursor_options(
            click_blink_var.get(),
            show_typed_text_var.get(),
            typed_text_duration
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
    root.update_idletasks()
    screen_x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    screen_y = (root.winfo_screenheight() - root.winfo_height()) // 2
    root.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{screen_x}+{screen_y}")
    root.mainloop()

if __name__ == "__main__":
    main()
