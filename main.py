import pyautogui
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageTk
import threading
import time
import ctypes
import sys
import math
import io
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


class WindowSelector:
    """Permite elegir una ventana visible de Windows como zona de captura."""
    def select_by_click(self, parent=None, on_selected=None):
        if sys.platform != "win32":
            messagebox.showinfo(
                "Función no disponible",
                "La selección de ventanas está disponible en Windows.",
                parent=parent
            )
            if on_selected:
                on_selected(None)
            return

        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class Rect(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)
            ]

        user32 = ctypes.windll.user32
        user32.WindowFromPoint.argtypes = [Point]
        user32.WindowFromPoint.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(Rect)]
        user32.GetWindowRect.restype = ctypes.c_bool
        user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        user32.IsWindowVisible.restype = ctypes.c_bool
        user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int

        selected = {"region": None}
        selection_done = threading.Event()
        clicked_point = {"value": None}
        parent_id = parent.winfo_id() if parent else None
        # La capa debe ser independiente del menú, que permanece oculto durante la selección.
        highlight = tk.Toplevel()
        highlight.overrideredirect(True)
        highlight.attributes("-topmost", True)
        highlight.attributes("-alpha", 0.22)
        highlight.configure(background="#dc2626")
        highlight.update_idletasks()

        def window_at_point(x, y):
            hwnd = user32.WindowFromPoint(Point(x, y))
            hwnd = user32.GetAncestor(hwnd, 2) if hwnd else None
            if not hwnd or hwnd == parent_id or not user32.IsWindowVisible(hwnd):
                return None
            title_length = user32.GetWindowTextLengthW(hwnd)
            if title_length == 0:
                return None
            window_rect = Rect()
            if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
                return None
            width = window_rect.right - window_rect.left
            height = window_rect.bottom - window_rect.top
            if width <= 20 or height <= 20:
                return None
            return (window_rect.left, window_rect.top, width, height)

        def on_click(x, y, _button, pressed):
            if not pressed:
                return
            clicked_point["value"] = (x, y)

        listener = mouse.Listener(on_click=on_click)
        listener.start()

        def finish_selection():
            listener.stop()
            listener.join()
            if highlight.winfo_exists():
                highlight.destroy()
            if on_selected:
                on_selected(selected["region"])

        def update_highlight():
            if selection_done.is_set():
                finish_selection()
                return

            click = clicked_point["value"]
            if click:
                highlight.withdraw()
                selected["region"] = window_at_point(*click)
                selection_done.set()
                finish_selection()
                return

            # WindowFromPoint debe ejecutarse sin el overlay visible; de lo
            # contrario Windows puede devolver la propia capa de resaltado.
            highlight.withdraw()
            x, y = pyautogui.position()
            region = window_at_point(x, y)
            if region:
                left, top, width, height = region
                highlight.geometry(f"{width}x{height}{left:+d}{top:+d}")
                highlight.deiconify()
                highlight.update_idletasks()
                highlight.lift()
            parent.after(40, update_highlight)

        update_highlight()

    def select(self, parent=None):
        if sys.platform != "win32":
            messagebox.showinfo(
                "Función no disponible",
                "La selección de ventanas está disponible en Windows.",
                parent=parent
            )
            return None

        class Rect(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)
            ]

        user32 = ctypes.windll.user32
        user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        user32.IsWindowVisible.restype = ctypes.c_bool
        user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(Rect)]
        user32.GetWindowRect.restype = ctypes.c_bool

        windows = []
        parent_id = parent.winfo_id() if parent else None

        enum_windows_callback = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )

        @enum_windows_callback
        def enum_callback(hwnd, _lparam):
            if hwnd == parent_id or not user32.IsWindowVisible(hwnd):
                return True
            title_length = user32.GetWindowTextLengthW(hwnd)
            if title_length == 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
            window_rect = Rect()
            if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
                return True
            width = window_rect.right - window_rect.left
            height = window_rect.bottom - window_rect.top
            if width > 20 and height > 20:
                windows.append((title_buffer.value, hwnd, window_rect.left,
                                window_rect.top, width, height))
            return True

        user32.EnumWindows.argtypes = [enum_windows_callback, ctypes.c_void_p]
        user32.EnumWindows.restype = ctypes.c_bool
        user32.EnumWindows(enum_callback, None)
        windows.sort(key=lambda window: window[0].lower())

        dialog = tk.Toplevel(parent) if parent else tk.Tk()
        dialog.title("Seleccionar ventana")
        dialog.geometry("560x420")
        dialog.minsize(420, 300)
        if parent:
            dialog.transient(parent)
        result = {"region": None}

        ttk.Label(
            dialog,
            text="Elegí una ventana para capturar su área completa.",
            padding=(16, 14, 16, 8)
        ).pack(fill="x")
        list_frame = ttk.Frame(dialog, padding=(16, 0, 16, 8))
        list_frame.pack(fill="both", expand=True)
        window_list = tk.Listbox(list_frame, activestyle="dotbox", selectmode="browse")
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=window_list.yview)
        window_list.configure(yscrollcommand=list_scroll.set)
        window_list.grid(row=0, column=0, sticky="nsew")
        list_scroll.grid(row=0, column=1, sticky="ns")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        for title, _hwnd, _left, _top, width, height in windows:
            window_list.insert("end", f"{title}  ({width} x {height})")
        if not windows:
            window_list.insert("end", "No se encontraron ventanas visibles")
            window_list.configure(state="disabled")

        def confirm(event=None):
            selection = window_list.curselection()
            if not selection:
                return
            _, _hwnd, left, top, width, height = windows[selection[0]]
            result["region"] = (left, top, width, height)
            dialog.destroy()

        def cancel(event=None):
            dialog.destroy()

        action_frame = ttk.Frame(dialog, padding=(16, 0, 16, 14))
        action_frame.pack(fill="x")
        ttk.Button(action_frame, text="Cancelar", command=cancel).pack(side="right")
        ttk.Button(action_frame, text="Usar ventana", command=confirm).pack(side="right", padx=(0, 8))
        window_list.bind("<Double-Button-1>", confirm)
        dialog.bind("<Return>", confirm)
        dialog.bind("<Escape>", cancel)
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.grab_set()
        dialog.focus_force()
        dialog.wait_window()
        return result["region"]

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
        self.current_color = "#dc2626"
        self.fill_rectangles = False
        self.rectangle_transparency = 72
        self.font_size = 16
        self.arrows = []
        self.ellipses = []
        self.annotation_items = {}
        self.selected_annotation = None
        self.display_scale = 1.0
        self.tool_icons = []

    def capture_and_save(self):
        if self.capture_image():
            self.show_editor()

    def capture_image(self):
        if not self.record_region:
            messagebox.showwarning("Zona no definida", "Selecciona una zona antes de capturar.", parent=self.parent)
            return False

        try:
            self.image = pyautogui.screenshot(region=self.record_region)
            # Deja la captura disponible para pegarla inmediatamente; si se
            # agregan anotaciones, save_image actualiza el contenido luego.
            self.copy_image_to_clipboard(self.image, show_error=False)
            return True
        except Exception as error:
            messagebox.showerror("No se pudo capturar", f"Ocurrió un error al capturar la pantalla:\n{error}", parent=self.parent)
            if self.on_closed:
                self.on_closed(False)
            return False

    def copy_image_to_clipboard(self, image=None, show_error=True):
        """Copia una imagen como bitmap para que Windows permita Ctrl+V."""
        if sys.platform != "win32":
            if show_error:
                messagebox.showinfo(
                    "Función no disponible",
                    "Copiar imágenes al portapapeles está disponible en Windows.",
                    parent=self.edit_window or self.parent
                )
            return False

        image = image or self.image
        if image is None:
            return False

        try:
            # pywin32 convierte el BMP al formato CF_DIB que Windows espera.
            import win32clipboard
            import win32con

            bitmap = io.BytesIO()
            image.convert("RGB").save(bitmap, format="BMP")
            dib_data = bitmap.getvalue()[14:]
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, dib_data)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as error:
            if show_error:
                messagebox.showerror(
                    "No se pudo copiar",
                    f"Ocurrió un error al copiar la imagen al portapapeles:\n{error}",
                    parent=self.edit_window or self.parent
                )
            return False

    def reset_annotations(self):
        self.rect = None
        self.rects = []
        self.text_entries = []
        self.arrows = []
        self.ellipses = []
        self.annotation_items = {}
        self.selected_annotation = None

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
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.destroy()
        self.reset_annotations()
        self.edit_window = tk.Toplevel(self.parent)
        self.edit_window.title("Editor de Captura")
        self.edit_window.resizable(True, True)
        editor_colors = {
            "background": "#2f343b",
            "surface": "#3b424b",
            "navy": "#f1f5f9",
            "muted": "#b8c1cc",
            "border": "#56606c",
            "blue": "#3678e8",
            "blue_active": "#4b8cf5",
            "red": "#b9414b",
            "red_active": "#d0525d"
        }
        editor_style = ttk.Style(self.edit_window)
        editor_style.configure("Editor.TFrame", background=editor_colors["background"])
        editor_style.configure("Editor.Toolbar.TFrame", background=editor_colors["surface"])
        editor_style.configure("Editor.Header.TLabel", background=editor_colors["background"], foreground=editor_colors["navy"], font=("Arial", 16, "bold"))
        editor_style.configure("Editor.Subtitle.TLabel", background=editor_colors["background"], foreground=editor_colors["muted"], font=("Arial", 9))
        editor_style.configure("Editor.Toolbar.TLabel", background=editor_colors["surface"], foreground=editor_colors["muted"], font=("Arial", 9, "bold"))
        editor_style.configure("Editor.Tool.TButton", padding=(10, 7), font=("Arial", 9), background=editor_colors["surface"], foreground=editor_colors["navy"])
        editor_style.map("Editor.Tool.TButton", background=[("active", "#4b5561")])
        editor_style.configure("Editor.Save.TButton", padding=(10, 7), font=("Arial", 9, "bold"), background=editor_colors["blue"], foreground="#ffffff")
        editor_style.map("Editor.Save.TButton", background=[("active", editor_colors["blue_active"])])
        editor_style.configure("Editor.Clipboard.TButton", padding=(10, 7), font=("Arial", 9, "bold"), background="#17633f", foreground="#dcfce7")
        editor_style.map("Editor.Clipboard.TButton", background=[("active", "#218052")])
        editor_style.configure("Editor.Danger.TButton", padding=(10, 7), font=("Arial", 9), background="#7f2934", foreground="#fee2e2")
        editor_style.map("Editor.Danger.TButton", background=[("active", "#a33643")])
        editor_style.configure("Editor.Status.TLabel", background=editor_colors["surface"], foreground=editor_colors["muted"], font=("Arial", 9, "italic"))
        editor_style.configure("Editor.TCombobox", fieldbackground=editor_colors["surface"], background=editor_colors["surface"], foreground=editor_colors["navy"], arrowcolor=editor_colors["navy"])
        editor_style.configure("Editor.TSpinbox", fieldbackground=editor_colors["surface"], background=editor_colors["surface"], foreground=editor_colors["navy"], arrowcolor=editor_colors["navy"])
        editor_style.configure("Editor.TCheckbutton", background=editor_colors["surface"], foreground=editor_colors["navy"], font=("Arial", 9))
        self.edit_window.configure(background=editor_colors["background"])
        self.edit_window.protocol("WM_DELETE_WINDOW", self.close_editor)
        
        img_width, img_height = self.image.size
        screen_width = self.edit_window.winfo_screenwidth()
        screen_height = self.edit_window.winfo_screenheight()
        viewport_width = max(400, min(img_width, int(screen_width * 0.82)))
        viewport_height = max(250, min(img_height, int(screen_height * 0.58)))
        self.display_scale = min(1.0, viewport_width / img_width, viewport_height / img_height)
        display_width = max(1, round(img_width * self.display_scale))
        display_height = max(1, round(img_height * self.display_scale))
        window_width = min(screen_width - 40, viewport_width + 58)
        window_height = min(screen_height - 60, viewport_height + 280)
        window_x = max(0, (screen_width - window_width) // 2)
        window_y = max(0, (screen_height - window_height) // 2)
        self.edit_window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
        self.edit_window.minsize(min(window_width, 640), min(window_height, 480))
        
        header = ttk.Frame(self.edit_window, style="Editor.TFrame", padding=(18, 14, 18, 4))
        header.pack(fill="x")
        ttk.Label(header, text="Editar captura", style="Editor.Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Anotá, ajustá y guardá la imagen cuando termines.",
            style="Editor.Subtitle.TLabel"
        ).pack(anchor="w", pady=(3, 0))

        help_label = ttk.Label(
            self.edit_window,
            text="Elegí una herramienta y arrastrá sobre la imagen. Hacé clic en una anotación para seleccionarla.",
            style="Editor.Subtitle.TLabel",
            anchor="w"
        )
        help_label.pack(fill="x", padx=18, pady=(0, 8))

        workspace = ttk.Frame(self.edit_window, style="Editor.TFrame")
        workspace.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        btn_frame = ttk.Frame(workspace, style="Editor.Toolbar.TFrame", padding=(12, 10), width=190)
        btn_frame.pack(side="left", fill="y", padx=(0, 10))
        btn_frame.pack_propagate(False)
        ttk.Label(btn_frame, text="HERRAMIENTAS", style="Editor.Toolbar.TLabel").pack(anchor="w", pady=(0, 10))
        
        color_frame = ttk.Frame(btn_frame, style="Editor.Toolbar.TFrame")
        color_frame.pack(fill="x", pady=(0, 6))
        
        ttk.Label(color_frame, text="COLOR DE ANOTACIÓN", style="Editor.Toolbar.TLabel").pack(anchor="w")
        self.editor_border = editor_colors["border"]
        self.editor_accent = editor_colors["blue"]
        self.current_color = "#dc2626"
        self.create_color_palette(color_frame)
        ttk.Label(color_frame, text="TAMAÑO DEL TEXTO", style="Editor.Toolbar.TLabel").pack(anchor="w")
        self.font_size_var = tk.StringVar(value="16")
        font_size_combo = ttk.Spinbox(
            color_frame, from_=8, to=72, increment=2,
            textvariable=self.font_size_var, width=5,
            command=self.apply_font_size, style="Editor.TSpinbox"
        )
        font_size_combo.pack(anchor="w", pady=(4, 0))
        font_size_combo.bind("<Return>", lambda event: self.apply_font_size())
        font_size_combo.bind("<FocusOut>", lambda event: self.apply_font_size())
        self.fill_rect_var = tk.BooleanVar(value=self.fill_rectangles)
        ttk.Checkbutton(
            color_frame, text="Rellenar rectángulos",
            variable=self.fill_rect_var, style="Editor.TCheckbutton",
            command=lambda: setattr(self, "fill_rectangles", self.fill_rect_var.get())
        ).pack(anchor="w", pady=(10, 0))
        ttk.Label(color_frame, text="TRANSPARENCIA DEL FONDO", style="Editor.Toolbar.TLabel").pack(anchor="w", pady=(12, 0))
        self.transparency_var = tk.DoubleVar(value=self.rectangle_transparency)
        transparency_frame = ttk.Frame(color_frame, style="Editor.Toolbar.TFrame")
        transparency_frame.pack(fill="x", pady=(4, 0))
        ttk.Scale(
            transparency_frame, from_=0, to=100, orient="horizontal",
            variable=self.transparency_var, command=self.set_rectangle_transparency,
            style="Editor.Horizontal.TScale"
        ).pack(side="left", fill="x", expand=True)
        self.transparency_value_var = tk.StringVar(value=f"{self.rectangle_transparency}%")
        ttk.Label(
            transparency_frame, textvariable=self.transparency_value_var,
            style="Editor.Toolbar.TLabel", width=4, anchor="e"
        ).pack(side="right", padx=(6, 0))
        
        tools_frame = ttk.Frame(btn_frame, style="Editor.Toolbar.TFrame")
        tools_frame.pack(fill="x")

        rect_btn = self.create_tool_button(tools_frame, "Rectángulo", "rectangle", self.enable_rectangle_mode)
        rect_btn.pack(fill="x", pady=2)

        ellipse_btn = self.create_tool_button(tools_frame, "Círculo", "ellipse", self.enable_ellipse_mode)
        ellipse_btn.pack(fill="x", pady=2)

        arrow_btn = self.create_tool_button(tools_frame, "Flecha", "arrow", self.enable_arrow_mode)
        arrow_btn.pack(fill="x", pady=2)

        text_btn = self.create_tool_button(tools_frame, "Texto", "text", self.enable_text_mode)
        text_btn.pack(fill="x", pady=2)

        edit_btn = self.create_tool_button(tools_frame, "Editar texto", "edit", self.edit_selected)
        edit_btn.pack(fill="x", pady=2)
        delete_btn = self.create_tool_button(tools_frame, "Eliminar", "delete", self.delete_selected, "Editor.Danger.TButton")
        delete_btn.pack(fill="x", pady=(12, 2))
        clear_btn = self.create_tool_button(tools_frame, "Limpiar todo", "clear", self.clear_all_annotations, "Editor.Danger.TButton")
        clear_btn.pack(fill="x", pady=2)
        clipboard_btn = self.create_tool_button(tools_frame, "Copiar imagen", "clipboard", self.copy_edited_image, "Editor.Clipboard.TButton")
        clipboard_btn.pack(fill="x", pady=2)
        save_btn = self.create_tool_button(tools_frame, "Guardar", "save", self.save_image, "Editor.Save.TButton")
        save_btn.pack(fill="x", pady=2)

        self.mode_var = tk.StringVar()
        ttk.Label(btn_frame, textvariable=self.mode_var, anchor="w", wraplength=160, style="Editor.Status.TLabel").pack(fill="x", pady=(12, 0))

        canvas_frame = ttk.Frame(workspace, style="Editor.Toolbar.TFrame", padding=8)
        canvas_frame.pack(side="left", fill="both", expand=True)
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.drawing_canvas = tk.Canvas(
            canvas_frame, width=min(viewport_width, display_width), height=min(viewport_height, display_height),
            background="white", highlightthickness=1,
            highlightbackground=editor_colors["border"],
            xscrollincrement=1, yscrollincrement=1
        )
        horizontal_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.drawing_canvas.xview)
        vertical_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.drawing_canvas.yview)
        self.drawing_canvas.configure(
            xscrollcommand=horizontal_scroll.set,
            yscrollcommand=vertical_scroll.set,
            scrollregion=(0, 0, display_width, display_height)
        )
        self.drawing_canvas.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        
        preview = self.image.resize((display_width, display_height), Image.Resampling.LANCZOS) \
            if self.display_scale < 1.0 else self.image
        self.photo = ImageTk.PhotoImage(preview)
        self.drawing_canvas.create_image(0, 0, anchor="nw", image=self.photo)
        
        self.drawing_canvas.bind("<ButtonPress-1>", self.start_draw)
        self.drawing_canvas.bind("<B1-Motion>", self.drawing)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.end_draw)
        
        self.drawing_canvas.tag_bind("draggable", "<ButtonPress-1>", self.start_drag)
        self.drawing_canvas.tag_bind("draggable", "<B1-Motion>", self.drag)
        self.drawing_canvas.tag_bind("draggable", "<ButtonRelease-1>", self.stop_drag)
        
        self.mode = "rect"
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.enable_rectangle_mode()
        self.edit_window.bind("<Control-s>", lambda event: self.save_image())

    def create_tool_button(self, parent, text, icon_name, command, style="Editor.Tool.TButton"):
        icon = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        ink = "#d8e0ea"

        if icon_name == "rectangle":
            draw.rectangle((3, 4, 17, 16), outline=ink, width=2)
        elif icon_name == "ellipse":
            draw.ellipse((3, 4, 17, 16), outline=ink, width=2)
        elif icon_name == "arrow":
            draw.line((3, 16, 15, 4), fill=ink, width=2)
            draw.polygon((10, 4, 17, 3, 16, 10), fill=ink)
        elif icon_name == "text":
            draw.line((3, 4, 17, 4), fill=ink, width=2)
            draw.line((10, 4, 10, 17), fill=ink, width=2)
            draw.line((6, 17, 14, 17), fill=ink, width=2)
        elif icon_name == "edit":
            draw.line((4, 16, 15, 5), fill=ink, width=3)
            draw.polygon((13, 3, 17, 7, 16, 9, 12, 5), fill=ink)
            draw.line((3, 17, 7, 16), fill=ink, width=2)
        elif icon_name == "delete":
            draw.rectangle((5, 6, 15, 17), outline="#fecdd3", width=2)
            draw.line((4, 4, 16, 4), fill="#fecdd3", width=2)
            draw.line((8, 2, 12, 2), fill="#fecdd3", width=2)
            draw.line((8, 9, 8, 15), fill="#fecdd3", width=1)
            draw.line((12, 9, 12, 15), fill="#fecdd3", width=1)
        elif icon_name == "clear":
            draw.polygon([(5, 6), (13, 6), (13, 12), (5, 12)], outline="#fecdd3", width=2)
            draw.polygon([(6, 12), (12, 12), (11, 16), (7, 16)], fill="#fecdd3")
        elif icon_name == "clipboard":
            draw.rectangle((5, 4, 15, 18), outline="#bbf7d0", width=2)
            draw.rectangle((8, 2, 12, 6), fill="#bbf7d0")
            draw.line((8, 10, 12, 10), fill="#bbf7d0", width=1)
            draw.line((8, 14, 12, 14), fill="#bbf7d0", width=1)
        elif icon_name == "save":
            draw.rectangle((3, 3, 17, 17), outline="white", width=2)
            draw.rectangle((6, 4, 14, 9), outline="white", width=1)
            draw.rectangle((7, 12, 13, 16), outline="white", width=1)

        image = ImageTk.PhotoImage(icon)
        self.tool_icons.append(image)
        return ttk.Button(parent, text=text, image=image, compound="left", command=command, style=style)

    def enable_rectangle_mode(self):
        self.mode = "rect"
        if hasattr(self, "mode_var"):
            self.mode_var.set("Herramienta activa: rectángulo. Arrastra sobre la imagen.")

    def set_rectangle_transparency(self, value):
        self.rectangle_transparency = round(float(value))
        if hasattr(self, "transparency_value_var"):
            self.transparency_value_var.set(f"{self.rectangle_transparency}%")

    def create_color_palette(self, parent):
        """Paleta de muestras de color + selector nativo de color."""
        self.palette_colors = [
            "#dc2626", "#2563eb", "#16a34a", "#facc15", "#0f172a",
            "#f1f5f9", "#a855f7", "#f97316"
        ]
        self.swatch_buttons = {}
        self.palette_grid = ttk.Frame(parent, style="Editor.Toolbar.TFrame")
        self.palette_grid.pack(fill="x", pady=(4, 6))
        for column in range(5):
            self.palette_grid.grid_columnconfigure(column, weight=1, uniform="swatch")
        for index, color in enumerate(self.palette_colors):
            self.add_swatch(index, color)
        ttk.Button(
            parent, text="Más colores…", style="Editor.Tool.TButton",
            command=self.pick_custom_color
        ).pack(fill="x", pady=(0, 10))
        self.set_current_color("#dc2626")

    def add_swatch(self, index, color):
        frame = tk.Frame(
            self.palette_grid, bg="#3b424b", bd=0,
            highlightthickness=2, highlightbackground=self.editor_border
        )
        frame.grid(row=index // 5, column=index % 5, padx=2, pady=2, ipadx=1, ipady=1, sticky="nsew")
        tk.Button(
            frame, bg=color, activebackground=color, bd=0, relief="flat",
            width=2, height=1, cursor="hand2",
            command=lambda selected=color: self.set_current_color(selected)
        ).pack(fill="both", expand=True, padx=1, pady=1)
        self.swatch_buttons[color] = frame

    def set_current_color(self, color):
        self.current_color = color
        self.show_color_palette()

    def show_color_palette(self):
        if not hasattr(self, "swatch_buttons"):
            return
        for color, frame in self.swatch_buttons.items():
            selected = color.lower() == self.current_color.lower()
            frame.configure(
                highlightbackground=self.editor_accent if selected else self.editor_border,
                highlightthickness=2 if selected else 1
            )

    def pick_custom_color(self):
        rgb, hex_color = colorchooser.askcolor(
            color=self.current_color, title="Elegir color",
            parent=self.edit_window
        )
        if hex_color is None:
            return
        hex_color = hex_color.lower()
        if hex_color not in self.swatch_buttons:
            self.palette_colors.append(hex_color)
            self.add_swatch(len(self.palette_colors) - 1, hex_color)
        self.set_current_color(hex_color)
        self.mode_var.set(f"Color aplicado: {hex_color}")

    def select_annotation(self, item):
        if item in self.annotation_items:
            self.selected_annotation = item
            kind, index = self.annotation_items[item]
            if kind == "texto" and hasattr(self, "font_size_var"):
                self.font_size_var.set(str(self.text_entries[index][5]))
            self.mode_var.set(f"Seleccionado: {kind}. Puedes moverlo o eliminarlo.")

    def enable_text_mode(self):
        self.mode = "text"
        if hasattr(self, "mode_var"):
            self.mode_var.set("Herramienta activa: texto. Haz clic en la imagen.")

    def enable_ellipse_mode(self):
        self.mode = "ellipse"
        if hasattr(self, "mode_var"):
            self.mode_var.set("Herramienta activa: círculo. Arrastra sobre la imagen.")

    def enable_arrow_mode(self):
        self.mode = "arrow"
        if hasattr(self, "mode_var"):
            self.mode_var.set("Herramienta activa: flecha. Arrastra desde el origen hasta el destino.")

    def canvas_position(self, event):
        return self.drawing_canvas.canvasx(event.x), self.drawing_canvas.canvasy(event.y)

    def image_position(self, x, y):
        return x / self.display_scale, y / self.display_scale

    def display_position(self, x, y):
        return x * self.display_scale, y * self.display_scale

    def start_draw(self, event):
        canvas_x, canvas_y = self.canvas_position(event)
        current_item = self.drawing_canvas.find_withtag("current")
        if current_item and current_item[0] in self.annotation_items:
            self.select_annotation(current_item[0])
            self.drag_data["item"] = current_item[0]
            self.drag_data["x"] = canvas_x
            self.drag_data["y"] = canvas_y
            return

        self.start_x, self.start_y = canvas_x, canvas_y
        if self.mode == "rect":
            rectangle_options = {
                "outline": self.current_color,
                "width": 3,
                "tags": ("annotation",)
            }
            if self.fill_rectangles:
                stipple = "gray12" if self.rectangle_transparency >= 75 else "gray25"
                if self.rectangle_transparency < 50:
                    stipple = "gray50"
                if self.rectangle_transparency < 25:
                    stipple = "gray75"
                rectangle_options.update(fill=self.current_color, stipple=stipple)
            self.rect = self.drawing_canvas.create_rectangle(
                self.start_x, self.start_y, self.start_x, self.start_y,
                **rectangle_options
            )
        elif self.mode == "ellipse":
            self.rect = self.drawing_canvas.create_oval(self.start_x, self.start_y, self.start_x, self.start_y, outline=self.current_color, width=3, tags=("annotation",))
        elif self.mode == "arrow":
            self.rect = self.drawing_canvas.create_line(
                self.start_x, self.start_y, self.start_x, self.start_y,
                fill=self.current_color, width=3, arrow=tk.LAST, arrowshape=(16, 20, 6),
                tags=("annotation",)
            )
        elif self.mode == "text":
            self.show_text_input(canvas_x, canvas_y)

    def drawing(self, event):
        if self.mode in ("rect", "ellipse", "arrow") and self.rect:
            canvas_x, canvas_y = self.canvas_position(event)
            self.drawing_canvas.coords(self.rect, self.start_x, self.start_y, canvas_x, canvas_y)

    def end_draw(self, event):
        if self.mode in ("rect", "ellipse", "arrow") and self.rect:
            x2, y2 = self.canvas_position(event)
            x1, y1 = self.start_x, self.start_y
            if self.mode == "rect":
                fill = self.fill_rectangles
                image_x1, image_y1 = self.image_position(x1, y1)
                image_x2, image_y2 = self.image_position(x2, y2)
                self.rects.append((min(image_x1, image_x2), min(image_y1, image_y2), abs(image_x2-image_x1), abs(image_y2-image_y1), self.current_color, fill, self.rectangle_transparency))
                self.annotation_items[self.rect] = ("rectángulo", len(self.rects) - 1)
            elif self.mode == "ellipse":
                image_x1, image_y1 = self.image_position(x1, y1)
                image_x2, image_y2 = self.image_position(x2, y2)
                self.ellipses.append((min(image_x1, image_x2), min(image_y1, image_y2), abs(image_x2-image_x1), abs(image_y2-image_y1), self.current_color))
                self.annotation_items[self.rect] = ("círculo", len(self.ellipses) - 1)
            else:
                image_x1, image_y1 = self.image_position(x1, y1)
                image_x2, image_y2 = self.image_position(x2, y2)
                self.arrows.append((image_x1, image_y1, image_x2, image_y2, self.current_color))
                self.annotation_items[self.rect] = ("flecha", len(self.arrows) - 1)
            self.rect = None

    def start_drag(self, event):
        item = self.drawing_canvas.find_withtag("current")
        if item and item[0] in self.annotation_items:
            self.select_annotation(item[0])
            canvas_x, canvas_y = self.canvas_position(event)
            self.drag_data["item"] = item[0]
            self.drag_data["x"] = canvas_x
            self.drag_data["y"] = canvas_y

    def drag(self, event):
        if self.drag_data["item"]:
            canvas_x, canvas_y = self.canvas_position(event)
            dx = canvas_x - self.drag_data["x"]
            dy = canvas_y - self.drag_data["y"]
            self.drawing_canvas.move(self.drag_data["item"], dx, dy)
            self.drag_data["x"] = canvas_x
            self.drag_data["y"] = canvas_y

    def stop_drag(self, event):
        if self.drag_data["item"]:
            coords = self.drawing_canvas.coords(self.drag_data["item"])
            item = self.drag_data["item"]
            kind, index = self.annotation_items.get(item, (None, None))
            if kind == "texto":
                _, _, text, color, text_id, size = self.text_entries[index]
                image_x, image_y = self.image_position(coords[0], coords[1])
                self.text_entries[index] = (image_x, image_y, text, color, text_id, size)
            elif kind == "rectángulo":
                image_x1, image_y1 = self.image_position(coords[0], coords[1])
                image_x2, image_y2 = self.image_position(coords[2], coords[3])
                self.rects[index] = (min(image_x1, image_x2), min(image_y1, image_y2), abs(image_x2 - image_x1), abs(image_y2 - image_y1), self.rects[index][4], self.rects[index][5], self.rects[index][6])
            elif kind == "círculo":
                image_x1, image_y1 = self.image_position(coords[0], coords[1])
                image_x2, image_y2 = self.image_position(coords[2], coords[3])
                self.ellipses[index] = (min(image_x1, image_x2), min(image_y1, image_y2), abs(image_x2 - image_x1), abs(image_y2 - image_y1), self.ellipses[index][4])
            elif kind == "flecha":
                image_x1, image_y1 = self.image_position(coords[0], coords[1])
                image_x2, image_y2 = self.image_position(coords[2], coords[3])
                self.arrows[index] = (image_x1, image_y1, image_x2, image_y2, self.arrows[index][4])
            self.drag_data["item"] = None

    def delete_selected(self):
        item = self.selected_annotation
        if not item or item not in self.annotation_items:
            self.mode_var.set("No hay ninguna anotación seleccionada.")
            return

        kind, index = self.annotation_items.pop(item)
        self.drawing_canvas.delete(item)
        collections = {
            "rectángulo": self.rects,
            "círculo": self.ellipses,
            "flecha": self.arrows,
            "texto": self.text_entries
        }
        collections[kind].pop(index)
        self.annotation_items = {
            item_id: (item_kind, item_index - (item_kind == kind and item_index > index))
            for item_id, (item_kind, item_index) in self.annotation_items.items()
        }
        self.selected_annotation = None
        self.mode_var.set("Anotación eliminada.")

    def clear_all_annotations(self):
        for item in list(self.annotation_items):
            self.drawing_canvas.delete(item)
        self.rects = []
        self.text_entries = []
        self.arrows = []
        self.ellipses = []
        self.annotation_items = {}
        self.selected_annotation = None
        self.rect = None
        if hasattr(self, "mode_var"):
            self.mode_var.set("Todas las anotaciones eliminadas.")

    def show_text_input(self, x, y, edit_item=None):
        input_win = tk.Toplevel(self.edit_window)
        input_win.title("Agregar Texto")
        input_win.geometry("300x100")
        input_win.transient(self.edit_window)
        input_win.grab_set()
        
        tk.Label(input_win, text="Texto:").pack(pady=5)
        text_entry = tk.Entry(input_win, width=40)
        text_entry.pack(pady=5)
        if edit_item in self.annotation_items:
            _, index = self.annotation_items[edit_item]
            text_entry.insert(0, self.text_entries[index][2])
        
        def add_text():
            text = text_entry.get()
            if text:
                if edit_item in self.annotation_items:
                    _, index = self.annotation_items[edit_item]
                    _, _, _, color, text_id, size = self.text_entries[index]
                    self.drawing_canvas.itemconfigure(edit_item, text=text)
                    self.text_entries[index] = (x, y, text, color, text_id, size)
                else:
                    image_x, image_y = self.image_position(x, y)
                    display_x, display_y = self.display_position(image_x, image_y)
                    text_id = self.drawing_canvas.create_text(
                        display_x, display_y, text=text, fill=self.current_color,
                        font=("Arial", self.font_size, "bold"), tags=("draggable", "annotation"),
                        anchor="nw"
                    )
                    self.text_entries.append((image_x, image_y, text, self.current_color, text_id, self.font_size))
                    self.annotation_items[text_id] = ("texto", len(self.text_entries) - 1)
            input_win.destroy()

        actions = tk.Frame(input_win)
        actions.pack(pady=5)
        tk.Button(actions, text="Agregar", command=add_text).pack(side="left", padx=4)
        tk.Button(actions, text="Cancelar", command=input_win.destroy).pack(side="left", padx=4)
        input_win.bind("<Return>", lambda event: add_text())
        input_win.bind("<Escape>", lambda event: input_win.destroy())
        input_win.protocol("WM_DELETE_WINDOW", input_win.destroy)
        text_entry.focus()

    def edit_selected(self):
        item = self.selected_annotation
        if not item or item not in self.annotation_items:
            self.mode_var.set("Selecciona primero una anotación de texto.")
            return
        kind, index = self.annotation_items[item]
        if kind != "texto":
            self.mode_var.set("Solo se puede editar el contenido de un texto.")
            return
        x, y, _, _, _, _ = self.text_entries[index]
        self.show_text_input(x, y, edit_item=item)

    def apply_font_size(self):
        try:
            size = int(self.font_size_var.get())
            if not 8 <= size <= 72:
                raise ValueError
        except (TypeError, ValueError):
            self.font_size_var.set(str(self.font_size))
            return

        self.font_size = size
        item = self.selected_annotation
        if item in self.annotation_items and self.annotation_items[item][0] == "texto":
            _, index = self.annotation_items[item]
            x, y, text, color, text_id, _ = self.text_entries[index]
            self.text_entries[index] = (x, y, text, color, text_id, size)
            self.drawing_canvas.itemconfigure(item, font=("Arial", size, "bold"))
            self.mode_var.set(f"Texto actualizado a {size} px.")

    def close_editor(self, saved=False):
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.destroy()
        if self.on_closed:
            self.on_closed(saved)

    def save_image(self):
        edit_img = self.render_edited_image()
        
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
            self.copy_image_to_clipboard(edit_img)
            self.close_editor(saved=True)

    def copy_edited_image(self):
        if self.copy_image_to_clipboard(self.render_edited_image()):
            self.mode_var.set("Imagen copiada. Ahora podés pegarla con Ctrl + V.")

    def render_edited_image(self):
        edit_img = self.image.copy()

        fill_layer = Image.new("RGBA", edit_img.size, (0, 0, 0, 0))
        fill_draw = ImageDraw.Draw(fill_layer)
        for rx, ry, rw, rh, color, filled, transparency in self.rects:
            if filled:
                fill_draw.rectangle(
                    [rx, ry, rx + rw, ry + rh],
                    fill=ImageColor.getrgb(color) + (round(255 * (100 - transparency) / 100),)
                )
        edit_img = Image.alpha_composite(edit_img.convert("RGBA"), fill_layer).convert("RGB")
        draw = ImageDraw.Draw(edit_img)

        for rx, ry, rw, rh, color, _filled, _transparency in self.rects:
            draw.rectangle([rx, ry, rx + rw, ry + rh], outline=color, width=3)

        for ex, ey, ew, eh, color in self.ellipses:
            draw.ellipse([ex, ey, ex + ew, ey + eh], outline=color, width=3)

        for x1, y1, x2, y2, color in self.arrows:
            self.draw_arrow(draw, x1, y1, x2, y2, color)

        for tx, ty, text, color, text_id, size in self.text_entries:
            draw.text((tx, ty), text, fill=color, font=self.get_text_font(size))

        return edit_img

    def get_text_font(self, size):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default(size=size)

    def draw_arrow(self, draw, x1, y1, x2, y2, color):
        draw.line((x1, y1, x2, y2), fill=color, width=3)
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_length = 16
        arrow_width = math.pi / 6
        left = (
            x2 - arrow_length * math.cos(angle - arrow_width),
            y2 - arrow_length * math.sin(angle - arrow_width)
        )
        right = (
            x2 - arrow_length * math.cos(angle + arrow_width),
            y2 - arrow_length * math.sin(angle + arrow_width)
        )
        draw.polygon([(x2, y2), left, right], fill=color)

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
    screenshot_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
    start_btn = ttk.Button(action_frame, text="Iniciar grabación GIF", style="Secondary.TButton", command=lambda: start())
    start_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)
    stop_btn = ttk.Button(action_frame, text="Detener y guardar GIF", style="Danger.TButton", command=lambda: recorder.stop_recording())
    stop_btn.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)
    region_btn = ttk.Button(action_frame, text="Definir zona de grabación", style="Secondary.TButton", command=lambda: choose_region())
    region_btn.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)
    window_btn = ttk.Button(action_frame, text="Seleccionar ventana con mouse", style="Secondary.TButton", command=lambda: choose_window_by_click())
    window_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=3)
    action_frame.columnconfigure(0, weight=1)
    action_frame.columnconfigure(1, weight=1)

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
        window_btn.configure(state="disabled" if recording else "normal")
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

    def choose_window():
        selected_region = WindowSelector().select(root)
        root.lift()
        if selected_region:
            recorder.record_region = selected_region
            screenshot_capture.record_region = selected_region
            region_var.set(format_region(selected_region))
            set_status("Ventana seleccionada. Ya puedes capturar o grabar.")
        else:
            set_status("Selección de ventana cancelada. Se conserva la zona anterior.")

    def choose_window_by_click():
        messagebox.showinfo(
            "Seleccionar ventana",
            "Después de cerrar este aviso, hacé clic sobre la ventana que querés capturar.",
            parent=root
        )
        root.withdraw()

        def window_selected(selected_region):
            root.deiconify()
            root.lift()
            if selected_region:
                recorder.record_region = selected_region
                screenshot_capture.record_region = selected_region
                region_var.set(format_region(selected_region))
                set_status("Ventana seleccionada. Ya puedes capturar o grabar.")
            else:
                set_status("No se pudo seleccionar una ventana. Se conserva la zona anterior.")

        WindowSelector().select_by_click(root, window_selected)

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
            def image_saved(saved):
                set_status("Captura guardada." if saved else "Captura cancelada.")

            screenshot_capture.on_closed = image_saved
            if not screenshot_capture.capture_image():
                root.deiconify()
                root.lift()
                return

            root.deiconify()
            root.lift()
            screenshot_capture.show_editor()
            set_status("Edita la captura y pulsa Guardar cuando termines.")

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
