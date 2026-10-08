import os
import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


LAT_FACTOR = 93206.74
LON_FACTOR = 46603.37


def hex_text(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def build_location(latitude: float, longitude: float, altitude: int) -> bytes:
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")

    if not -180.0 <= longitude <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    if not 0 <= altitude <= 65535:
        raise ValueError("Altitude must be between 0 and 65535 m.")

    # Latitude sign:
    # North = 00 00 00 00
    # South = 00 00 00 01
    lat_sign = bytes.fromhex(
        "00 00 00 00" if latitude >= 0 else "00 00 00 01"
    )

    lat_value = int(abs(latitude) * LAT_FACTOR)
    lat_bytes = struct.pack("<I", lat_value)

    lon_value = int(abs(longitude) * LON_FACTOR)

    if longitude < 0:
        # Follow Qualcomm document's West-longitude example.
        lon_value = 0xFFFFFFFF - lon_value

    lon_bytes = struct.pack("<I", lon_value)

    altitude_direction = b"\x00\x00"  # Height
    altitude_bytes = struct.pack("<H", altitude)
    reserved = bytes(44)

    data = (
        lat_sign
        + lat_bytes
        + lon_bytes
        + altitude_direction
        + altitude_bytes
        + reserved
    )

    if len(data) != 60:
        raise RuntimeError(
            f"Location EFS size error: {len(data)} bytes"
        )

    return data


def build_force_altitude(altitude: int) -> bytes:
    if not 0 <= altitude <= 0xFFFFFFFF:
        raise ValueError(
            "Force altitude must be between 0 and 4294967295 m."
        )

    data = struct.pack("<I", altitude)

    if len(data) != 4:
        raise RuntimeError(
            f"Force-altitude EFS size error: {len(data)} bytes"
        )

    return data


def build_earfcn_lock(earfcn1: int, earfcn2: int) -> bytes:
    if not 0 <= earfcn1 <= 0xFFFFFFFF:
        raise ValueError(
            "EARFCN 1 must be between 0 and 4294967295."
        )

    if not 0 <= earfcn2 <= 0xFFFFFFFF:
        raise ValueError(
            "EARFCN 2 must be between 0 and 4294967295."
        )

    data = struct.pack("<II", earfcn1, earfcn2)

    if len(data) != 8:
        raise RuntimeError(
            f"EARFCN-lock EFS size error: {len(data)} bytes"
        )

    return data


def build_pci_lock(dl_earfcn: int, pci: int) -> bytes:
    if not 0 <= dl_earfcn <= 0xFFFFFFFF:
        raise ValueError(
            "PCI-lock DL EARFCN must be between 0 and 4294967295."
        )

    if not 0 <= pci <= 503:
        raise ValueError("PCI must be between 0 and 503.")

    # Qualcomm document defines:
    # dl_earfcn: 4 bytes
    # pci:        2 bytes
    #
    # Therefore, the generated structure is 6 bytes.
    data = struct.pack("<IH", dl_earfcn, pci)

    if len(data) != 6:
        raise RuntimeError(
            f"PCI-lock EFS size error: {len(data)} bytes"
        )

    return data


def build_disable_satellite_velocity() -> bytes:
    # 1 = Disable satellite trajectory prediction
    data = b"\x01"

    if len(data) != 1:
        raise RuntimeError(
            f"Satellite-velocity EFS size error: {len(data)} bytes"
        )

    return data


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("NTN EFS File Generator")
        self.geometry("920x850")
        self.minsize(820, 700)

        # Fixed GNSS location
        self.latitude = tk.StringVar(
            value="45.71353691999299"
        )
        self.longitude = tk.StringVar(
            value="13.737700273783235"
        )
        self.altitude = tk.StringVar(value="529")

        # Optional EFS enable flags
        self.enable_force_altitude = tk.BooleanVar(value=False)
        self.enable_earfcn_lock = tk.BooleanVar(value=False)
        self.enable_pci_lock = tk.BooleanVar(value=False)
        self.enable_sat_velocity_disable = tk.BooleanVar(value=False)

        # Optional EFS input values
        self.force_altitude = tk.StringVar(value="70000")

        self.earfcn1 = tk.StringVar(value="229015")
        self.earfcn2 = tk.StringVar(value="229015")

        self.pci_dl_earfcn = tk.StringVar(value="229015")
        self.pci = tk.StringVar(value="3")

        self.output_dir = tk.StringVar(value=os.getcwd())

        self.optional_widgets = {}

        self._build_ui()
        self._update_optional_states()
        self.update_preview()

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        title = ttk.Label(
            root,
            text="NTN GNSS EFS File Generator",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        example = (
            "Fixed GNSS location EFS\n"
            "• ntn_loc_gnss_fix_efs\n"
            "• Path: /nv/item_files/modem/lte/rrc/\n"
            "• Document example: North 45.71353691999299°, "
            "East 13.737700273783235°, altitude 529 m\n\n"
            "Optional EFS files are generated only when selected."
        )

        ttk.Label(
            root,
            text=example,
            justify="left",
            foreground="#244a73",
        ).pack(anchor="w", pady=(0, 14))

        # ------------------------------------------------------------
        # Fixed GNSS location
        # ------------------------------------------------------------
        location_frame = ttk.LabelFrame(
            root,
            text="Fixed GNSS location",
            padding=12,
        )
        location_frame.pack(fill="x")

        location_fields = [
            ("Latitude (-90 to 90)", self.latitude),
            ("Longitude (-180 to 180)", self.longitude),
            ("GNSS altitude (0 to 65535 m)", self.altitude),
        ]

        for row, (label, variable) in enumerate(location_fields):
            ttk.Label(
                location_frame,
                text=label,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 12),
                pady=5,
            )

            entry = ttk.Entry(
                location_frame,
                textvariable=variable,
                width=34,
            )
            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=5,
            )
            entry.bind(
                "<KeyRelease>",
                lambda _event: self.update_preview(),
            )

        location_frame.columnconfigure(1, weight=1)

        # ------------------------------------------------------------
        # Optional EFS settings
        # ------------------------------------------------------------
        optional_frame = ttk.LabelFrame(
            root,
            text="Optional EFS settings",
            padding=12,
        )
        optional_frame.pack(fill="x", pady=(12, 0))

        # Force altitude
        force_check = ttk.Checkbutton(
            optional_frame,
            text="Force altitude over 65 km",
            variable=self.enable_force_altitude,
            command=self._optional_setting_changed,
        )
        force_check.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 4),
        )

        ttk.Label(
            optional_frame,
            text="Altitude (m)",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(24, 12),
            pady=3,
        )

        force_entry = ttk.Entry(
            optional_frame,
            textvariable=self.force_altitude,
            width=24,
        )
        force_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=3,
        )
        force_entry.bind(
            "<KeyRelease>",
            lambda _event: self.update_preview(),
        )

        self.optional_widgets["force_altitude"] = [force_entry]

        ttk.Separator(
            optional_frame,
            orient="horizontal",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=10,
        )

        # EARFCN lock
        earfcn_check = ttk.Checkbutton(
            optional_frame,
            text="EARFCN lock",
            variable=self.enable_earfcn_lock,
            command=self._optional_setting_changed,
        )
        earfcn_check.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 4),
        )

        ttk.Label(
            optional_frame,
            text="EARFCN 1",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(24, 12),
            pady=3,
        )

        earfcn1_entry = ttk.Entry(
            optional_frame,
            textvariable=self.earfcn1,
            width=24,
        )
        earfcn1_entry.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            optional_frame,
            text="EARFCN 2",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            padx=(24, 12),
            pady=3,
        )

        earfcn2_entry = ttk.Entry(
            optional_frame,
            textvariable=self.earfcn2,
            width=24,
        )
        earfcn2_entry.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=3,
        )

        earfcn1_entry.bind(
            "<KeyRelease>",
            lambda _event: self.update_preview(),
        )
        earfcn2_entry.bind(
            "<KeyRelease>",
            lambda _event: self.update_preview(),
        )

        self.optional_widgets["earfcn_lock"] = [
            earfcn1_entry,
            earfcn2_entry,
        ]

        ttk.Separator(
            optional_frame,
            orient="horizontal",
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=10,
        )

        # PCI lock
        pci_check = ttk.Checkbutton(
            optional_frame,
            text="PCI lock",
            variable=self.enable_pci_lock,
            command=self._optional_setting_changed,
        )
        pci_check.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 4),
        )

        ttk.Label(
            optional_frame,
            text="DL EARFCN",
        ).grid(
            row=8,
            column=0,
            sticky="w",
            padx=(24, 12),
            pady=3,
        )

        pci_earfcn_entry = ttk.Entry(
            optional_frame,
            textvariable=self.pci_dl_earfcn,
            width=24,
        )
        pci_earfcn_entry.grid(
            row=8,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            optional_frame,
            text="PCI (0 to 503)",
        ).grid(
            row=9,
            column=0,
            sticky="w",
            padx=(24, 12),
            pady=3,
        )

        pci_entry = ttk.Entry(
            optional_frame,
            textvariable=self.pci,
            width=24,
        )
        pci_entry.grid(
            row=9,
            column=1,
            sticky="ew",
            pady=3,
        )

        pci_earfcn_entry.bind(
            "<KeyRelease>",
            lambda _event: self.update_preview(),
        )
        pci_entry.bind(
            "<KeyRelease>",
            lambda _event: self.update_preview(),
        )

        self.optional_widgets["pci_lock"] = [
            pci_earfcn_entry,
            pci_entry,
        ]

        ttk.Separator(
            optional_frame,
            orient="horizontal",
        ).grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=10,
        )

        # Disable satellite velocity update
        sat_velocity_check = ttk.Checkbutton(
            optional_frame,
            text=(
                "Disable satellite trajectory prediction "
                "(nb1_ml1_sat_vel_upd_disable = 1)"
            ),
            variable=self.enable_sat_velocity_disable,
            command=self._optional_setting_changed,
        )
        sat_velocity_check.grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="w",
        )

        ttk.Label(
            optional_frame,
            text=(
                "Enable only for a specific lab test. "
                "Unchecked keeps the default behavior."
            ),
            foreground="#8a4b08",
        ).grid(
            row=12,
            column=0,
            columnspan=2,
            sticky="w",
            padx=(24, 0),
            pady=(3, 0),
        )

        optional_frame.columnconfigure(1, weight=1)

        # ------------------------------------------------------------
        # Output folder
        # ------------------------------------------------------------
        out = ttk.Frame(root)
        out.pack(fill="x", pady=12)

        ttk.Label(
            out,
            text="Output folder",
        ).pack(side="left")

        ttk.Entry(
            out,
            textvariable=self.output_dir,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=10,
        )

        ttk.Button(
            out,
            text="Browse",
            command=self.choose_folder,
        ).pack(side="right")

        # ------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------
        buttons = ttk.Frame(root)
        buttons.pack(fill="x", side="bottom", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Load document example",
            command=self.load_example,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Create selected files",
            command=self.create_files,
        ).pack(side="right")

        # ------------------------------------------------------------
        # Preview
        # ------------------------------------------------------------
        preview_frame = ttk.LabelFrame(
            root,
            text="Selected EFS hex preview",
            padding=10,
        )
        preview_frame.pack(fill="both", expand=True)

        preview_scroll = ttk.Scrollbar(
            preview_frame,
            orient="vertical",
        )
        preview_scroll.pack(side="right", fill="y")

        self.preview = tk.Text(
            preview_frame,
            height=12,
            wrap="word",
            font=("Consolas", 10),
            yscrollcommand=preview_scroll.set,
        )
        self.preview.pack(fill="both", expand=True)

        preview_scroll.configure(command=self.preview.yview)
        self.preview.configure(state="disabled")

    def _optional_setting_changed(self):
        self._update_optional_states()
        self.update_preview()

    def _set_widget_state(self, widgets, enabled):
        state = "normal" if enabled else "disabled"

        for widget in widgets:
            widget.configure(state=state)

    def _update_optional_states(self):
        self._set_widget_state(
            self.optional_widgets["force_altitude"],
            self.enable_force_altitude.get(),
        )

        self._set_widget_state(
            self.optional_widgets["earfcn_lock"],
            self.enable_earfcn_lock.get(),
        )

        self._set_widget_state(
            self.optional_widgets["pci_lock"],
            self.enable_pci_lock.get(),
        )

    def choose_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.output_dir.get() or os.getcwd()
        )

        if folder:
            self.output_dir.set(folder)

    def load_example(self):
        self.latitude.set("45.71353691999299")
        self.longitude.set("13.737700273783235")
        self.altitude.set("529")

        self.force_altitude.set("70000")

        self.earfcn1.set("229015")
        self.earfcn2.set("229015")

        self.pci_dl_earfcn.set("229015")
        self.pci.set("3")

        self.update_preview()

    def get_selected_files(self):
        files = {}

        # Fixed GNSS location is always generated.
        latitude = float(self.latitude.get().strip())
        longitude = float(self.longitude.get().strip())
        altitude = int(self.altitude.get().strip())

        files["ntn_loc_gnss_fix_efs"] = build_location(
            latitude,
            longitude,
            altitude,
        )

        if self.enable_force_altitude.get():
            force_altitude = int(
                self.force_altitude.get().strip()
            )

            files["ntn_force_altitude"] = build_force_altitude(
                force_altitude
            )

        if self.enable_earfcn_lock.get():
            earfcn1 = int(self.earfcn1.get().strip())
            earfcn2_text = self.earfcn2.get().strip()

            # If EARFCN 2 is empty, repeat EARFCN 1.
            earfcn2 = (
                int(earfcn2_text)
                if earfcn2_text
                else earfcn1
            )

            files["earfcn_lock"] = build_earfcn_lock(
                earfcn1,
                earfcn2,
            )

        if self.enable_pci_lock.get():
            pci_dl_earfcn = int(
                self.pci_dl_earfcn.get().strip()
            )
            pci = int(self.pci.get().strip())

            files["pci_lock"] = build_pci_lock(
                pci_dl_earfcn,
                pci,
            )

        if self.enable_sat_velocity_disable.get():
            files["nb1_ml1_sat_vel_upd_disable"] = (
                build_disable_satellite_velocity()
            )

        return files

    def update_preview(self):
        try:
            files = self.get_selected_files()
            sections = []

            for filename, data in files.items():
                sections.append(
                    f"{filename} ({len(data)} bytes)\n"
                    f"{hex_text(data)}"
                )

            text = "\n\n".join(sections)

        except Exception as exc:
            text = f"Input error: {exc}"

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def create_files(self):
        try:
            files = self.get_selected_files()

            folder = self.output_dir.get().strip()

            if not folder:
                raise ValueError("Select an output folder.")

            os.makedirs(folder, exist_ok=True)

            created_files = []

            for filename, data in files.items():
                file_path = os.path.join(folder, filename)

                with open(file_path, "wb") as output_file:
                    output_file.write(data)

                # Read back and verify.
                with open(file_path, "rb") as input_file:
                    saved_data = input_file.read()

                if saved_data != data:
                    raise IOError(
                        f"{filename} binary verification failed."
                    )

                if os.path.getsize(file_path) != len(data):
                    raise IOError(
                        f"{filename} size verification failed."
                    )

                created_files.append(
                    f"{file_path} ({len(data)} bytes)"
                )

            messagebox.showinfo(
                "Created",
                "Files created and verified:\n\n"
                + "\n".join(created_files),
            )

        except Exception as exc:
            messagebox.showerror("Error", str(exc))


if __name__ == "__main__":
    App().mainloop()