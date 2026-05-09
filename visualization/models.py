from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Packet:
    packet_id: int
    seq_no: int
    total_packets: int
    chunk_index: int
    payload: str
    size_bytes: int
    checksum: str
    ttl: int
    status: str
    delay_ms: int
    attempt_no: int = 1
    acked: bool = False
    dropped: bool = False
    retransmit_count: int = 0
    sent_at_ms: int = 0
    delivered_at_ms: Optional[int] = None
    notes: str = ""


@dataclass
class SimulationEvent:
    time_ms: int
    packet_id: int
    stage: str
    description: str
    color: str
    lane: str


@dataclass
class SimulationResult:
    protocol: str
    original_message: str
    reassembled_message: str
    packets: List[Packet]
    events: List[SimulationEvent]
    dropped_packets: int
    retransmissions: int
    delivered_packets: int
    total_packets: int
    total_time_ms: int
    ordered_delivery: bool
    network_profile_name: str
