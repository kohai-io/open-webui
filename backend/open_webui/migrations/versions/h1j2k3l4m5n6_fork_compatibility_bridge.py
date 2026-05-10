"""Fork compatibility bridge for scheduled prompts

Revision ID: h1j2k3l4m5n6
Revises: a5c220713937
Create Date: 2026-05-10 11:45:00.000000

"""

from typing import Sequence, Union


revision: str = 'h1j2k3l4m5n6'
down_revision: Union[str, None] = 'a5c220713937'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
