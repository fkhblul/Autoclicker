import tkinter as tk
from tkinter import ttk, messagebox
import yaml
import os
import time
import threading
from pynput import mouse, keyboard

CONFIG_FILE = 'config.yaml'


class AutoClickerApp:
    def __init__(self, root):
        """
        The constructor for the class. Builds the entire application.
        'root' is the main window (tk.Tk()).
        """
        self.root = root
        self.root.title("AutoClicker")
        self.root.resizable(False, False)

        # --- SET WINDOW ICON ---
        icon_path = os.path.join(os.path.dirname(__file__), '.\\assets', 'pc-mouse.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                print(f"Warning: Could not load icon '{icon_path}'. Ensure it's a valid .ico file.")
                # Fallback for other platforms or if .ico fails (e.g., trying .png)
                # You could try .png here if you have one:
                try:
                    photo = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), 'assets', 'pc-mouse.png'))
                    self.root.iconphoto(True, photo)
                except tk.TclError:
                    print("Warning: Could not load .png icon either.")
        else:
            print(f"Warning: Icon file not found at '{icon_path}'")

        # --- Core Logic ---
        self.mouse_controller = mouse.Controller()
        self.running_event = threading.Event()  # Signal to stop the thread
        self.clicker_thread = None
        self.hotkey_listener = None

        # --- UI Element References ---
        self.start_button = None
        self.stop_button = None

        # 1. Initialize all state variables
        self._init_variables()

        # 2. Create the menu
        self._create_menu()

        # 3. Create all widgets (UI elements)
        self._create_widgets()

        # 4. Load settings on startup
        self.load_settings()

        # 5. Start the hotkey listener
        self.start_hotkey_listener()

        # 6. Ensure a clean exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _init_variables(self):
        """Initializes all tk variables as instance attributes."""
        self.hours_var = tk.IntVar(value=0)
        self.minutes_var = tk.IntVar(value=0)
        self.seconds_var = tk.IntVar(value=0)
        self.millis_var = tk.IntVar(value=100)
        self.repeat_var = tk.IntVar(value=0)  # 0 = Infinite, 1 = Times
        self.repeat_times_var = tk.IntVar(value=1)
        self.position_var = tk.IntVar(value=0)  # 0 = Current, 1 = X/Y
        self.pos_x_var = tk.IntVar(value=0)
        self.pos_y_var = tk.IntVar(value=0)
        self.button_var = tk.StringVar(value="Left")
        self.type_var = tk.StringVar(value="Single")
        self.top_most_var = tk.BooleanVar(value=False)
        self.top_most_var.trace_add("write", self._toggle_top_most)

    def _create_menu(self):
        """Creates the top menu bar."""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Help")
        menu_bar.add_cascade(label="Help", menu=help_menu)
        menu_bar.add_command(label="Exit", command=self.on_exit)

    def _create_widgets(self):
        """Creates all UI elements in the main window."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- 1. Click Interval ---
        lf_interval = ttk.LabelFrame(main_frame, text="Click Interval", padding="10")
        lf_interval.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        # (Spinboxes and Labels...)
        ttk.Spinbox(lf_interval, from_=0, to=999, width=5, textvariable=self.hours_var).grid(row=0, column=0,
                                                                                             padx=(0, 2))
        ttk.Label(lf_interval, text="hours").grid(row=0, column=1, padx=(0, 10))
        ttk.Spinbox(lf_interval, from_=0, to=59, width=5, textvariable=self.minutes_var).grid(row=0, column=2,
                                                                                              padx=(0, 2))
        ttk.Label(lf_interval, text="minutes").grid(row=0, column=3, padx=(0, 10))
        ttk.Spinbox(lf_interval, from_=0, to=59, width=5, textvariable=self.seconds_var).grid(row=0, column=4,
                                                                                              padx=(0, 2))
        ttk.Label(lf_interval, text="seconds").grid(row=0, column=5, padx=(0, 10))
        ttk.Spinbox(lf_interval, from_=0, to=999, width=5, textvariable=self.millis_var).grid(row=0, column=6,
                                                                                              padx=(0, 2))
        ttk.Label(lf_interval, text="milliseconds").grid(row=0, column=7)

        # --- 2. Click Repeat ---
        lf_repeat = ttk.LabelFrame(main_frame, text="Click Repeat", padding="10")
        lf_repeat.grid(row=1, column=0, sticky="ns", pady=5, padx=(0, 5))
        ttk.Radiobutton(lf_repeat, text="Infinite (Until stopped)", variable=self.repeat_var, value=0).pack(anchor="w")
        repeat_times_frame = ttk.Frame(lf_repeat)
        repeat_times_frame.pack(anchor="w")
        ttk.Radiobutton(repeat_times_frame, variable=self.repeat_var, value=1).pack(side="left")
        ttk.Spinbox(repeat_times_frame, from_=0, to=99999, width=7, textvariable=self.repeat_times_var).pack(
            side="left", padx=2)
        ttk.Label(repeat_times_frame, text="Times").pack(side="left")

        # --- 3. Click Position ---
        lf_position = ttk.LabelFrame(main_frame, text="Click Position", padding="10")
        lf_position.grid(row=1, column=1, sticky="ns", pady=5, padx=(5, 0))
        ttk.Radiobutton(lf_position, text="Current Cursor Position", variable=self.position_var, value=0).pack(
            anchor="w")
        position_xy_frame = ttk.Frame(lf_position)
        position_xy_frame.pack(anchor="w")
        ttk.Radiobutton(position_xy_frame, variable=self.position_var, value=1).pack(side="left")
        ttk.Label(position_xy_frame, text="X").pack(side="left", padx=(5, 2))
        ttk.Spinbox(position_xy_frame, from_=0, to=9999, width=5, textvariable=self.pos_x_var).pack(side="left")
        ttk.Label(position_xy_frame, text="Y").pack(side="left", padx=(5, 2))
        ttk.Spinbox(position_xy_frame, from_=0, to=9999, width=5, textvariable=self.pos_y_var).pack(side="left")
        # 'Pick Location'-Button
        ttk.Button(position_xy_frame, text="🎯", width=2, command=self._pick_location).pack(side="left", padx=5)

        # --- 4. Click Options ---
        lf_options = ttk.LabelFrame(main_frame, text="Click Options", padding="10")
        lf_options.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(lf_options, text="Mouse Button").grid(row=0, column=0, padx=(0, 5), sticky="w")
        cb_button = ttk.Combobox(lf_options, values=["Left", "Right", "Middle"], width=10, textvariable=self.button_var,
                                 state="readonly")
        cb_button.grid(row=0, column=1, padx=(0, 15))
        ttk.Label(lf_options, text="Click Type").grid(row=0, column=2, padx=(0, 5), sticky="w")
        cb_type = ttk.Combobox(lf_options, values=["Single", "Double"], width=10, textvariable=self.type_var,
                               state="readonly")
        cb_type.grid(row=0, column=3)

        # --- 5. Buttons ---
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.start_button = ttk.Button(buttons_frame, text="Start (F6)", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(buttons_frame, text="Stop (F7)", command=self.stop_clicking, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)

        ttk.Button(buttons_frame, text="Toggle (F8)", command=self.toggle_clicking).grid(row=0, column=2, padx=5)

        ttk.Button(buttons_frame, text="Save Settings", command=self.save_settings).grid(row=1, column=0, padx=5,
                                                                                         pady=5)
        ttk.Button(buttons_frame, text="Hotkeys", command=self.show_hotkey_info).grid(row=1, column=1, padx=5, pady=5)

        # --- 6. Top most window ---
        ttk.Checkbutton(main_frame, text="Top most window", variable=self.top_most_var).grid(row=4, column=1,
                                                                                             sticky="e", pady=5)

    def _toggle_top_most(self, *args):
        """Sets the window to "Always on Top"."""
        self.root.attributes("-topmost", self.top_most_var.get())

    # --- 7. Core Functions (Start, Stop, Toggle) ---

    def start_clicking(self):
        """Starts the clicking thread."""
        if self.running_event.is_set():
            return  # Already running

        self.running_event.set()

        # Gather settings *before* starting the thread
        self.current_settings = self._gather_settings()

        self.clicker_thread = threading.Thread(target=self._clicker_loop, daemon=True)
        self.clicker_thread.start()

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.root.title("AutoClicker (RUNNING...)")

    def stop_clicking(self):
        """Stops the clicking thread."""
        self.running_event.clear()  # Send stop signal to the thread

        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.root.title("AutoClicker")

    def toggle_clicking(self):
        """Toggles between Start and Stop."""
        if self.running_event.is_set():
            self.stop_clicking()
        else:
            self.start_clicking()

    def _gather_settings(self):
        """Gathers all settings from the UI into a dictionary."""
        # Use safe-get for spinboxes
        h = self._safe_get_int(self.hours_var)
        m = self._safe_get_int(self.minutes_var)
        s = self._safe_get_int(self.seconds_var)
        ms = self._safe_get_int(self.millis_var, default=100)

        interval = (h * 3600) + (m * 60) + s + (ms / 1000)
        if interval <= 0:
            interval = 0.01  # Prevent zero division / too-fast clicking

        return {
            'interval': interval,
            'repeat_mode': self.repeat_var.get(),  # Radio is safe
            'repeat_times': self._safe_get_int(self.repeat_times_var, default=1),
            'pos_mode': self.position_var.get(),  # Radio is safe
            'x': self._safe_get_int(self.pos_x_var),
            'y': self._safe_get_int(self.pos_y_var),
            'button': self.button_var.get(),  # Combobox is safe
            'type': self.type_var.get()  # Combobox is safe
        }

    def _clicker_loop(self):
        """The actual clicking loop (runs in a thread)."""
        settings = self.current_settings

        # Parse settings
        button_map = {"Left": mouse.Button.left, "Right": mouse.Button.right, "Middle": mouse.Button.middle}
        click_button = button_map.get(settings['button'], mouse.Button.left)
        click_count = 2 if settings['type'] == 'Double' else 1

        is_infinite = settings['repeat_mode'] == 0
        repeat_count = settings['repeat_times']

        loop_counter = 0

        while self.running_event.is_set():
            # 1. Check position
            if settings['pos_mode'] == 1:  # X/Y
                self.mouse_controller.position = (settings['x'], settings['y'])

            # 2. Click
            self.mouse_controller.click(click_button, click_count)

            # 3. Check repetition
            if not is_infinite:
                loop_counter += 1
                if loop_counter >= repeat_count:
                    break  # End loop

            # 4. Wait
            time.sleep(settings['interval'])

        # When the loop ends (either by stop or by count),
        # safely call stop_clicking() in the main thread.
        self.root.after(0, self.stop_clicking)

    # --- 8. Hotkeys and Helper Functions ---

    def start_hotkey_listener(self):
        """Starts the global hotkey listener in its own thread."""
        try:
            self.hotkey_listener = keyboard.Listener(on_press=self._on_hotkey_press)
            self.hotkey_listener.start()
        except Exception as e:
            print(f"Error starting hotkey listener: {e}")
            messagebox.showwarning("Hotkey Error",
                                   "Could not register hotkeys. Are you running as admin?\n"
                                   f"Error: {e}")

    def _on_hotkey_press(self, key):
        """Callback for the hotkey listener (runs in the listener thread)."""
        try:
            if key == keyboard.Key.f6:
                self.root.after(0, self.start_clicking)
            elif key == keyboard.Key.f7:
                self.root.after(0, self.stop_clicking)
            elif key == keyboard.Key.f8:
                self.root.after(0, self.toggle_clicking)
        except AttributeError:
            pass  # Ignore regular keys

    def _pick_location(self):
        """Starts the 'Pick Location' mode."""
        self.root.title("AutoClicker - PICK LOCATION (CLICK)")

        # Start a temporary mouse listener
        # It will stop itself once a click is detected.
        def on_pick(x, y, button, pressed):
            if pressed:
                # Set values safely in the main thread
                self.root.after(0, self.pos_x_var.set, x)
                self.root.after(0, self.pos_y_var.set, y)
                self.root.after(0, self.position_var.set, 1)  # Switch to X/Y
                self.root.after(0, self.root.title, "AutoClicker")
                return False  # Stops the listener

        mouse_listener = mouse.Listener(on_click=on_pick)
        mouse_listener.start()

    def show_hotkey_info(self):
        """Shows an info box with the hotkeys."""
        messagebox.showinfo("Hotkeys",
                            "The global hotkeys are:\n\n"
                            "F6: Start\n"
                            "F7: Stop\n"
                            "F8: Toggle (Start/Stop)"
                            )

    def on_exit(self):
        """Called when the window is closed."""
        self.running_event.clear()  # Stop clicking thread
        if self.hotkey_listener:
            self.hotkey_listener.stop()  # Stop hotkey thread
        self.root.quit()  # Exit Tkinter

    # --- 9. Save & Load ---

    def _safe_get_int(self, var, default=0):
        """
        Safely get an int value from a tk.Variable.
        Catches TclError (e.g., if text is in a spinbox).
        """
        try:
            return var.get()
        except tk.TclError:
            print(f"Invalid value in a spinbox. Using default: {default}")
            var.set(default)  # Reset the faulty field to the default
            return default

    def save_settings(self):
        """Gathers all values and saves them to a YAML file."""

        # Safe-gets for all spinboxes
        hours = self._safe_get_int(self.hours_var)
        minutes = self._safe_get_int(self.minutes_var)
        seconds = self._safe_get_int(self.seconds_var)
        millis = self._safe_get_int(self.millis_var, default=100)
        repeat_times = self._safe_get_int(self.repeat_times_var, default=1)
        pos_x = self._safe_get_int(self.pos_x_var)
        pos_y = self._safe_get_int(self.pos_y_var)

        config_data = {
            'click_interval': {
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'milliseconds': millis
            },
            'click_repeat': {
                'mode': self.repeat_var.get(),
                'times': repeat_times
            },
            'click_position': {
                'mode': self.position_var.get(),
                'x': pos_x,
                'y': pos_y
            },
            'click_options': {
                'mouse_button': self.button_var.get(),
                'click_type': self.type_var.get()
            },
            'top_most': self.top_most_var.get()
        }

        try:
            with open(CONFIG_FILE, 'w') as file:
                yaml.dump(config_data, file, sort_keys=False)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save settings:\n{e}")

    def load_settings(self):
        """Loads settings from the YAML file and sets the UI values."""
        if not os.path.exists(CONFIG_FILE):
            print("No config.yaml found. Using default values.")
            self._toggle_top_most()  # Apply default (false)
            return

        try:
            with open(CONFIG_FILE, 'r') as file:
                config = yaml.safe_load(file)

            if not config:
                return

            # Click Interval
            interval_cfg = config.get('click_interval', {})
            self.hours_var.set(interval_cfg.get('hours', 0))
            self.minutes_var.set(interval_cfg.get('minutes', 0))
            self.seconds_var.set(interval_cfg.get('seconds', 0))
            self.millis_var.set(interval_cfg.get('milliseconds', 100))

            # Click Repeat
            repeat_cfg = config.get('click_repeat', {})
            self.repeat_var.set(repeat_cfg.get('mode', 0))
            self.repeat_times_var.set(repeat_cfg.get('times', 1))

            # Click Position
            position_cfg = config.get('click_position', {})
            self.position_var.set(position_cfg.get('mode', 0))
            self.pos_x_var.set(position_cfg.get('x', 0))
            self.pos_y_var.set(position_cfg.get('y', 0))

            # Click Options
            options_cfg = config.get('click_options', {})
            self.button_var.set(options_cfg.get('mouse_button', 'Left'))
            self.type_var.set(options_cfg.get('click_type', 'Single'))

            # Top Most
            self.top_most_var.set(config.get('top_most', False))

            print(f"Settings loaded from {CONFIG_FILE}.")

        except Exception as e:
            messagebox.showwarning("Load Error", f"Could not load {CONFIG_FILE}:\n{e}")


# --- The "main" Program ---
# This block only runs if the file is started directly as a script.

if __name__ == "__main__":
    # 1. Create the main window
    root_window = tk.Tk()

    # 2. Create an instance of our application class
    app = AutoClickerApp(root_window)

    # 3. Start the event loop (waits for clicks, etc.)
    root_window.mainloop()