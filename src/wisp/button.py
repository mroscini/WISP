from __future__ import annotations

from datetime import timedelta
from typing import Callable


def watch_gpio_button(
    chip: str,
    line_offset: int,
    callback: Callable[[], None],
    *,
    edge: str = "falling",
    debounce_ms: int = 80,
) -> None:
    """Block forever and invoke callback for each debounced physical button press."""
    try:
        import gpiod
        from gpiod.line import Bias, Edge
    except ImportError as error:
        raise RuntimeError("Installa il componente hardware gpiod") from error

    edge_type = Edge.FALLING if edge == "falling" else Edge.RISING
    settings = gpiod.LineSettings(
        edge_detection=edge_type,
        bias=Bias.PULL_UP,
        debounce_period=timedelta(milliseconds=debounce_ms),
    )
    with gpiod.request_lines(
        chip,
        consumer="wisp-talk-button",
        config={line_offset: settings},
    ) as request:
        while True:
            for _event in request.read_edge_events():
                callback()

