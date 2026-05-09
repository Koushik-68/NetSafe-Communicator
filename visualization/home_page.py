import tkinter as tk


class HomePage(tk.Frame):
    def __init__(self, master, on_select_protocol):
        super().__init__(master, bg="#121417")
        self.on_select_protocol = on_select_protocol
        self._build()

    def _build(self):
        title = tk.Label(
            self,
            text="Protocol Visualization Lab",
            bg="#121417",
            fg="#E6E9EE",
            font=("Segoe UI Semibold", 18),
        )
        title.pack(pady=(30, 10))

        subtitle = tk.Label(
            self,
            text="Choose a protocol to simulate packet delivery",
            bg="#121417",
            fg="#A8AFB9",
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 20))

        cards = tk.Frame(self, bg="#121417")
        cards.pack(fill="both", expand=True, padx=25, pady=15)

        protocol_meta = {
            "TCP": "Reliable and ordered delivery with retransmissions.",
            "UDP": "Fast datagram style delivery with possible loss/out-of-order.",
            "QUIC": "Reliable delivery over UDP with modern transport behavior.",
        }

        for protocol, info in protocol_meta.items():
            card = tk.Frame(cards, bg="#1A1D21", highlightthickness=1, highlightbackground="#2A2F36")
            card.pack(fill="x", pady=8)

            tk.Label(
                card,
                text=protocol,
                bg="#1A1D21",
                fg="#E6E9EE",
                font=("Segoe UI Semibold", 14),
            ).pack(anchor="w", padx=12, pady=(10, 2))

            tk.Label(
                card,
                text=info,
                bg="#1A1D21",
                fg="#A8AFB9",
                font=("Segoe UI", 10),
                wraplength=680,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 10))

            tk.Button(
                card,
                text=f"Start {protocol} Simulation",
                command=lambda p=protocol: self.on_select_protocol(p),
                bg="#57B5A5",
                fg="#0E1412",
                activebackground="#3C8F82",
                relief="flat",
                bd=0,
                padx=12,
                pady=6,
                font=("Segoe UI Semibold", 10),
                cursor="hand2",
            ).pack(anchor="e", padx=12, pady=(0, 12))
