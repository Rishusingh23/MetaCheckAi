"""initial_phase2_schema

Revision ID: 0001_initial_phase2_schema
Revises: 
Create Date: 2026-09-14 22:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_phase2_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # 2. users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)

    # 3. products table
    op.create_table(
        'products',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('brand', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('packer', sa.String(length=255), nullable=True),
        sa.Column('importer', sa.String(length=255), nullable=True),
        sa.Column('barcode_gtin', sa.String(length=50), nullable=True),
        sa.Column('country_of_origin', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_brand'), 'products', ['brand'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_barcode_gtin'), 'products', ['barcode_gtin'], unique=False)

    # 4. product_images table
    op.create_table(
        'product_images',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('image_url_or_path', sa.String(length=500), nullable=False),
        sa.Column('image_type', sa.String(length=50), nullable=False),
        sa.Column('file_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False)

    # 5. inspections table
    op.create_table(
        'inspections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('inspector_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('overall_result_placeholder', sa.String(length=50), nullable=False),
        sa.Column('inspection_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspector_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspections_product_id'), 'inspections', ['product_id'], unique=False)
    op.create_index(op.f('ix_inspections_inspector_id'), 'inspections', ['inspector_id'], unique=False)
    op.create_index(op.f('ix_inspections_status'), 'inspections', ['status'], unique=False)
    op.create_index(op.f('ix_inspections_overall_result_placeholder'), 'inspections', ['overall_result_placeholder'], unique=False)
    op.create_index(op.f('ix_inspections_inspection_date'), 'inspections', ['inspection_date'], unique=False)

    # 6. scans table
    op.create_table(
        'scans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('product_image_id', sa.String(length=36), nullable=True),
        sa.Column('image_path', sa.String(length=500), nullable=False),
        sa.Column('panel_type', sa.String(length=50), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_image_id'], ['product_images.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scans_inspection_id'), 'scans', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_scans_processing_status'), 'scans', ['processing_status'], unique=False)

    # 7. ocr_results table
    op.create_table(
        'ocr_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('scan_id', sa.String(length=36), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('bounding_boxes', sa.JSON(), nullable=True),
        sa.Column('ocr_engine', sa.String(length=100), nullable=True),
        sa.Column('processing_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_results_scan_id'), 'ocr_results', ['scan_id'], unique=False)

    # 8. declarations table
    op.create_table(
        'declarations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('scan_id', sa.String(length=36), nullable=False),
        sa.Column('declaration_type', sa.String(length=50), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('extraction_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_declarations_scan_id'), 'declarations', ['scan_id'], unique=False)
    op.create_index(op.f('ix_declarations_declaration_type'), 'declarations', ['declaration_type'], unique=False)

    # 9. rules table
    op.create_table(
        'rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rule_code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('legal_reference', sa.String(length=500), nullable=False, comment='Authoritative statutory source reference, e.g. PCR 2011 Rule 6(1)'),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rules_rule_code'), 'rules', ['rule_code'], unique=True)

    # 10. rule_versions table
    op.create_table(
        'rule_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rule_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('requirement_text', sa.Text(), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('applicable_product_categories', sa.JSON(), nullable=True),
        sa.Column('validation_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('evidence_required', sa.Boolean(), nullable=False),
        sa.Column('source_gazette_reference', sa.String(length=500), nullable=True),
        sa.Column('active_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rule_versions_rule_id'), 'rule_versions', ['rule_id'], unique=False)

    # 11. compliance_checks table
    op.create_table(
        'compliance_checks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('rule_version_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('detected_value', sa.Text(), nullable=True),
        sa.Column('expected_requirement', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_version_id'], ['rule_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_checks_inspection_id'), 'compliance_checks', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_compliance_checks_rule_version_id'), 'compliance_checks', ['rule_version_id'], unique=False)
    op.create_index(op.f('ix_compliance_checks_status'), 'compliance_checks', ['status'], unique=False)

    # 12. violations table
    op.create_table(
        'violations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('compliance_check_id', sa.String(length=36), nullable=True),
        sa.Column('violation_code', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['compliance_check_id'], ['compliance_checks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_violations_inspection_id'), 'violations', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_violations_compliance_check_id'), 'violations', ['compliance_check_id'], unique=False)
    op.create_index(op.f('ix_violations_violation_code'), 'violations', ['violation_code'], unique=False)
    op.create_index(op.f('ix_violations_status'), 'violations', ['status'], unique=False)

    # 13. evidences table
    op.create_table(
        'evidences',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('violation_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('image_url_or_path', sa.String(length=500), nullable=True),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['violation_id'], ['violations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidences_inspection_id'), 'evidences', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_evidences_violation_id'), 'evidences', ['violation_id'], unique=False)

    # 14. reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=False),
        sa.Column('generated_by', sa.String(length=36), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_inspection_id'), 'reports', ['inspection_id'], unique=False)

    # 15. inspection_histories table
    op.create_table(
        'inspection_histories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('change_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_histories_inspection_id'), 'inspection_histories', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_inspection_histories_user_id'), 'inspection_histories', ['user_id'], unique=False)
    op.create_index(op.f('ix_inspection_histories_timestamp'), 'inspection_histories', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('inspection_histories')
    op.drop_table('reports')
    op.drop_table('evidences')
    op.drop_table('violations')
    op.drop_table('compliance_checks')
    op.drop_table('rule_versions')
    op.drop_table('rules')
    op.drop_table('declarations')
    op.drop_table('ocr_results')
    op.drop_table('scans')
    op.drop_table('inspections')
    op.drop_table('product_images')
    op.drop_table('products')
    op.drop_table('users')
    op.drop_table('roles')
