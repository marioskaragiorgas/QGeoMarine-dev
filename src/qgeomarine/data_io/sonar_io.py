# qgeomarine/data_io/sonar_io.py
"""
Side-scan sonar (XTF) reader + normalized SQLite schema + binary amplitude store.

Overview
========
This module ingests an XTF file (via `pyxtf`), extracts metadata and ping-level
navigation/attitude, *and* writes amplitude samples to a compact binary file
(`.bin`). The SQLite database stores only metadata and an index that maps each
(ping, channel) to a row in the `.bin` file. Amplitudes are never stored in the DB.

Design goals
------------
- **Normalized schema**: file-level, channel-info, ping, ping-channel, and binfile
  are separated for clarity and future extension.
- **Fast sequential I/O**: amplitudes are written once as an interleaved matrix:
  even rows = Port, odd rows = Starboard, all rows have equal (padded) length.
- **Memory-friendly**: amplitudes are read back as `numpy.memmap` (no full load).
- **Explicit mapping**: each (ping, channel) stores its `row_idx` in the BIN.

Interleaved layout
------------------
Let `P = #pings`, `N = #samples per row (padded)`. The `.bin` file stores a 2D
array of shape `(2*P, N)`:

    row 0 -> Port ping 0
    row 1 -> Stbd ping 0
    row 2 -> Port ping 1
    row 3 -> Stbd ping 1
    ...
    row 2*i   -> Port ping i
    row 2*i+1 -> Stbd ping i

Schema (tables)
---------------
- `xtf_file`          : one row per XTF source file.
- `xtf_channel_info`  : one row per sonar channel (as reported by XTF header).
- `xtf_ping`          : one row per ping (time + nav + attitude).
- `xtf_ping_channel`  : one row per (ping, channel) with padded samples count,
                        sample interval, bytes-per-sample in BIN, `row_idx`.
- `xtf_binfile`       : path + dtype + layout + matrix dimensions for the BIN.

Typical usage
-------------
    xtf = XTF(db_file_path="out/my_survey.sqlite", bin_file_path="out/my_survey.bin")
    xtf.load_data_xtf("input/my_line.xtf", store_dtype="float32")
    port = xtf.load_pings_from_bin("port")  # shape = (P, N), memmap view
    stbd = xtf.load_pings_from_bin("stbd")

    # quicklook
    xtf.export_image_mosaic("out/quicklook.png", channel="port")

Notes
-----
- Only ONE frequency pair (Port/Stbd) is written per load. The pair is chosen
  based on channel names (e.g., "Port100"/"Stbd100") and a preference list.
- To store multiple frequencies, call `load_data_xtf` again with a different
  `bin_file_path` and the same DB, or create separate DB/BIN pairs.


"""

from __future__ import annotations

import sys
import sqlite3
import logging
from pathlib import Path
import numpy as np
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)

@dataclass
class BinMeta:
    bin_id: int
    bin_path: str
    rows: int
    cols: int
    dtype: str
    layout: str
    channel_group: str

class XTF:
    """
    Side-Scan Sonar ingest for XTF files.

    Parameters
    ----------
    db_file_path : str
        Path to the SQLite database that will hold the metadata and BIN index.
    bin_file_path : str
        Path to the binary file where amplitude samples will be stored.

    Attributes
    ----------
    n_pings : int | None
        Ping count for the currently loaded line (set after writing BIN).
    n_samples : int | None
        Padded samples per row for the currently loaded line (set after writing BIN).
    dtype : str
        BIN dtype ("float32" or "uint16").
    layout : str
        BIN layout string (currently "interleaved_even_port_odd_stbd").
    """

    def __init__(self, db_file_path: str, bin_file_path: str):
        self.db_file_path = db_file_path
        self.bin_file_path = bin_file_path
        self.n_pings: int | None = None
        self.n_samples: int | None = None
        self.dtype: str = "float32"       # default internal dtype
        self.layout: str = "interleaved"  # human hint; final layout string set on write

    # ---------------------------------------------------------------------
    # Schema
    # ---------------------------------------------------------------------
    def create_database(self) -> None:
        """
        Create the normalized XTF schema (idempotent).

        Adds integrity indexes, including unique constraints on
        (file_id, chan_index), (file_id, ping_index), and (file_id, ping_id, chan_index).
        """
        DDL = """
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS xtf_file (
            file_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            src_path           TEXT NOT NULL,
            created_utc        TEXT DEFAULT (datetime('now')),
            file_format        INTEGER,
            system_type        INTEGER,
            recording_program  TEXT,
            recording_version  TEXT,
            sonar_name         TEXT,
            sonar_type         INTEGER,
            note_string        TEXT,
            nav_units          INTEGER,
            num_sonar_channels INTEGER,
            num_bathy_channels INTEGER,
            num_snippet_channels INTEGER,
            num_forwardlook_arrays INTEGER,
            num_echo_strength_channels INTEGER,
            num_interferometry_channels INTEGER,
            spheroid_type      TEXT,
            projection_type    TEXT,
            origin_x           REAL, origin_y REAL,
            nav_offset_x       REAL, nav_offset_y REAL, nav_offset_z REAL, nav_offset_yaw REAL,
            mru_offset_x       REAL, mru_offset_y REAL, mru_offset_z REAL, mru_offset_yaw REAL, mru_offset_pitch REAL, mru_offset_roll REAL
        );

        CREATE TABLE IF NOT EXISTS xtf_channel_info (
            chan_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id           INTEGER NOT NULL REFERENCES xtf_file(file_id) ON DELETE CASCADE,
            chan_index        INTEGER NOT NULL,         -- 0..N-1 in fh.sonar_info order
            channel_name      TEXT,                     -- e.g. "Port100"
            type_of_channel   INTEGER,
            subchannel_number INTEGER,
            correction_flags  INTEGER,
            unipolar          INTEGER,
            bytes_per_sample  INTEGER,
            volt_scale        REAL,
            frequency_hz      REAL,
            horiz_beam_angle  REAL,
            tilt_angle        REAL,
            beam_width        REAL,
            offset_x          REAL, offset_y REAL, offset_z REAL,
            offset_yaw        REAL, offset_pitch REAL, offset_roll REAL,
            beams_per_array   INTEGER,
            sample_format     INTEGER
        );

        CREATE TABLE IF NOT EXISTS xtf_ping (
            ping_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id       INTEGER NOT NULL REFERENCES xtf_file(file_id) ON DELETE CASCADE,
            ping_index    INTEGER NOT NULL,     -- 0..n_pings-1
            t_utc         TEXT NOT NULL,
            julian_day    INTEGER,
            ping_number   INTEGER,
            ship_speed    REAL,
            ship_heading  REAL,
            ship_lon      REAL,
            ship_lat      REAL,
            sensor_depth  REAL,
            sensor_altitude REAL,
            sensor_pitch  REAL,
            sensor_roll   REAL,
            sensor_heading REAL,
            layback       REAL,
            cable_out     REAL
        );

        -- No amplitude samples here; only per-(ping, channel) info and BIN row mapping.
        CREATE TABLE IF NOT EXISTS xtf_ping_channel (
            pc_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id          INTEGER NOT NULL REFERENCES xtf_file(file_id) ON DELETE CASCADE,
            ping_id          INTEGER NOT NULL REFERENCES xtf_ping(ping_id) ON DELETE CASCADE,
            chan_index       INTEGER NOT NULL,       -- matches xtf_channel_info.chan_index
            samples          INTEGER NOT NULL,       -- padded length written to BIN
            sample_int_sec   REAL,                   -- seconds
            bytes_per_sample INTEGER,                -- bytes in BIN row (e.g., 4 for float32)
            slant_range_m    REAL,
            row_idx          INTEGER NOT NULL        -- row number in BIN for this (ping,chan)
        );

        CREATE TABLE IF NOT EXISTS xtf_binfile (
            bin_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id    INTEGER NOT NULL REFERENCES xtf_file(file_id) ON DELETE CASCADE,
            bin_path   TEXT NOT NULL,
            dtype      TEXT NOT NULL,                -- "float32" or "uint16"
            layout     TEXT NOT NULL,                -- "interleaved_even_port_odd_stbd"
            rows       INTEGER NOT NULL,             -- total rows in bin
            cols       INTEGER NOT NULL,             -- samples per row (padded)
            channel_group TEXT                       -- e.g., "100" or "500"
        );

        CREATE INDEX IF NOT EXISTS idx_xtf_channel_info_file ON xtf_channel_info(file_id);
        CREATE INDEX IF NOT EXISTS idx_xtf_ping_file ON xtf_ping(file_id, ping_index);
        CREATE INDEX IF NOT EXISTS idx_xtf_ping_channel_file ON xtf_ping_channel(file_id, ping_id, chan_index);
        CREATE INDEX IF NOT EXISTS idx_xtf_ping_channel_row ON xtf_ping_channel(file_id, row_idx);

        -- Uniqueness for integrity:
        CREATE UNIQUE INDEX IF NOT EXISTS uq_xtf_channel_info ON xtf_channel_info(file_id, chan_index);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_xtf_ping          ON xtf_ping(file_id, ping_index);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_xtf_ping_channel  ON xtf_ping_channel(file_id, ping_id, chan_index);
        """
        try:
            # ensure self.db_file_path's existence
            Path(self.db_file_path).parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_file_path) as conn:
                conn.executescript(DDL)
                conn.commit()
            logging.info("XTF database tables created/verified.")
        except sqlite3.Error as e:
            logging.error(f"DB create error: {e}")

    # ---------------------------------------------------------------------
    # Inserts / helpers
    # ---------------------------------------------------------------------
    def _decode_bytes(self, v) -> str:
        """Decode bytes to str safely; pass through str/None."""
        return v.decode(errors="ignore") if isinstance(v, (bytes, bytearray)) else ("" if v is None else str(v))

    def insert_xtf_file(self, fh, src_path: str) -> int:
        """Insert file-level metadata from pyxtf file header and return file_id."""
        rec = {
            "src_path": src_path,
            "file_format": getattr(fh, "FileFormat", None),
            "system_type": getattr(fh, "SystemType", None),
            "recording_program": self._decode_bytes(getattr(fh, "RecordingProgramName", b"")),
            "recording_version": self._decode_bytes(getattr(fh, "RecordingProgramVersion", b"")),
            "sonar_name": self._decode_bytes(getattr(fh, "SonarName", b"")),
            "sonar_type": getattr(fh, "SonarType", None),
            "note_string": self._decode_bytes(getattr(fh, "NoteString", b"")),
            "nav_units": getattr(fh, "NavUnits", None),
            "num_sonar_channels": getattr(fh, "NumberOfSonarChannels", None),
            "num_bathy_channels": getattr(fh, "NumberOfBathymetryChannels", None),
            "num_snippet_channels": getattr(fh, "NumberOfSnippetChannels", None),
            "num_forwardlook_arrays": getattr(fh, "NumberOfForwardLookArrays", None),
            "num_echo_strength_channels": getattr(fh, "NumberOfEchoStrengthChannels", None),
            "num_interferometry_channels": getattr(fh, "NumberOfInterferometryChannels", None),
            "spheroid_type": "".join(chr(b) if isinstance(b, int) else "" for b in getattr(fh, "SpheriodType", [])).strip("\\x00"),
            "projection_type": "".join(chr(b) if isinstance(b, int) else "" for b in getattr(fh, "ProjectionType", [])).strip("\\x00"),
            "origin_x": getattr(fh, "OriginX", None),
            "origin_y": getattr(fh, "OriginY", None),
            "nav_offset_x": getattr(fh, "NavOffsetX", None),
            "nav_offset_y": getattr(fh, "NavOffsetY", None),
            "nav_offset_z": getattr(fh, "NavOffsetZ", None),
            "nav_offset_yaw": getattr(fh, "NavOffsetYaw", None),
            "mru_offset_x": getattr(fh, "MRUOffsetX", None),
            "mru_offset_y": getattr(fh, "MRUOffsetY", None),
            "mru_offset_z": getattr(fh, "MRUOffsetZ", None),
            "mru_offset_yaw": getattr(fh, "MRUOffsetYaw", None),
            "mru_offset_pitch": getattr(fh, "MRUOffsetPitch", None),
            "mru_offset_roll": getattr(fh, "MRUOffsetRoll", None),
        }
        with sqlite3.connect(self.db_file_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO xtf_file
                (src_path,file_format,system_type,recording_program,recording_version,sonar_name,sonar_type,note_string,nav_units,
                 num_sonar_channels,num_bathy_channels,num_snippet_channels,num_forwardlook_arrays,num_echo_strength_channels,
                 num_interferometry_channels,spheroid_type,projection_type,origin_x,origin_y,nav_offset_x,nav_offset_y,nav_offset_z,
                 nav_offset_yaw,mru_offset_x,mru_offset_y,mru_offset_z,mru_offset_yaw,mru_offset_pitch,mru_offset_roll)
                VALUES (:src_path,:file_format,:system_type,:recording_program,:recording_version,:sonar_name,:sonar_type,:note_string,
                        :nav_units,:num_sonar_channels,:num_bathy_channels,:num_snippet_channels,:num_forwardlook_arrays,:num_echo_strength_channels,
                        :num_interferometry_channels,:spheroid_type,:projection_type,:origin_x,:origin_y,:nav_offset_x,:nav_offset_y,:nav_offset_z,
                        :nav_offset_yaw,:mru_offset_x,:mru_offset_y,:mru_offset_z,:mru_offset_yaw,:mru_offset_pitch,:mru_offset_roll)
                """,
                rec,
            )
            conn.commit()
            return int(cur.lastrowid)

    def insert_channel_info(self, fh, file_id: int) -> None:
        """Insert one row per sonar channel from `fh.sonar_info`."""
        rows = []
        for idx, ci in enumerate(getattr(fh, "sonar_info", [])):
            g = lambda n, d=None: getattr(ci, n, d)
            nm = self._decode_bytes(g("ChannelName", b""))
            rows.append(
                (
                    file_id,
                    idx,
                    nm,
                    g("TypeOfChannel"),
                    g("SubChannelNumber"),
                    g("CorrectionFlags"),
                    g("UniPolar"),
                    g("BytesPerSample"),
                    g("VoltScale"),
                    g("Frequency"),
                    g("HorizBeamAngle"),
                    g("TiltAngle"),
                    g("BeamWidth"),
                    g("OffsetX"),
                    g("OffsetY"),
                    g("OffsetZ"),
                    g("OffsetYaw"),
                    g("OffsetPitch"),
                    g("OffsetRoll"),
                    g("BeamsPerArray"),
                    g("SampleFormat"),
                )
            )
        if not rows:
            return
        with sqlite3.connect(self.db_file_path) as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO xtf_channel_info
                (file_id,chan_index,channel_name,type_of_channel,subchannel_number,correction_flags,unipolar,bytes_per_sample,
                 volt_scale,frequency_hz,horiz_beam_angle,tilt_angle,beam_width,offset_x,offset_y,offset_z,offset_yaw,
                 offset_pitch,offset_roll,beams_per_array,sample_format)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                rows,
            )
            conn.commit()

    def insert_ping(self, file_id: int, ping_index: int, ph) -> int:
        """Insert a ping row and return ping_id."""
        with sqlite3.connect(self.db_file_path) as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO xtf_ping
                (file_id,ping_index,t_utc,julian_day,ping_number,ship_speed,ship_heading,ship_lon,ship_lat,
                 sensor_depth,sensor_altitude,sensor_pitch,sensor_roll,sensor_heading,layback,cable_out)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    file_id,
                    ping_index,
                    self._to_iso_time(ph),
                    getattr(ph, "JulianDay", None),
                    getattr(ph, "PingNumber", None),
                    float(getattr(ph, "ShipSpeed", 0.0) or 0.0),
                    float(getattr(ph, "ShipGyro", 0.0) or 0.0),
                    float(getattr(ph, "ShipXcoordinate", 0.0) or 0.0),
                    float(getattr(ph, "ShipYcoordinate", 0.0) or 0.0),
                    float(getattr(ph, "SensorDepth", 0.0) or 0.0),
                    float(getattr(ph, "SensorPrimaryAltitude", 0.0) or 0.0),
                    float(getattr(ph, "SensorPitch", 0.0) or 0.0),
                    float(getattr(ph, "SensorRoll", 0.0) or 0.0),
                    float(getattr(ph, "SensorHeading", 0.0) or 0.0),
                    float(getattr(ph, "Layback", 0.0) or 0.0),
                    float(getattr(ph, "CableOut", 0.0) or 0.0),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def insert_ping_channel(
        self,
        file_id: int,
        ping_id: int,
        chan_index: int,
        samples: int,
        sample_int_sec: float,
        bytes_per_sample: int,
        slant_range_m: float | None,
        row_idx: int,
        bin_id: int
    ) -> None:
        """Insert a ping-channel mapping row (points to BIN row)."""
        with sqlite3.connect(self.db_file_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO xtf_ping_channel
                (file_id,ping_id,chan_index,samples,sample_int_sec,bytes_per_sample,slant_range_m,row_idx,bin_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (file_id, ping_id, chan_index, samples, sample_int_sec, bytes_per_sample, slant_range_m, row_idx, bin_id),
            )
            conn.commit()
  
    def insert_binfile_meta(
        self, file_id: int, channel_group: str, rows: int, cols: int, dtype: str, layout: str, bin_path: str
    ) -> int:
        """Record the BIN file path and matrix metadata."""
        with sqlite3.connect(self.db_file_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO xtf_binfile (file_id,bin_path,dtype,layout,rows,cols,channel_group)
                VALUES (?,?,?,?,?,?,?)
                """,
                (file_id, bin_path, dtype, layout, rows, cols, channel_group),
            )
            conn.commit()
            return int(cur.lastrowid)
    
    def ensure_schema_upgrade_for_multi_bins(self):
        with sqlite3.connect(self.db_file_path) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(xtf_ping_channel)")]
            if "bin_id" not in cols:
                conn.execute("ALTER TABLE xtf_ping_channel ADD COLUMN bin_id INTEGER REFERENCES xtf_binfile(bin_id)")
                conn.commit()

    # ---------------------------------------------------------------------
    # Binary I/O
    # ---------------------------------------------------------------------
    
    def _bin_path_for_freq(self, freq_label: str) -> str:
        """
        Derive a per-frequency BIN filename based on self.bin_file_path.
        e.g., /data/line.bin -> /data/line_100.bin
        """
        p = Path(self.bin_file_path)
        return str(p.with_name(f"{p.stem}_{freq_label}{p.suffix or '.bin'}"))

    def _write_bin_interleaved(self, port_array: np.ndarray, stbd_array: np.ndarray, dtype: str, out_path: str) -> tuple[int, int, str]:
        """
        Write interleaved matrix to BIN (even=port, odd=stbd).

        Parameters
        ----------
        port_array, stbd_array : np.ndarray
            Shape (P, N) arrays for the two sides.
        dtype : {"float32", "uint16"}

        Returns
        -------
        rows, cols : tuple[int, int]
            The final BIN matrix shape.
        """
        assert port_array.shape == stbd_array.shape, "Port/Stbd arrays must be same shape."
        n_pings, n_samples = port_array.shape

        out_dtype = np.float32 if dtype == "float32" else np.uint16
        out = np.empty((n_pings * 2, n_samples), dtype=out_dtype)
        out[0::2, :] = port_array.astype(out_dtype, copy=False)
        out[1::2, :] = stbd_array.astype(out_dtype, copy=False)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            out.tofile(f)

        self.n_pings, self.n_samples = n_pings, n_samples
        self.dtype = dtype
        self.layout = "interleaved_even_port_odd_stbd"
        logging.info(f"Wrote binary file [BIN {Path(out_path).name}] rows={n_pings*2}, cols={n_samples}, dtype={dtype}")
        return (n_pings * 2, n_samples, out_path)  # rows, cols

    def _derive_freq_bin_path(self, base_path: str, freq_label: str) -> str:
        p = Path(base_path)
        stem = p.stem
        return str(p.with_name(f"{stem}_f{freq_label}{p.suffix}"))
    
    def load_pings_from_bin(self, channel_side: str | int = "port") -> np.memmap | None:
        """
        Return a memmap view of shape (P, N) for the requested side.

        Parameters
        ----------
        channel_side : {"port","stbd"} | {0,1}
            Either a side name or a 0/1 integer (0=port, 1=stbd).

        Returns
        -------
        np.memmap | None
            A memmap view of shape (P, N), or None if metadata is missing.
        """
        try:
            with sqlite3.connect(self.db_file_path) as conn:
                row = conn.execute("SELECT bin_path, rows, cols, dtype FROM xtf_binfile LIMIT 1").fetchone()
            if not row:
                logging.error("No BIN metadata found in xtf_binfile.")
                return None

            bin_path, rows, cols, dtype = row
            dtype_np = np.float32 if dtype == "float32" else np.uint16
            mm = np.memmap(bin_path, dtype=dtype_np, mode="r", shape=(rows, cols))

            if isinstance(channel_side, int):
                side = 0 if channel_side == 0 else 1
            else:
                side = 0 if str(channel_side).lower().startswith("p") else 1

            return mm[side::2, :]
        except Exception as e:
            logging.error(f"load_pings_from_bin error: {e}")
            return None

    def load_pings_from_bin_all(self, freq: str , channel_side: str | int ) -> np.memmap | None:
        """
        Memmap a per-frequency BIN and return (n_pings, n_samples) view
        for the requested side ("port" or "stbd") and frequency. If the user
        requests both sides, call this function twice.
        """
        side_idx = 0 if str(channel_side).lower().startswith("p") else 1
        try:
            with sqlite3.connect(self.db_file_path) as conn:
                row = conn.execute(
                    "SELECT bin_path, rows, cols, dtype FROM xtf_binfile WHERE channel_group = ? ORDER BY bin_id DESC LIMIT 1",
                    (freq,)
                ).fetchone()
            if not row:
                logging.error(f"No BIN found for frequency '{freq}'.")
                return None
            bin_path, rows, cols, dtype = row
            mm = np.memmap(bin_path, dtype=np.float32 if dtype=="float32" else np.uint16, mode="r", shape=(rows, cols))
            return mm[side_idx::2, :]
        except Exception as e:
            logging.error(f"load_pings_from_bin({freq},{channel_side}) error: {e}")
            return None
    
    
    def get_bin_meta(db_path: str, freq: str) -> BinMeta:
        """
        Return the most recent BIN metadata row for a given frequency tag (e.g., "100", "455").
        If multiple BINs exist (from multiple runs), we pick the highest bin_id.
        """
        q = """
        SELECT bin_id, bin_path, rows, cols, dtype, layout, channel_group
        FROM xtf_binfile
        WHERE channel_group = ?
        ORDER BY bin_id DESC
        LIMIT 1
        """
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(q, (str(freq),)).fetchone()
            if not row:
                raise RuntimeError(f"No xtf_binfile row found for channel_group={freq!r}.")
            return BinMeta(
                bin_id=int(row[0]),
                bin_path=str(row[1]),
                rows=int(row[2]),
                cols=int(row[3]),
                dtype=str(row[4]),
                layout=str(row[5]),
                channel_group=str(row[6]),
            )
    # ---------------------------------------------------------------------
    # Small utilities
    # ---------------------------------------------------------------------
    def _to_iso_time(self, ph) -> str:
        """
        Format XTF time fields to ISO-8601 string.

        Uses Year/Month/Day/Hour/Minute/Second/HSeconds (hundredths of a second).
        Example: '2007-07-06T18:40:28.75Z'
        """
        try:
            sec = int(getattr(ph, "Second", 0) or 0)
            hs = int(getattr(ph, "HSeconds", 0) or 0)  # hundredths of a second
            return f"{ph.Year:04d}-{ph.Month:02d}-{ph.Day:02d}T{ph.Hour:02d}:{ph.Minute:02d}:{sec:02d}.{hs:02d}Z"
        except Exception:
            # Fallback (no subseconds)
            return f"{ph.Year:04d}-{ph.Month:02d}-{ph.Day:02d}T{ph.Hour:02d}:{ph.Minute:02d}:{getattr(ph,'Second',0):02d}Z"
        
    def available_freq_pairs(self, fh):
        pairs = {}
        for i, ci in enumerate(getattr(fh, "sonar_info", [])):
            nm = getattr(ci, "ChannelName", b"")
            nm = nm.decode(errors="ignore") if isinstance(nm, (bytes, bytearray)) else str(nm)
            side = "port" if "port" in nm.lower() else ("stbd" if "stbd" in nm.lower() or "star" in nm.lower() else None)
            freq = "".join(c for c in nm if c.isdigit())
            if side and freq:
                pairs.setdefault(freq, {})[side] = i
        # keep only complete pairs
        return {f: m for f, m in pairs.items() if "port" in m and "stbd" in m}


    def _choose_sonar_pair(self, fh, freq_preference=("100", "455")) -> tuple[int, int, str]:
        """
        Pick (port_idx, stbd_idx, freq_label) from header channel names.

        The first frequency in `freq_preference` that has both sides available
        wins (e.g., "100" or "500"). Fallback = first two channels.
        """
        names = []
        for ci in getattr(fh, "sonar_info", []):
            nm = getattr(ci, "ChannelName", b"")
            if isinstance(nm, (bytes, bytearray)):
                nm = nm.decode(errors="ignore")
            names.append(nm)  # e.g., "Port100", "Stbd100", "Port500", "Stbd500"
        print("Channel names:", names)
        
        # Build lookup: freq -> {"port": idx, "stbd": idx}
        by_freq: dict[str, dict[str, int]] = {}

        for idx, nm in enumerate(names):
            nml = nm.lower()
            side = "port" if "port" in nml else ("stbd" if "stbd" in nml or "star" in nml else None)
            freq = "".join(c for c in nm if c.isdigit()) or ""
            if side and freq:
                by_freq.setdefault(freq, {})[side] = idx

        for f in freq_preference:
            pair = by_freq.get(f, {})
            if "port" in pair and "stbd" in pair:
                return pair["port"], pair["stbd"], f

        return 0, 1, "unknown"

    @staticmethod
    def _pad_to(arr: np.ndarray, n: int) -> np.ndarray:
        """Right-pad a 1D array with zeros to length n."""
        if arr.shape[0] == n:
            return arr
        out = np.zeros((n,), dtype=arr.dtype)
        out[: min(n, arr.shape[0])] = arr[: min(n, arr.shape[0])]
        return out
    
    def _infer_dt_from_slant(self, n_samples: int, slant_range_m: float, c: float = 1500.0) -> float | None:
        try:
            if slant_range_m and n_samples and n_samples > 1:
                return (2.0 * float(slant_range_m)) / (c * float(n_samples - 1))
        except Exception:
            pass
        return None
    # ---------------------------------------------------------------------
    # Loader
    # ---------------------------------------------------------------------
    def load_data_xtf(self, file_path: str, store_dtype: str = "float32", freq_preference=("100", "500")):
        """
        Parse an XTF with pyxtf, store one Port/Stbd frequency pair to DB + BIN.

        Parameters
        ----------
        file_path : str
            Path to the input XTF file.
        store_dtype : {"float32", "uint16"}, default "float32"
            Amplitude dtype to store in the BIN. For "float32", raw uint16 values
            are scaled to [0,1] by dividing by 65535.
        freq_preference : tuple[str, ...]
            Preferred frequencies to choose the Port/Stbd pair, first match wins.

        Returns
        -------
        tuple[int, int, float, str] | None
            (n_pings, padded_samples_per_row, sample_interval_sec, freq_label) or None.
        """
        try:
            import pyxtf  # type: ignore
        except Exception as e:
            logging.error(f"pyxtf import failed: {e}")
            return None

        if not file_path or not Path(file_path).exists():
            logging.error(f"File not found: {file_path}")
            return None

        # Read with pyxtf
        fh, packets = pyxtf.xtf_read(file_path)
        sonar_pings = packets.get(pyxtf.XTFHeaderType.sonar, [])
        if not sonar_pings:
            logging.error("No sonar pings found in XTF.")
            return None

        # Prepare DB
        self.create_database()

        # File + channel info
        file_id = self.insert_xtf_file(fh, str(file_path))
        self.insert_channel_info(fh, file_id)

        # Choose Port/Stbd pair
        pairs = self.available_freq_pairs(fh)
        logging.info(f"Available Frequency channels: {pairs}")
        port_idx, stbd_idx, freq_label = self._choose_sonar_pair(fh, freq_preference=freq_preference)
        logging.info(f"Using channels: port={port_idx}, stbd={stbd_idx} (freq={freq_label})")

        # Sample interval (µs -> s) from first ping's channel header
        first_ph = sonar_pings[0]
        try:
            pch = first_ph.ping_chan_headers[port_idx]
            samp_int_sec = float(getattr(pch, "SampleInterval", 0.0)) * 1e-6
            logging.info(f"Sample interval from first ping's channel header: {samp_int_sec} s")
        except Exception:
            samp_int_sec = 0.0
            logging.warning("Could not read sample interval from first ping's channel header; will attempt to infer.")

        # Slant range from first ping's channel headers (may be 0)
        try:
            pch_port = first_ph.ping_chan_headers[port_idx]
            pch_stbd = first_ph.ping_chan_headers[stbd_idx]
            slant_port_m = float(getattr(pch_port, "SlantRange", 0.0) or 0.0)
            slant_stbd_m = float(getattr(pch_stbd, "SlantRange", 0.0) or 0.0)
        except Exception:
            slant_port_m = slant_stbd_m = 0.0

        # Collect arrays + metadata
        port_rows, stbd_rows = [], []
        pc_ids_meta = []  # holds (ping_id) order-aligned for row mapping
        max_len = 0

        for i, ph in enumerate(sonar_pings):
            ping_id = self.insert_ping(file_id, i, ph)

            data_list = getattr(ph, "data", None)
            if not data_list or len(data_list) <= max(port_idx, stbd_idx):
                continue

            a_port = np.asarray(data_list[port_idx])
            a_stbd = np.asarray(data_list[stbd_idx])

            max_len = max(max_len, a_port.shape[0], a_stbd.shape[0])

            port_rows.append(a_port)
            stbd_rows.append(a_stbd)
            pc_ids_meta.append(ping_id)

            # if samp_int_sec is missing/zero, infer from current ping
            if not samp_int_sec or samp_int_sec <= 0:
                logging.debug(f"Inferring sample interval from ping {i} slant range.")
                dt1 = self._infer_dt_from_slant(a_port.shape[0], slant_port_m)
                dt2 = self._infer_dt_from_slant(a_stbd.shape[0], slant_stbd_m)
                # pick a robust value (median of non-nulls)
                cands = [dt for dt in (dt1, dt2) if dt]
                if cands:
                    samp_int_sec = float(np.median(cands))
                    logging.info(f"Inferred sample interval: {samp_int_sec} s")
                else:
                    logging.warning("Could not infer sample interval; leaving as 0.")
                    samp_int_sec = 0.0

        if not port_rows or not stbd_rows:
            logging.error("No channel data collected.")
            return None

        # Pad to rectangular
        port_stack = np.vstack([self._pad_to(a, max_len) for a in port_rows])
        stbd_stack = np.vstack([self._pad_to(a, max_len) for a in stbd_rows])

        # Dtype conversion for BIN
        if store_dtype == "float32":
            port_stack = port_stack.astype(np.float32) / 65535.0
            stbd_stack = stbd_stack.astype(np.float32) / 65535.0
            bin_bps = 4
        elif store_dtype == "uint16":
            port_stack = port_stack.astype(np.uint16)
            stbd_stack = stbd_stack.astype(np.uint16)
            bin_bps = 2
        else:
            raise ValueError("store_dtype must be 'float32' or 'uint16'")

        # Write BIN
        total_rows, padded_len = self._write_bin_interleaved(port_stack, stbd_stack, store_dtype)

        # Record BIN meta
        self.insert_binfile_meta(file_id, freq_label, total_rows, padded_len, store_dtype, "interleaved_even_port_odd_stbd")

        # Insert ping-channel rows with row_idx mapping
        # row_idx: even=port (2*i), odd=stbd (2*i+1)
        for i, ping_id in enumerate(pc_ids_meta):
            self.insert_ping_channel(
                file_id=file_id,
                ping_id=ping_id,
                chan_index=port_idx,
                samples=padded_len,
                sample_int_sec=samp_int_sec,
                bytes_per_sample=bin_bps,
                slant_range_m=slant_port_m,  
                row_idx=2 * i,
            )
            self.insert_ping_channel(
                file_id=file_id,
                ping_id=ping_id,
                chan_index=stbd_idx,
                samples=padded_len,
                sample_int_sec=samp_int_sec,
                bytes_per_sample=bin_bps,
                slant_range_m=slant_stbd_m,
                row_idx=2 * i + 1,
            )

        logging.info(
            f"XTF load complete: pings={port_stack.shape[0]}, samples={padded_len}, dt={samp_int_sec:.6e}s, freq={freq_label}"
        )
        return port_stack.shape[0], padded_len, samp_int_sec, freq_label

    def load_data_xtf_all_freqs(self, file_path: str, store_dtype: str = "float32"):
        """
        Read the XTF once, store metadata for ALL channels, and for every available
        (Port,Stbd) frequency pair:
        - write a separate BIN file (interleaved rows),
        - insert xtf_binfile row,
        - insert two xtf_ping_channel rows per ping (port+stbd) pointing to that BIN.

        Returns: dict[freq] -> (n_pings, padded_len, median_sample_interval_sec)
        """
        try:
            import pyxtf  # type: ignore
        except Exception as e:
            logging.error(f"pyxtf import failed: {e}")
            return None

        if not file_path or not Path(file_path).exists():
            logging.error(f"File not found: {file_path}")
            return None

        self.create_database()
        self.ensure_schema_upgrade_for_multi_bins()

        fh, packets = pyxtf.xtf_read(file_path)
        sonar_pings = packets.get(pyxtf.XTFHeaderType.sonar, [])
        if not sonar_pings:
            logging.error("No sonar pings found in XTF.")
            return None

        file_id = self.insert_xtf_file(fh, str(file_path))
        self.insert_channel_info(fh, file_id)

        pairs = self.available_freq_pairs(fh)  # {"100":{"port":i,"stbd":j}, ...}
        if not pairs:
            logging.error("No complete (port,stbd) frequency pairs found in XTF.")
            return None
        logging.info(f"Available frequency pairs: {pairs}")

        # Per-frequency collectors (consistent keys!)
        freq_data = {
            f: {
                "port_idx": pairs[f]["port"],
                "stbd_idx": pairs[f]["stbd"],
                "port_rows": [],
                "stbd_rows": [],
                "ping_ids": [],
                "dt": [],                 # per-ping sample interval (s)
                "slant_port": [],         # per-ping slant (m)
                "slant_stbd": [],         # per-ping slant (m)
                "max_len": 0,
            }
            for f in pairs.keys()
        }

        # Walk all pings once, collect arrays + per-ping dt/slant
        for i, ph in enumerate(sonar_pings):
            ping_id = self.insert_ping(file_id, i, ph)

            data_list = getattr(ph, "data", None)
            if not data_list:
                continue

            for f, info in freq_data.items():
                p_idx, s_idx = info["port_idx"], info["stbd_idx"]
                if max(p_idx, s_idx) >= len(data_list):
                    continue  # channels missing on this ping

                a_port = np.asarray(data_list[p_idx])
                a_stbd = np.asarray(data_list[s_idx])

                # per-ping channel headers
                try:
                    pch_p = ph.ping_chan_headers[p_idx]
                    pch_s = ph.ping_chan_headers[s_idx]
                    dt = float(getattr(pch_p, "SampleInterval", 0.0) or 0.0) * 1e-6
                    sr_p = float(getattr(pch_p, "SlantRange", 0.0) or 0.0)
                    sr_s = float(getattr(pch_s, "SlantRange", 0.0) or 0.0)
                except Exception:
                    dt = 0.0; sr_p = 0.0; sr_s = 0.0

                # fallbacks if missing/zero
                if not dt:
                    dt = (self._infer_dt_from_slant(a_port.size, sr_p) or
                        self._infer_dt_from_slant(a_stbd.size, sr_s) or
                        (info["dt"][-1] if info["dt"] else 0.0))
                if not sr_p and info["slant_port"]:
                    sr_p = info["slant_port"][-1]
                if not sr_s and info["slant_stbd"]:
                    sr_s = info["slant_stbd"][-1]

                # collect
                info["port_rows"].append(a_port)
                info["stbd_rows"].append(a_stbd)
                info["ping_ids"].append(ping_id)
                info["dt"].append(float(dt))
                info["slant_port"].append(float(sr_p))
                info["slant_stbd"].append(float(sr_s))
                info["max_len"] = max(info["max_len"], a_port.size, a_stbd.size)

        results = {}
        bin_layout = "interleaved_even_port_odd_stbd"

        for f, info in freq_data.items():
            if not info["port_rows"]:
                logging.warning(f"No data collected for frequency {f}; skipping.")
                continue

            # rectangularize
            max_len = int(info["max_len"])
            port_stack = np.vstack([self._pad_to(a, max_len) for a in info["port_rows"]])
            stbd_stack = np.vstack([self._pad_to(a, max_len) for a in info["stbd_rows"]])

            # dtype convert
            if store_dtype == "float32":
                port_stack = port_stack.astype(np.float32) / 65535.0
                stbd_stack = stbd_stack.astype(np.float32) / 65535.0
                bin_bps = 4
            elif store_dtype == "uint16":
                port_stack = port_stack.astype(np.uint16)
                stbd_stack = stbd_stack.astype(np.uint16)
                bin_bps = 2
            else:
                raise ValueError("store_dtype must be 'float32' or 'uint16'")

            # write per-frequency BIN
            out_path = self._bin_path_for_freq(f)
            total_rows, padded_len, bin_path = self._write_bin_interleaved(
                port_stack, stbd_stack, store_dtype, out_path
            )

            # record BIN meta → get bin_id
            bin_id = self.insert_binfile_meta(
                file_id=file_id,
                channel_group=f,
                rows=total_rows,
                cols=padded_len,
                dtype=store_dtype,
                layout=bin_layout,
                bin_path=bin_path,
            )

            # insert two ping_channel rows per ping, mapped to this BIN (per-ping dt/slant!)
            pidx, sidx = info["port_idx"], info["stbd_idx"]
            for j, ping_id in enumerate(info["ping_ids"]):
                self.insert_ping_channel(
                    file_id=file_id, ping_id=ping_id, chan_index=pidx,
                    samples=padded_len, sample_int_sec=float(info["dt"][j]),
                    bytes_per_sample=bin_bps, slant_range_m=float(info["slant_port"][j]),
                    row_idx=2*j, bin_id=bin_id
                )
                self.insert_ping_channel(
                    file_id=file_id, ping_id=ping_id, chan_index=sidx,
                    samples=padded_len, sample_int_sec=float(info["dt"][j]),
                    bytes_per_sample=bin_bps, slant_range_m=float(info["slant_stbd"][j]),
                    row_idx=2*j + 1, bin_id=bin_id
                )

           results[f] = {
                "n_pings": port_stack.shape[0],
                "n_samples": padded_len,
                "dt_median": float(np.median(info["dt"])),
                "bin_path": bin_path,
                "dtype": store_dtype,
                "layout": bin_layout,
            }

            logging.info(f"[{f}] pings={port_stack.shape[0]}, samples={padded_len}, "
                         f"dt~{results[f]['dt_median']:.6e}s → {bin_path}")
        
        return results if results else None

    def get_meta_per_ping(db_path: str, freq: str, side: str | int):
        """
        For the given frequency and side, return per-ping metadata arrays. 
        Used to align navigation or other time-series data to the sonar pings.
        Parameters:
            db_path : str
            freq    : str  (e.g., "100" or "500")
            side    : {"port","stbd"} | {0,1}
                Either a side name or a 0/1 integer (0=port, 1=stbd).
        Returns:
            ping_ids : (P,) int
            alt      : (P,) float  (sensor altitude, meters)
            dt       : (P,) float  (sample interval, seconds). If constant in DB, broadcast.
            n_pings, n_samples     (ints)
            bps      : bytes per sample in BIN (2 or 4)
            bin_path : str
        """
        side = side.lower()
        side_is_port = side.startswith("p")

        with sqlite3.connect(db_path) as conn:
            # Pull BIN row for this frequency
            row = conn.execute("""
                SELECT bin_id, bin_path, dtype, layout, rows, cols
                FROM xtf_binfile
                WHERE channel_group = ?
                LIMIT 1
            """, (str(freq),)).fetchone()
            if not row:
                raise RuntimeError(f"No xtf_binfile row for frequency={freq}")
            bin_id, bin_path, dtype, layout, rows, cols = row
            bps = 4 if dtype == "float32" else 2

            # Map chan_index by side for this freq
            ch_port, ch_stbd = conn.execute("""
                SELECT ci_port.chan_index, ci_stbd.chan_index
                FROM xtf_channel_info ci_port
                JOIN xtf_channel_info ci_stbd ON ci_port.file_id = ci_stbd.file_id
                WHERE ci_port.channel_name LIKE 'Port%' || ?
                AND ci_stbd.channel_name LIKE 'Stbd%' || ?
                LIMIT 1
            """, (str(freq), str(freq))).fetchone() or (None, None)
            if ch_port is None:
                # Fallback: find by digits only
                freq_like = f"%{freq}%"
                ch_port = conn.execute("""
                    SELECT chan_index FROM xtf_channel_info
                    WHERE channel_name LIKE 'Port%' AND channel_name LIKE ?
                    ORDER BY chan_index LIMIT 1
                """, (freq_like,)).fetchone()
                ch_port = ch_port[0] if ch_port else None
                ch_stbd = conn.execute("""
                    SELECT chan_index FROM xtf_channel_info
                    WHERE channel_name LIKE 'Stbd%' AND channel_name LIKE ?
                    ORDER BY chan_index LIMIT 1
                """, (freq_like,)).fetchone()
                ch_stbd = ch_stbd[0] if ch_stbd else None
            if ch_port is None or ch_stbd is None:
                raise RuntimeError(f"Could not resolve chan_index for {freq} kHz")

            chan_index = ch_port if side_is_port else ch_stbd

            # Per-ping ordering and meta
            rows = conn.execute("""
                SELECT p.ping_id, p.ping_index, p.sensor_altitude,
                    pc.sample_int_sec
                FROM xtf_ping p
                JOIN xtf_ping_channel pc
                ON p.ping_id = pc.ping_id
                JOIN xtf_binfile b
                ON b.bin_id = pc.bin_id
                WHERE b.channel_group = ?
                AND pc.chan_index = ?
                ORDER BY p.ping_index ASC
            """, (str(freq), int(chan_index))).fetchall()

        if not rows:
            raise RuntimeError("No ping/chan rows resolved for this freq/side")

        ping_ids      = np.array([r[0] for r in rows], dtype=int)
        ping_index    = np.array([r[1] for r in rows], dtype=int)
        alt           = np.array([float(r[2] or 0.0) for r in rows], dtype=float)
        dt            = np.array([float(r[3] or 0.0) for r in rows], dtype=float)
        
        # If dt is constant or zero in places, fill from median of non-zero
        if not np.any(dt > 0):
            dt[:] = 0.0
        else:
            med = np.median(dt[dt > 0])
            dt[dt <= 0] = med

        n_pings = ping_ids.size

        # n_samples from the bin meta we already pulled in the caller function
        # but we return None here; caller will get it from the image array shape
        return ping_ids, alt, dt, bps, bin_path, n_pings
    
    # ---------------------------------------------------------------------
    # Quicklook
    # ---------------------------------------------------------------------
    def export_image_mosaic(self, output_path: str, freq: str , channel: str | int ) -> None:
        """
        Save a quick-look image (non-georeferenced) of the chosen side.

        Parameters
        ----------
        output_path : str
            PNG path to write.
        channel : {"port","stbd"} | {0,1}
            Which side to visualize.
        """
        try:
            import matplotlib.pyplot as plt  # local import (optional dependency)
        except ImportError:
            logging.error("matplotlib not installed.")
            return

        data = self.load_pings_from_bin_all(freq=freq, channel_side=channel)
        if data is None:
            return

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(data.T, aspect="auto", cmap="gray")
        ax.set_xlabel("Ping #")
        ax.set_ylabel("Sample")
        side_str = "port" if (channel == 0 or (isinstance(channel, str) and channel.lower().startswith("p"))) else "starboard"
        ax.set_title(f"Side-scan amplitude (channel={side_str})")
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)


__all__ = ["XTF"]

if __name__ == "__main__":
    print("This module is intended to be imported, not run directly.")