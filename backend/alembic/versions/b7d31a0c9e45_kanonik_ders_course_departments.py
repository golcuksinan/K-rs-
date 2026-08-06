"""Course üniversite düzeyine çıkar; bölüm bağı + müfredat course_departments'a taşınır

Revision ID: b7d31a0c9e45
Revises: c3f5a8d21b74
Create Date: 2026-07-30 00:00:00.000000

Ders bölüme bağlı olduğu için ortak dersler her bölümde ayrı satırdı: 16.253 satır =
7.206 kanonik (code, name) dersi, aynı fiziksel ders N değerlendirme havuzuna bölünüyordu.

⚠️ Migration SALT ŞEMA değiştirir: veri taşıma yok, courses + course_professors boşaltılır
ve güncellenmiş seed cache'ten yeniden yazar (birleştirme mantığı tek yerde, seed'de yaşar).
universities/faculties/departments'a DOKUNULMAZ — elle yapılmış düzeltmelerin taşıyıcısı onlar.

Boşaltma DELETE ile yapılır, TRUNCATE CASCADE ile değil: reviews/reports bir course_professor'a
bağlıysa migration sessizce silmek yerine patlar (bugün reviews = 0).

downgrade yazılmadı — geri dönüş yolu yeniden seed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b7d31a0c9e45'
down_revision: Union[str, Sequence[str], None] = 'c3f5a8d21b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'course_departments',
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), primary_key=True),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), primary_key=True),
        sa.Column('semesters', postgresql.ARRAY(sa.SmallInteger()), nullable=True),
        sa.Column('is_elective', sa.Boolean(), nullable=True),
    )
    op.create_index(
        'ix_course_departments_department_id', 'course_departments', ['department_id']
    )

    # FK sırası: önce course_professors, sonra courses.
    op.execute('DELETE FROM course_professors')
    op.execute('DELETE FROM courses')

    # Tablo boş olduğu için NOT NULL doğrudan eklenebiliyor (§7'deki server_default tuzağı
    # burada geçerli değil).
    op.add_column('courses', sa.Column('university_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'fk_courses_university_id', 'courses', 'universities', ['university_id'], ['id']
    )
    op.create_index('ix_courses_university_id', 'courses', ['university_id'])

    op.drop_index('uq_department_course_name_active', table_name='courses')
    # İki kolonlu CHECK, kolonlar düşünce kendiliğinden düşmez — açıkça düşürülüyor.
    op.drop_constraint('ck_course_semester_range', 'courses', type_='check')
    op.drop_column('courses', 'semester_min')
    op.drop_column('courses', 'semester_max')
    op.drop_column('courses', 'is_elective')
    op.drop_column('courses', 'department_id')

    # Partial unique: autogenerate koşulu yakalamaz, elle yazılır (§7).
    op.create_index(
        'uq_university_course_code_name_active',
        'courses',
        ['university_id', 'code', 'name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    raise NotImplementedError('Geri dönüş yolu yeniden seed (bkz. ders-kimligi-karari.md K10).')
