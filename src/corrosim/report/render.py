"""corrosim.report.render.

The one place the data-driven "Scientific basis & validation" block list
(:data:`report_content.SCIENTIFIC_BASIS`) is turned into a concrete format. The
HTML and Word renderers each implement :class:`BasisRenderer`, and
:func:`render_blocks` walks the block list once and dispatches each
``(kind, payload)`` item to the renderer, raising on an unknown kind.
Centralising the dispatch here means the
two outputs cannot silently drift when a block kind is added — the old per-
renderer ``if kind == …`` chains had no ``else`` and quietly dropped anything
unhandled.

Scope is deliberately narrow: only the *data-driven* Scientific-basis section
flows through this seam. The hand-authored, format-specific sections stay two
separate renderers — the narrative is fixed as static prose, so promoting the
whole report to a generic block model would buy nothing.

::

    SCIENTIFIC_BASIS ---> render_blocks ---> renderer.subheading / paragraph
      [(kind, payload)]         |                 / table / equation_groups
                                +-- unknown kind ---> raise ValueError
"""
from __future__ import annotations

from typing import Protocol


class BasisRenderer(Protocol):
    """The four operations a format must provide to render SCIENTIFIC_BASIS.

    HTML (``report``) and Word (``report_docx``) each supply a concrete
    implementation; :func:`render_blocks` calls these and nothing else.
    """

    def subheading(self, text: str) -> None:
        """Render a subsection heading.

        Args:
            text: The heading text.
        """
        ...

    def paragraph(self, text: str) -> None:
        """Render a prose paragraph (``**bold**`` markup via ``inline_runs``).

        Args:
            text: The paragraph text.
        """
        ...

    def table(self, payload: dict) -> None:
        """Render a content table.

        Args:
            payload: A ``{columns, rows, caption}`` table dict.
        """
        ...

    def equation_groups(self) -> None:
        """Render the governing-equation set (``equations.EQUATION_GROUPS``)."""
        ...


def render_blocks(blocks: list[tuple[str, object]],
                  renderer: BasisRenderer) -> None:
    """Dispatch each Scientific-basis block to ``renderer``, in order.

    The ``kind`` set is exhaustive: an unrecognised block (or a payload of the
    wrong type for its kind) raises rather than being silently dropped, so the
    HTML and Word outputs stay in lock-step as blocks are added.

    Args:
        blocks: ``(kind, payload)`` items, e.g.
            ``report_content.SCIENTIFIC_BASIS``.
        renderer: The concrete :class:`BasisRenderer` for the output format.

    Raises:
        ValueError: If a block's kind is unknown or its payload type is wrong.
    """
    for kind, payload in blocks:
        if kind == "h3" and isinstance(payload, str):
            renderer.subheading(payload)
        elif kind == "p" and isinstance(payload, str):
            renderer.paragraph(payload)
        elif kind == "table" and isinstance(payload, dict):
            renderer.table(payload)
        elif kind == "eqgroups":
            renderer.equation_groups()
        else:
            raise ValueError(f"unknown scientific-basis block: {kind!r}")
