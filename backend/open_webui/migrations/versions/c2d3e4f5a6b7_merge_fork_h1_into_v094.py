"""Merge fork scheduled-prompt head into v0.9.4 migration chain

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f6a7, h1j2k3l4m5n6
Create Date: 2026-05-10 11:46:00.000000

"""

from typing import Sequence, Union


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, tuple[str, str]] = ('b1c2d3e4f6a7', 'h1j2k3l4m5n6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
