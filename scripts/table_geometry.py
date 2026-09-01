"""Geometria OOXML autocontida para tabelas geradas com python-docx."""

from __future__ import annotations

from collections.abc import Sequence

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Twips


DEFAULT_CELL_MARGINS_DXA = {"top": 80, "bottom": 80, "start": 120, "end": 120}


def section_content_width_dxa(section) -> int:
    """Calcula a largura útil da seção em twips (DXA)."""

    return int(
        round(
            section.page_width.twips
            - section.left_margin.twips
            - section.right_margin.twips
        )
    )


def column_widths_from_weights(
    weights: Sequence[float], total_width_dxa: int
) -> list[int]:
    """Distribui a largura total e preserva a soma exata após arredondamento."""

    if not weights or any(weight <= 0 for weight in weights):
        raise ValueError("weights deve conter apenas valores positivos")
    total_weight = float(sum(weights))
    widths = [
        int(round(total_width_dxa * weight / total_weight)) for weight in weights
    ]
    widths[-1] += int(total_width_dxa) - sum(widths)
    return widths


def _ensure_child(parent, tag: str):
    child = parent.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        parent.append(child)
    return child


def _set_width(parent, tag: str, width_dxa: int) -> None:
    width = _ensure_child(parent, tag)
    width.set(qn("w:type"), "dxa")
    width.set(qn("w:w"), str(int(width_dxa)))


def apply_table_geometry(
    table,
    column_widths_dxa: Sequence[int],
    *,
    table_width_dxa: int | None = None,
    indent_dxa: int | None = None,
    cell_margins_dxa: dict[str, int] | None = None,
) -> None:
    """Sincroniza largura da tabela, grade, colunas, células e margens."""

    widths = [int(width) for width in column_widths_dxa]
    if not widths or any(width <= 0 for width in widths):
        raise ValueError("column_widths_dxa deve conter apenas valores positivos")
    total = int(table_width_dxa if table_width_dxa is not None else sum(widths))
    if sum(widths) != total:
        raise ValueError("a soma das colunas deve ser igual à largura da tabela")

    margins = dict(DEFAULT_CELL_MARGINS_DXA)
    if cell_margins_dxa:
        margins.update({key: int(value) for key, value in cell_margins_dxa.items()})
    indent = margins["start"] if indent_dxa is None else int(indent_dxa)

    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table_properties = table._tbl.tblPr
    _set_width(table_properties, "w:tblW", total)
    table_indent = _ensure_child(table_properties, "w:tblInd")
    table_indent.set(qn("w:type"), "dxa")
    table_indent.set(qn("w:w"), str(indent))
    layout = _ensure_child(table_properties, "w:tblLayout")
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        grid_column = OxmlElement("w:gridCol")
        grid_column.set(qn("w:w"), str(width))
        grid.append(grid_column)

    for index, width in enumerate(widths):
        table.columns[index].width = Twips(width)
    for row in table.rows:
        if len(row.cells) != len(widths):
            raise ValueError("a geometria exige linhas sem células mescladas")
        for index, cell in enumerate(row.cells):
            width = widths[index]
            cell.width = Twips(width)
            cell_properties = cell._tc.get_or_add_tcPr()
            _set_width(cell_properties, "w:tcW", width)
            cell_margins = _ensure_child(cell_properties, "w:tcMar")
            for side in ("top", "bottom", "start", "end"):
                margin = _ensure_child(cell_margins, f"w:{side}")
                margin.set(qn("w:type"), "dxa")
                margin.set(qn("w:w"), str(margins[side]))
