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

    # Qualcomm document format:
    # Latitude sign: 4 bytes (North=00 00 00 00, South=00 00 00 01)
    lat_sign = bytes.fromhex("00 00 00 00" if latitude >= 0 else "00 00 00 01")
    lat_value = int(abs(latitude) * LAT_FACTOR)
    lat_bytes = struct.pack("<I", lat_value)

    lon_value = int(abs(longitude) * LON_FACTOR)
    if longitude < 0:
        # Follow the document's West-longitude example: FFFFFFFF - magnitude.
        lon_value = 0xFFFFFFFF - lon_value
    lon_bytes = struct.pack("<I", lon_value)

    altitude_direction = b"\x00\x00"  # Height
    altitude_bytes = struct.pack("<H", altitude)
    reserved = bytes(44)

    data = lat_sign + lat_bytes + lon_bytes + altitude_direction + altitude_bytes + reserved
    if len(data) != 60:
        raise RuntimeError(f"Location EFS size error: {len(data)} bytes")
    return data


def build_force_altitude(altitude: int) -> bytes:
    if not 0 <= altitude <= 0xFFFFFFFF:
        raise ValueError("Force altitude must be between 0 and 4294967295 m.")
    data = struct.pack("<I", altitude)
    if len(data) != 4:
        raise RuntimeError(f"Force-altitude EFS size error: {len(data)} bytes")
    return data


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NTN EFS File Generator")
        self.geometry("860x650")
        self.minsize(760, 580)

        self.latitude = tk.StringVar(value="45.71353691999299")
        self.longitude = tk.StringVar(value="13.737700273783235")
        self.altitude = tk.StringVar(value="529")
        self.force_altitude = tk.StringVar(value="70000")
        self.output_dir = tk.StringVar(value=os.getcwd())

        self._build_ui()
        self.update_preview()

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="NTN GNSS EFS File Generator", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        example = (
            "Document examples\n"
            "• ntn_loc_gnss_fix_efs: North 45.71353691999299°, "
            "East 13.737700273783235°, altitude 529 m\n"
            "• ntn_force_altitude: force altitude 70000 m → 70 11 01 00\n"
            "• EFS paths:\n"
            "  /nv/item_files/modem/lte/rrc/ntn_loc_gnss_fix_efs\n"
            "  /nv/item_files/modem/nb1/ML1/ntn_force_altitude"
        )
        ttk.Label(root, text=example, justify="left", foreground="#244a73").pack(anchor="w", pady=(0, 14))

        form = ttk.LabelFrame(root, text="Input values", padding=12)
        form.pack(fill="x")

        fields = [
            ("Latitude (-90 to 90)", self.latitude),
            ("Longitude (-180 to 180)", self.longitude),
            ("GNSS altitude (0 to 65535 m)", self.altitude),
            ("Force altitude (m)", self.force_altitude),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            entry = ttk.Entry(form, textvariable=variable, width=34)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entry.bind("<KeyRelease>", lambda _event: self.update_preview())
        form.columnconfigure(1, weight=1)

        out = ttk.Frame(root)
        out.pack(fill="x", pady=12)
        ttk.Label(out, text="Output folder").pack(side="left")
        ttk.Entry(out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(out, text="Browse", command=self.choose_folder).pack(side="right")

        # Pack buttons before the expanding preview frame so they always stay visible,
        # even if the window is shorter than the full content height.
        buttons = ttk.Frame(root)
        buttons.pack(fill="x", side="bottom", pady=(12, 0))
        ttk.Button(buttons, text="Load document example", command=self.load_example).pack(side="left")
        ttk.Button(buttons, text="Create files", command=self.create_files).pack(side="right")

        preview_frame = ttk.LabelFrame(root, text="Hex preview", padding=10)
        preview_frame.pack(fill="both", expand=True)
        self.preview = tk.Text(preview_frame, height=14, wrap="word", font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True)
        self.preview.configure(state="disabled")

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir.get() or os.getcwd())
        if folder:
            self.output_dir.set(folder)

    def load_example(self):
        self.latitude.set("45.71353691999299")
        self.longitude.set("13.737700273783235")
        self.altitude.set("529")
        self.force_altitude.set("70000")
        self.update_preview()

    def get_data(self):
        lat = float(self.latitude.get().strip())
        lon = float(self.longitude.get().strip())
        alt = int(self.altitude.get().strip())
        force_alt = int(self.force_altitude.get().strip())
        return build_location(lat, lon, alt), build_force_altitude(force_alt)

    def update_preview(self):
        try:
            location, force = self.get_data()
            text = (
                f"ntn_loc_gnss_fix_efs ({len(location)} bytes)\n"
                f"{hex_text(location)}\n\n"
                f"ntn_force_altitude ({len(force)} bytes)\n"
                f"{hex_text(force)}"
            )
        except Exception as exc:
            text = f"Input error: {exc}"

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def create_files(self):
        try:
            location, force = self.get_data()
            folder = self.output_dir.get().strip()
            if not folder:
                raise ValueError("Select an output folder.")
            os.makedirs(folder, exist_ok=True)

            location_path = os.path.join(folder, "ntn_loc_gnss_fix_efs")
            force_path = os.path.join(folder, "ntn_force_altitude")

            with open(location_path, "wb") as file:
                file.write(location)
            with open(force_path, "wb") as file:
                file.write(force)

            # Read back and verify exact binary content and size.
            if open(location_path, "rb").read() != location or os.path.getsize(location_path) != 60:
                raise IOError("ntn_loc_gnss_fix_efs verification failed.")
            if open(force_path, "rb").read() != force or os.path.getsize(force_path) != 4:
                raise IOError("ntn_force_altitude verification failed.")

            messagebox.showinfo(
                "Created",
                "Files created and verified:\n"
                f"{location_path} (60 bytes)\n"
                f"{force_path} (4 bytes)"
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))


if __name__ == "__main__":
    App().mainloop()
