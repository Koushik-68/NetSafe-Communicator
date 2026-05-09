import hashlib
import random
from typing import List

from .models import Packet, SimulationEvent, SimulationResult


class ProtocolSimulator:
    """Reusable protocol simulation engine.

    New protocols can be added by expanding _profile_for_protocol.
    """

    def run(self, protocol: str, message: str, chunk_size: int = 8) -> SimulationResult:
        profile = self._profile_for_protocol(protocol)

        chunks = [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)] or [""]
        total_packets = len(chunks)
        packets: List[Packet] = []
        events: List[SimulationEvent] = []

        dropped = 0
        retransmissions = 0
        delivered_payloads = []
        current_time = 0

        for i, chunk in enumerate(chunks, start=1):
            payload_bytes = chunk.encode("utf-8")
            checksum = hashlib.sha256(payload_bytes).hexdigest()[:10]
            delay_ms = max(20, int(random.gauss(profile["base_delay_ms"], profile["jitter_ms"]))) + 18
            dropped_now = random.random() < profile["drop_rate"]
            reordered_now = profile["reorder_enabled"] and random.random() < profile["reorder_rate"]

            packet = Packet(
                packet_id=i,
                seq_no=i,
                total_packets=total_packets,
                chunk_index=i - 1,
                payload=chunk,
                size_bytes=len(payload_bytes),
                checksum=checksum,
                ttl=profile["ttl"],
                status="created",
                delay_ms=delay_ms,
                sent_at_ms=current_time,
                notes=f"seq={i}/{total_packets} checksum={checksum}",
            )

            events.extend(self._packet_lifecycle_events(packet, profile, current_time))

            status = "dropped" if dropped_now else "delivered"
            if dropped_now:
                dropped += 1
                packet.dropped = True
                packet.status = "dropped"
                packet.notes = f"Dropped after {current_time + delay_ms}ms"
                packets.append(packet)
                events.append(
                    SimulationEvent(
                        time_ms=current_time + delay_ms,
                        packet_id=i,
                        stage="drop",
                        description=f"Packet {i} is dropped in the network layer.",
                        color="#D16B6B",
                        lane="network",
                    )
                )
                if profile["reliable"]:
                    retransmissions += 1
                    packet.retransmit_count += 1
                    retry_time = current_time + delay_ms + profile["ack_delay_ms"] + 160
                    retry_packet = Packet(
                        packet_id=i,
                        seq_no=i,
                        total_packets=total_packets,
                        chunk_index=i - 1,
                        payload=chunk,
                        size_bytes=len(payload_bytes),
                        checksum=checksum,
                        ttl=max(1, profile["ttl"] - 1),
                        status="retransmitted",
                        delay_ms=max(24, delay_ms - 6),
                        attempt_no=2,
                        retransmit_count=1,
                        sent_at_ms=retry_time,
                        notes="Retry keeps same sequence number and checksum",
                    )
                    events.extend(self._packet_retransmit_events(retry_packet, profile, retry_time))
                    retry_delivered_at = retry_time + retry_packet.delay_ms
                    retry_packet.delivered_at_ms = retry_delivered_at
                    retry_packet.acked = True
                    retry_packet.status = "delivered"
                    packets.append(retry_packet)
                    delivered_payloads.append((i, chunk, retry_delivered_at))
                else:
                    pass
            else:
                packet.status = "delivered"
                packet.delivered_at_ms = current_time + delay_ms
                packet.acked = profile["reliable"]
                packet.notes = f"Delivered at {packet.delivered_at_ms}ms"
                packets.append(packet)
                delivered_payloads.append((i, chunk, packet.delivered_at_ms))

                if profile["reliable"]:
                    events.append(
                        SimulationEvent(
                            time_ms=packet.delivered_at_ms,
                            packet_id=i,
                            stage="ack",
                            description=f"ACK received for packet {i}.",
                            color="#5D87E5",
                            lane="ack",
                        )
                    )

            if reordered_now and not dropped_now:
                events.append(
                    SimulationEvent(
                        time_ms=current_time + delay_ms + 40,
                        packet_id=i,
                        stage="reorder",
                        description=f"Packet {i} arrives out of order and waits in reorder buffer.",
                        color="#E0A84F",
                        lane="network",
                    )
                )

            current_time += profile["inter_packet_gap_ms"]

        if profile["ordered_delivery"]:
            delivered_payloads.sort(key=lambda x: x[0])
        else:
            delivered_payloads.sort(key=lambda x: x[2])

        reassembled_message = "".join(part for _, part, _ in delivered_payloads)
        delivered_packets = len(delivered_payloads)
        total_time_ms = max((p.delivered_at_ms or 0) for p in packets) + 120 if packets else 0

        if packets:
            events.append(
                SimulationEvent(
                    time_ms=total_time_ms,
                    packet_id=0,
                    stage="reassemble",
                    description=f"Receiver reassembles {delivered_packets}/{total_packets} packets into the final message.",
                    color="#44C28B",
                    lane="receiver",
                )
            )

        return SimulationResult(
            protocol=protocol,
            original_message=message,
            reassembled_message=reassembled_message,
            packets=packets,
            events=sorted(events, key=lambda e: e.time_ms),
            dropped_packets=dropped,
            retransmissions=retransmissions,
            delivered_packets=delivered_packets,
            total_packets=total_packets,
            total_time_ms=total_time_ms,
            ordered_delivery=profile["ordered_delivery"],
            network_profile_name=profile["profile_name"],
        )

    def _packet_lifecycle_events(self, packet: Packet, profile, start_time: int) -> List[SimulationEvent]:
        return [
            SimulationEvent(start_time, packet.packet_id, "split", f"Message chunked into packet {packet.seq_no}.", "#57B5A5", "sender"),
            SimulationEvent(start_time + 40, packet.packet_id, "header", f"Header built: seq={packet.seq_no}, checksum={packet.checksum}, ttl={packet.ttl}.", "#A8AFB9", "sender"),
            SimulationEvent(start_time + 80, packet.packet_id, "encrypt", "Payload protected and ready for transmission.", "#5D87E5", "sender"),
            SimulationEvent(start_time + 110, packet.packet_id, "queue", f"Packet queued for the {profile['profile_name']} pipeline.", "#E0A84F", "network"),
            SimulationEvent(start_time + 130, packet.packet_id, "send", f"Packet {packet.seq_no} sent from sender to network.", "#44C28B", "network"),
            SimulationEvent(start_time + 180, packet.packet_id, "hop", f"Packet {packet.seq_no} traversing network hop(s).", "#E6E9EE", "network"),
        ]

    def _packet_retransmit_events(self, packet: Packet, profile, start_time: int) -> List[SimulationEvent]:
        return [
            SimulationEvent(start_time, packet.packet_id, "retry", f"Packet {packet.seq_no} retransmitted with same sequence number.", "#E0A84F", "sender"),
            SimulationEvent(start_time + 55, packet.packet_id, "retry_send", f"Retry packet {packet.seq_no} enters the network again.", "#E0A84F", "network"),
            SimulationEvent(start_time + 140, packet.packet_id, "retry_deliver", f"Retry packet {packet.seq_no} reaches receiver.", "#44C28B", "receiver"),
            SimulationEvent(start_time + 180, packet.packet_id, "ack", f"ACK confirms retransmitted packet {packet.seq_no} delivery.", "#5D87E5", "ack"),
        ]

    def _profile_for_protocol(self, protocol: str):
        protocol = protocol.upper()
        profiles = {
            "TCP": {
                "profile_name": "TCP-like Reliable Stream",
                "base_delay_ms": 70,
                "jitter_ms": 15,
                "drop_rate": 0.08,
                "reliable": True,
                "ordered_delivery": True,
                "ttl": 8,
                "ack_delay_ms": 70,
                "inter_packet_gap_ms": 90,
                "reorder_enabled": True,
                "reorder_rate": 0.15,
            },
            "UDP": {
                "profile_name": "UDP-like Datagram Flow",
                "base_delay_ms": 30,
                "jitter_ms": 22,
                "drop_rate": 0.20,
                "reliable": False,
                "ordered_delivery": False,
                "ttl": 4,
                "ack_delay_ms": 0,
                "inter_packet_gap_ms": 60,
                "reorder_enabled": True,
                "reorder_rate": 0.28,
            },
            "QUIC": {
                "profile_name": "QUIC-like Fast Secure Stream",
                "base_delay_ms": 45,
                "jitter_ms": 12,
                "drop_rate": 0.10,
                "reliable": True,
                "ordered_delivery": True,
                "ttl": 6,
                "ack_delay_ms": 42,
                "inter_packet_gap_ms": 75,
                "reorder_enabled": True,
                "reorder_rate": 0.11,
            },
        }
        return profiles.get(protocol, profiles["TCP"])
