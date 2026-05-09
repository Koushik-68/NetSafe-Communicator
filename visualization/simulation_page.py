import tkinter as tk
from tkinter import ttk

from .simulator_logic import ProtocolSimulator


class SimulationPage(tk.Frame):
    def __init__(self, master, protocol, on_back):
        super().__init__(master, bg="#121417")
        self.protocol = protocol
        self.on_back = on_back
        self.simulator = ProtocolSimulator()
        self.animation_after_ids = []
        self.current_result = None
        self.active_packet_id = None
        self.packet_bubbles = {}

        # Canvas coordinates for path visualization.
        self.sender_pos = (130, 130)
        self.network_pos = (460, 130)
        self.receiver_pos = (790, 130)
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#121417")
        header.pack(fill="x", padx=16, pady=(16, 8))

        tk.Button(
            header,
            text="← Back",
            command=self.on_back,
            bg="#22262B",
            fg="#E6E9EE",
            activebackground="#3C8F82",
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

        tk.Label(
            header,
            text=f"{self.protocol} Simulation",
            bg="#121417",
            fg="#E6E9EE",
            font=("Segoe UI Semibold", 16),
        ).pack(side="left", padx=12)

        controls = tk.Frame(self, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
        controls.pack(fill="x", padx=16, pady=(0, 10))

        tk.Label(controls, text="Preset Message", bg="#1A1D21", fg="#A8AFB9", font=("Segoe UI", 9)).grid(row=0, column=0, padx=8, pady=(10, 4), sticky="w")
        self.preset_var = tk.StringVar(value="Hello, this is a protocol simulation demo message.")
        ttk.Combobox(
            controls,
            textvariable=self.preset_var,
            values=[
                "Hello, this is a protocol simulation demo message.",
                "Secure chat packet testing under unstable network.",
                "Visualization helps understand delivery internals.",
            ],
            state="readonly",
            width=52,
        ).grid(row=0, column=1, padx=8, pady=(10, 4), sticky="w")

        tk.Label(controls, text="Your Message", bg="#1A1D21", fg="#A8AFB9", font=("Segoe UI", 9)).grid(row=1, column=0, padx=8, pady=4, sticky="w")
        self.message_entry = tk.Entry(controls, width=60, bg="#22262B", fg="#E6E9EE", insertbackground="#E6E9EE", relief="flat")
        self.message_entry.grid(row=1, column=1, padx=8, pady=4, sticky="w")

        tk.Label(controls, text="Chunk Size", bg="#1A1D21", fg="#A8AFB9", font=("Segoe UI", 9)).grid(row=2, column=0, padx=8, pady=(4, 10), sticky="w")
        self.chunk_var = tk.IntVar(value=8)
        tk.Spinbox(controls, from_=4, to=20, textvariable=self.chunk_var, width=8).grid(row=2, column=1, padx=8, pady=(4, 10), sticky="w")

        tk.Button(
            controls,
            text="Run Simulation",
            command=self.run_simulation,
            bg="#57B5A5",
            fg="#0E1412",
            activebackground="#3C8F82",
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        ).grid(row=3, column=1, padx=8, pady=(0, 12), sticky="e")

        summary_frame = tk.Frame(self, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
        summary_frame.pack(fill="x", padx=16, pady=(0, 10))
        self.summary_label = tk.Label(summary_frame, text="Run a simulation to view protocol metrics.", bg="#1A1D21", fg="#A8AFB9", font=("Consolas", 10), justify="left", anchor="w")
        self.summary_label.pack(fill="x", padx=10, pady=10)

        self.stage_frame = tk.Frame(self, bg="#121417")
        self.stage_frame.pack(fill="x", padx=16, pady=(0, 10))
        self.stage_labels = {}
        for stage_name in ["Split", "Header", "Encrypt", "Queue", "Send", "Transit", "ACK", "Reassemble"]:
            chip = tk.Label(
                self.stage_frame,
                text=stage_name,
                bg="#22262B",
                fg="#A8AFB9",
                font=("Segoe UI Semibold", 9),
                padx=10,
                pady=5,
            )
            chip.pack(side="left", padx=4)
            self.stage_labels[stage_name.lower()] = chip

        viz_frame = tk.Frame(self, bg="#121417")
        viz_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        left_panel = tk.Frame(viz_frame, bg="#121417")
        left_panel.pack(side="left", fill="both", expand=True)

        right_panel = tk.Frame(viz_frame, bg="#121417")
        right_panel.pack(side="right", fill="y", padx=(12, 0))

        chunk_frame = tk.Frame(left_panel, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
        chunk_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            chunk_frame,
            text="Packet Division View",
            bg="#1A1D21",
            fg="#E6E9EE",
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.chunk_canvas = tk.Canvas(
            chunk_frame,
            bg="#1A1D21",
            height=70,
            highlightthickness=0,
            bd=0,
        )
        self.chunk_canvas.pack(fill="x", padx=8, pady=(0, 8))

        path_frame = tk.Frame(left_panel, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
        path_frame.pack(fill="x")

        tk.Label(
            path_frame,
            text="Packet Path Visualization (Sender -> Network -> Receiver)",
            bg="#1A1D21",
            fg="#E6E9EE",
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.path_canvas = tk.Canvas(
            path_frame,
            bg="#15181C",
            height=340,
            width=900,
            highlightthickness=0,
            bd=0,
        )
        self.path_canvas.pack(fill="x", padx=8, pady=(0, 8))

        table_frame = tk.Frame(left_panel, bg="#121417")
        table_frame.pack(fill="both", expand=True, pady=(10, 0))

        columns = ("seq", "payload", "size", "status", "delay")
        self.packet_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.packet_table.heading("seq", text="Seq")
        self.packet_table.heading("payload", text="Payload")
        self.packet_table.heading("size", text="Bytes")
        self.packet_table.heading("status", text="Status")
        self.packet_table.heading("delay", text="Delay (ms)")
        self.packet_table.column("seq", width=50, anchor="center")
        self.packet_table.column("payload", width=300)
        self.packet_table.column("size", width=70, anchor="center")
        self.packet_table.column("status", width=120, anchor="center")
        self.packet_table.column("delay", width=90, anchor="center")
        self.packet_table.pack(fill="both", expand=True)

        inspector_frame = tk.Frame(right_panel, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
        inspector_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            inspector_frame,
            text="Packet Inspector",
            bg="#1A1D21",
            fg="#E6E9EE",
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.packet_inspector = tk.Label(
            inspector_frame,
            text="No packet selected yet.",
            justify="left",
            anchor="w",
            bg="#1A1D21",
            fg="#A8AFB9",
            font=("Consolas", 9),
            padx=10,
            pady=8,
        )
        self.packet_inspector.pack(fill="x", padx=8, pady=(0, 8))

        timeline_frame = tk.Frame(right_panel, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
        timeline_frame.pack(fill="both", expand=True)

        tk.Label(
            timeline_frame,
            text="Event Timeline",
            bg="#1A1D21",
            fg="#E6E9EE",
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.timeline_list = tk.Listbox(
            timeline_frame,
            width=42,
            bg="#1A1D21",
            fg="#A8AFB9",
            selectbackground="#3C8F82",
            relief="flat",
            bd=0,
            font=("Consolas", 9),
        )
        self.timeline_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._draw_static_path()

    def run_simulation(self):
        self._cancel_pending_animation()
        self.packet_bubbles = {}
        self.active_packet_id = None

        message = self.message_entry.get().strip() or self.preset_var.get().strip()
        result = self.simulator.run(self.protocol, message, self.chunk_var.get())
        self.current_result = result

        self.summary_label.config(
            text=(
                f"Protocol: {result.protocol}\n"
                f"Total Packets: {result.total_packets} | Delivered: {result.delivered_packets} | Dropped: {result.dropped_packets}\n"
                f"Retransmissions: {result.retransmissions} | Ordered Delivery: {result.ordered_delivery}\n"
                f"Total Time: {result.total_time_ms} ms\n"
                f"Reassembled: {result.reassembled_message}"
            )
        )

        self._highlight_stage("split")
        self.packet_inspector.config(text="Simulation running... packet details will appear here.")

        self._render_packet_division(result)
        self._draw_static_path()
        self._reset_timeline()

        for row in self.packet_table.get_children():
            self.packet_table.delete(row)

        for packet in result.packets:
            self.packet_table.insert(
                "",
                "end",
                values=(
                    packet.seq_no,
                    packet.payload,
                    packet.size_bytes,
                    packet.status,
                    packet.delay_ms,
                ),
            )

        self._render_event_overview(result)
        self._start_animation(result)

    def _draw_static_path(self):
        self.path_canvas.delete("all")

        sx, sy = self.sender_pos
        nx, ny = self.network_pos
        rx, ry = self.receiver_pos

        self.path_canvas.create_line(sx + 55, sy, nx - 55, ny, fill="#3B4048", width=3)
        self.path_canvas.create_line(nx + 55, ny, rx - 55, ry, fill="#3B4048", width=3)

        self._draw_node(sx, sy, "Sender", "#57B5A5")
        self._draw_node(nx, ny, "Network", "#E0A84F")
        self._draw_node(rx, ry, "Receiver", "#5D87E5")

        self.path_canvas.create_text(
            sx,
            sy + 45,
            text="Packet creation",
            fill="#A8AFB9",
            font=("Segoe UI", 9),
        )
        self.path_canvas.create_text(
            nx,
            ny + 45,
            text="Transit / loss / reorder",
            fill="#A8AFB9",
            font=("Segoe UI", 9),
        )
        self.path_canvas.create_text(
            rx,
            ry + 45,
            text="Reassembly",
            fill="#A8AFB9",
            font=("Segoe UI", 9),
        )

    def _draw_node(self, x, y, label, color):
        self.path_canvas.create_oval(x - 52, y - 32, x + 52, y + 32, fill="#1A1D21", outline=color, width=2)
        self.path_canvas.create_text(x, y, text=label, fill="#E6E9EE", font=("Segoe UI Semibold", 10))

    def _render_packet_division(self, result):
        self.chunk_canvas.delete("all")
        width = max(self.chunk_canvas.winfo_width(), 850)
        total = max(1, len(result.packets))
        usable = width - 20
        box_w = max(62, min(140, usable // total))

        x = 10
        y0 = 10
        y1 = 62

        for packet in result.packets:
            status_color = "#44C28B"
            if packet.status == "dropped":
                status_color = "#D16B6B"
            elif packet.status == "retransmitted":
                status_color = "#E0A84F"

            card_id = self.chunk_canvas.create_rectangle(x, y0, x + box_w - 6, y1, fill="#22262B", outline=status_color, width=2)
            self.chunk_canvas.create_text(
                x + 8,
                y0 + 12,
                text=f"P{packet.seq_no}  A{packet.attempt_no}",
                fill="#E6E9EE",
                font=("Segoe UI Semibold", 9),
                anchor="w",
            )
            preview = packet.payload if len(packet.payload) <= 10 else packet.payload[:10] + "..."
            self.chunk_canvas.create_text(
                x + 8,
                y0 + 28,
                text=preview,
                fill="#A8AFB9",
                font=("Consolas", 8),
                anchor="w",
            )
            self.chunk_canvas.create_text(
                x + 8,
                y0 + 44,
                text=f"CHK {packet.checksum} | TTL {packet.ttl}",
                fill="#7D8A9B",
                font=("Consolas", 7),
                anchor="w",
            )
            self.chunk_canvas.tag_bind(card_id, "<Button-1>", lambda e, p=packet: self._inspect_packet(p))
            x += box_w

    def _render_event_overview(self, result):
        self.timeline_list.delete(0, tk.END)
        self.timeline_list.insert(tk.END, f"Protocol profile: {result.network_profile_name}")
        self.timeline_list.insert(tk.END, f"Ordered delivery: {result.ordered_delivery}")
        self.timeline_list.insert(tk.END, "-")
        self.timeline_list.yview_moveto(1.0)

    def _start_animation(self, result):
        for index, event in enumerate(result.events):
            delay_ms = event.time_ms
            if event.stage in {"split", "header", "encrypt", "queue"}:
                self._queue_event(delay_ms, event, index)
            elif event.stage == "send":
                self._queue_motion(delay_ms, event.packet_id, "sender_to_network", event)
            elif event.stage == "hop":
                self._queue_event(delay_ms, event, index)
                self._queue_linger(delay_ms, event.packet_id, event, "#6AA8FF")
            elif event.stage == "drop":
                self._queue_event(delay_ms, event, index)
                self._queue_drop_mark(delay_ms, event.packet_id)
            elif event.stage in {"retry", "retry_send"}:
                self._queue_motion(delay_ms, event.packet_id, "sender_to_network", event, retry=True)
            elif event.stage == "retry_deliver":
                self._queue_motion(delay_ms, event.packet_id, "network_to_receiver", event, retry=True)
            elif event.stage == "ack":
                self._queue_ack(delay_ms, event)
            elif event.stage == "reorder":
                self._queue_event(delay_ms, event, index)
                self._queue_reorder_mark(delay_ms, event.packet_id)
            elif event.stage == "reassemble":
                self._queue_event(delay_ms, event, index)
                self.after(delay_ms + 180, lambda e=event: self._show_reassembly_complete(e))

    def _highlight_stage(self, stage_name):
        for name, widget in self.stage_labels.items():
            if name == stage_name:
                widget.config(bg="#57B5A5", fg="#0E1412")
            else:
                widget.config(bg="#22262B", fg="#A8AFB9")

    def _queue_event(self, delay_ms, event, index):
        after_id = self.after(
            delay_ms,
            lambda e=event, idx=index: self._handle_event(e, idx),
        )
        self.animation_after_ids.append(after_id)

    def _queue_motion(self, delay_ms, packet_id, movement_type, event, retry=False):
        after_id = self.after(
            delay_ms,
            lambda pid=packet_id, mt=movement_type, ev=event, rt=retry: self._animate_packet_motion(pid, mt, ev, rt),
        )
        self.animation_after_ids.append(after_id)

    def _queue_linger(self, delay_ms, packet_id, event, color):
        after_id = self.after(delay_ms + 120, lambda pid=packet_id, ev=event, c=color: self._pulse_network(pid, ev, c))
        self.animation_after_ids.append(after_id)

    def _queue_drop_mark(self, delay_ms, packet_id):
        after_id = self.after(delay_ms + 40, lambda pid=packet_id: self._draw_drop_marker(pid))
        self.animation_after_ids.append(after_id)

    def _queue_reorder_mark(self, delay_ms, packet_id):
        after_id = self.after(delay_ms + 40, lambda pid=packet_id: self._draw_reorder_marker(pid))
        self.animation_after_ids.append(after_id)

    def _queue_ack(self, delay_ms, event):
        after_id = self.after(delay_ms + 30, lambda e=event: self._draw_ack_line(e))
        self.animation_after_ids.append(after_id)

    def _animate_packet_motion(self, packet_id, movement_type, event, retry=False):
        packet = self._packet_by_id(packet_id, retry=retry)
        if not packet:
            return

        self.active_packet_id = packet_id
        self._inspect_packet(packet)

        if movement_type == "sender_to_network":
            start = (self.sender_pos[0], self.sender_pos[1])
            end = (self.network_pos[0], self.network_pos[1])
            color = "#6AA8FF" if not retry else "#E0A84F"
            label = f"P{packet.seq_no}" if not retry else f"R{packet.seq_no}"
        else:
            start = (self.network_pos[0], self.network_pos[1])
            end = (self.receiver_pos[0], self.receiver_pos[1])
            color = "#44C28B" if not retry else "#E0A84F"
            label = f"P{packet.seq_no}" if not retry else f"R{packet.seq_no}"

        self._draw_packet_bubble(packet_id, start, color, label)

        steps = 28
        bubble, text = self.packet_bubbles.get((packet_id, packet.attempt_no), (None, None))
        if not bubble:
            return

        dx = (end[0] - start[0]) / steps
        dy = (end[1] - start[1]) / steps

        def step(i=0):
            if i >= steps:
                if movement_type == "network_to_receiver":
                    self._draw_delivery_marker(packet_id, retry)
                return
            self.path_canvas.move(bubble, dx, dy)
            self.path_canvas.move(text, dx, dy)
            after_id = self.after(24, lambda: step(i + 1))
            self.animation_after_ids.append(after_id)

        step()

    def _pulse_network(self, packet_id, event, color):
        marker = self.path_canvas.create_oval(430, 95, 490, 155, outline=color, width=2)

        def fade(step=0):
            if step >= 10:
                self.path_canvas.delete(marker)
                return
            width = max(1, 4 - step // 3)
            self.path_canvas.itemconfig(marker, width=width)
            after_id = self.after(40, lambda: fade(step + 1))
            self.animation_after_ids.append(after_id)

        fade()

    def _draw_packet_bubble(self, packet_id, start, color, label):
        packet = self._packet_by_id(packet_id)
        if not packet:
            return
        x0, y0 = start
        radius = 13
        bubble = self.path_canvas.create_oval(x0 - radius, y0 - radius, x0 + radius, y0 + radius, fill=color, outline="")
        text = self.path_canvas.create_text(x0, y0, text=label, fill="#0E1412", font=("Consolas", 8, "bold"))
        self.packet_bubbles[(packet_id, packet.attempt_no)] = (bubble, text)

    def _draw_delivery_marker(self, packet_id, retry=False):
        x, y = self.receiver_pos
        text = f"delivered P{packet_id}" if not retry else f"retry delivered P{packet_id}"
        self.path_canvas.create_text(x + 125, y - 55 + (packet_id % 4) * 16, text=text, fill="#44C28B", font=("Consolas", 8, "bold"), anchor="w")

    def _draw_drop_marker(self, seq_no):
        nx, ny = self.network_pos
        x = nx + 95
        y = ny - 40 + (seq_no % 4) * 18
        self.path_canvas.create_text(x, y, text=f"✕ Packet {seq_no} dropped", fill="#D16B6B", font=("Consolas", 9, "bold"), anchor="w")

    def _draw_reorder_marker(self, packet_id):
        x, y = self.network_pos
        self.path_canvas.create_text(x + 90, y + 40, text=f"Packet {packet_id} waiting in reorder buffer", fill="#E0A84F", font=("Consolas", 8), anchor="w")

    def _draw_ack_line(self, event):
        x0, y0 = self.receiver_pos
        x1, y1 = self.sender_pos
        ack = self.path_canvas.create_line(x0 - 35, y0 + 58, x1 + 35, y1 + 58, fill="#5D87E5", width=2, arrow=tk.LAST, dash=(4, 3))
        self.path_canvas.create_text((x0 + x1) / 2, y0 + 75, text=event.description, fill="#5D87E5", font=("Consolas", 8))

    def _show_reassembly_complete(self, event):
        self._highlight_stage("reassemble")
        self._append_timeline(event.time_ms, event.description, event.color)
        self.packet_inspector.config(text=f"Final message reconstructed\n\n{self.current_result.reassembled_message}")

    def _packet_by_id(self, packet_id, retry=False):
        if not self.current_result:
            return None
        if retry:
            retry_packets = [packet for packet in self.current_result.packets if packet.seq_no == packet_id and packet.attempt_no > 1]
            return retry_packets[0] if retry_packets else None
        packets = [packet for packet in self.current_result.packets if packet.seq_no == packet_id and packet.attempt_no == 1]
        return packets[0] if packets else next((packet for packet in self.current_result.packets if packet.seq_no == packet_id), None)

    def _inspect_packet(self, packet):
        self.active_packet_id = packet.packet_id
        self.packet_inspector.config(
            text=(
                f"Packet {packet.seq_no} (Attempt {packet.attempt_no})\n"
                f"Chunk Index: {packet.chunk_index}\n"
                f"Payload: {packet.payload}\n"
                f"Bytes: {packet.size_bytes}\n"
                f"Checksum: {packet.checksum}\n"
                f"TTL: {packet.ttl}\n"
                f"Status: {packet.status}\n"
                f"Sent At: {packet.sent_at_ms} ms\n"
                f"Delivered At: {packet.delivered_at_ms if packet.delivered_at_ms is not None else 'Pending'}\n"
                f"Notes: {packet.notes}"
            )
        )
        self._highlight_stage("send" if packet.status != "dropped" else "queue")

    def _handle_event(self, event, index):
        self._highlight_stage(event.stage if event.stage in self.stage_labels else "send")
        self._append_timeline(event.time_ms, event.description, event.color)
        if event.packet_id:
            packet = self._packet_by_id(event.packet_id, retry=event.stage.startswith("retry"))
            if packet:
                self._inspect_packet(packet)

    def _reset_timeline(self):
        self.timeline_list.delete(0, tk.END)

    def _append_timeline(self, delay_ms, text, color="#A8AFB9"):
        self.timeline_list.insert(tk.END, f"t+{delay_ms:04d}ms  {text}")
        self.timeline_list.yview_moveto(1.0)
        if self.timeline_list.size() > 0:
            self.timeline_list.itemconfig(self.timeline_list.size() - 1, fg=color)

    def _cancel_pending_animation(self):
        for after_id in self.animation_after_ids:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self.animation_after_ids = []
