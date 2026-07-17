"""Bounded, non-sensitive psutil telemetry collection."""

from __future__ import annotations

import os
import socket
from datetime import UTC, datetime

import psutil

from fleetpulse.telemetry import (
    DiskTelemetry,
    MemoryTelemetry,
    NetworkTelemetry,
    ProcessTelemetry,
    TelemetrySample,
)


def _top_processes(limit: int = 10) -> tuple[int, list[ProcessTelemetry]]:
    process_count = 0
    processes: list[ProcessTelemetry] = []
    for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        process_count += 1
        try:
            info = process.info
            name = str(info.get("name") or "unknown")[:256]
            processes.append(
                ProcessTelemetry(
                    pid=int(info["pid"]),
                    name=name,
                    cpu_percent=max(0.0, float(info.get("cpu_percent") or 0.0)),
                    memory_percent=max(0.0, min(100.0, float(info.get("memory_percent") or 0.0))),
                )
            )
        except (psutil.AccessDenied, psutil.NoSuchProcess, ValueError, TypeError):
            continue
    processes.sort(key=lambda item: (item.cpu_percent, item.memory_percent), reverse=True)
    return process_count, processes[:limit]


def _network_telemetry() -> NetworkTelemetry:
    counters = psutil.net_io_counters()
    tcp_established = 0
    tcp_listening = 0
    tcp_other = 0
    udp_sockets = 0
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        connections = []
    for connection in connections:
        if connection.type == socket.SOCK_DGRAM:
            udp_sockets += 1
        elif connection.type == socket.SOCK_STREAM:
            if connection.status == psutil.CONN_ESTABLISHED:
                tcp_established += 1
            elif connection.status == psutil.CONN_LISTEN:
                tcp_listening += 1
            else:
                tcp_other += 1
    return NetworkTelemetry(
        bytes_sent=counters.bytes_sent,
        bytes_received=counters.bytes_recv,
        packets_sent=counters.packets_sent,
        packets_received=counters.packets_recv,
        errors_in=counters.errin,
        errors_out=counters.errout,
        drops_in=counters.dropin,
        drops_out=counters.dropout,
        tcp_established=tcp_established,
        tcp_listening=tcp_listening,
        tcp_other=tcp_other,
        udp_sockets=udp_sockets,
    )


def collect_sample() -> TelemetrySample:
    """Collect one host/container snapshot without command lines or environments."""
    memory = psutil.virtual_memory()
    root_disk = psutil.disk_usage("/")
    process_count, processes = _top_processes()
    load_1m, load_5m, load_15m = os.getloadavg()
    return TelemetrySample(
        observed_at=datetime.now(UTC),
        cpu_percent=psutil.cpu_percent(interval=None),
        load_1m=max(0.0, load_1m),
        load_5m=max(0.0, load_5m),
        load_15m=max(0.0, load_15m),
        memory=MemoryTelemetry(
            total_bytes=memory.total,
            available_bytes=memory.available,
            used_bytes=memory.used,
            used_percent=memory.percent,
        ),
        disks=[
            DiskTelemetry(
                mount="/",
                total_bytes=root_disk.total,
                used_bytes=root_disk.used,
                free_bytes=root_disk.free,
                used_percent=root_disk.percent,
            )
        ],
        network=_network_telemetry(),
        process_count=process_count,
        top_processes=processes,
    )
