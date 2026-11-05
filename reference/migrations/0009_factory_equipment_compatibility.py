# Generated for W2 B4 Factory Equipment and Compatibility

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reference', '0008_transmission_domain'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('namespace', models.TextField()),
                ('source_native_identity', models.TextField()),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='EquipmentItemRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.JSONField()),
                ('content_hash', models.CharField(max_length=71, unique=True)),
                ('revision_number', models.PositiveIntegerField()),
                ('finding', models.CharField(max_length=20)),
                ('name', models.TextField()),
                ('code', models.TextField(blank=True, null=True)),
                ('kind', models.CharField(choices=[('equipment_item', 'equipment_item'), ('factory_package', 'factory_package'), ('factory_option', 'factory_option'), ('accessory', 'accessory')], max_length=30)),
                ('installation_channel', models.CharField(choices=[('factory', 'factory'), ('manufacturer_accessory', 'manufacturer_accessory'), ('unresolved', 'unresolved')], max_length=30)),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='EquipmentOffering',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='EquipmentOfferingRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.JSONField()),
                ('content_hash', models.CharField(max_length=71, unique=True)),
                ('revision_number', models.PositiveIntegerField()),
                ('finding', models.CharField(max_length=20)),
                ('assignment', models.CharField(choices=[('standard', 'standard'), ('optional', 'optional'), ('unavailable', 'unavailable'), ('unknown', 'unknown'), ('accessory_catalogue_only', 'accessory_catalogue_only')], max_length=30)),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='CompatibilityRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='CompatibilityRuleRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.JSONField()),
                ('content_hash', models.CharField(max_length=71, unique=True)),
                ('revision_number', models.PositiveIntegerField()),
                ('finding', models.CharField(max_length=20)),
                ('rule_kind', models.CharField(choices=[('requires_all', 'requires_all'), ('requires_any', 'requires_any'), ('excludes', 'excludes'), ('includes', 'includes'), ('replaces', 'replaces'), ('cardinality', 'cardinality'), ('supports_combination', 'supports_combination')], max_length=30)),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
        ),
        migrations.RemoveConstraint(
            model_name='specificationcataloguemembership',
            name='reference_spec_membership_one_target',
        ),
        migrations.RemoveConstraint(
            model_name='specificationevidencelink',
            name='reference_spec_evidence_one_owner',
        ),
        migrations.AddField(
            model_name='equipmentitem',
            name='manufacturer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reference.manufacturer'),
        ),
        migrations.AddField(
            model_name='equipmentitemrevision',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisions', to='reference.equipmentitem'),
        ),
        migrations.AddField(
            model_name='equipmentitemrevision',
            name='supersedes',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='successor', to='reference.equipmentitemrevision'),
        ),
        migrations.AddField(
            model_name='specificationcataloguemembership',
            name='equipment_item_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='reference.equipmentitemrevision'),
        ),
        migrations.AddField(
            model_name='specificationevidencelink',
            name='equipment_item_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='reference.equipmentitemrevision'),
        ),
        migrations.AddField(
            model_name='equipmentoffering',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reference.equipmentitem'),
        ),
        migrations.AddField(
            model_name='equipmentoffering',
            name='vehicle_definition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipment_offerings', to='reference.vehicledefinition'),
        ),
        migrations.AddField(
            model_name='equipmentofferingrevision',
            name='item_revision',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reference.equipmentitemrevision'),
        ),
        migrations.AddField(
            model_name='equipmentofferingrevision',
            name='offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisions', to='reference.equipmentoffering'),
        ),
        migrations.AddField(
            model_name='equipmentofferingrevision',
            name='supersedes',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='successor', to='reference.equipmentofferingrevision'),
        ),
        migrations.AddField(
            model_name='specificationcataloguemembership',
            name='equipment_offering_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='reference.equipmentofferingrevision'),
        ),
        migrations.AddField(
            model_name='specificationevidencelink',
            name='equipment_offering_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='reference.equipmentofferingrevision'),
        ),
        migrations.AddField(
            model_name='compatibilityrule',
            name='vehicle_definition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='compatibility_rules', to='reference.vehicledefinition'),
        ),
        migrations.AddField(
            model_name='compatibilityrulerevision',
            name='rule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisions', to='reference.compatibilityrule'),
        ),
        migrations.AddField(
            model_name='compatibilityrulerevision',
            name='supersedes',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='successor', to='reference.compatibilityrulerevision'),
        ),
        migrations.AddField(
            model_name='specificationcataloguemembership',
            name='compatibility_rule_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='reference.compatibilityrulerevision'),
        ),
        migrations.AddField(
            model_name='specificationevidencelink',
            name='compatibility_rule_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='reference.compatibilityrulerevision'),
        ),
        migrations.AddConstraint(
            model_name='specificationcataloguemembership',
            constraint=models.CheckConstraint(condition=models.Q(
                models.Q(('assertion__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', False), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', False), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', False), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', False)),
                models.Q(('assertion__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', False), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', False), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('compatibility_rule_revision__isnull', False), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                _connector='OR'
            ), name='reference_spec_membership_one_target'),
        ),
        migrations.AddConstraint(
            model_name='specificationcataloguemembership',
            constraint=models.UniqueConstraint(fields=('catalogue_revision', 'equipment_item_revision'), name='reference_spec_member_equipment_item'),
        ),
        migrations.AddConstraint(
            model_name='specificationcataloguemembership',
            constraint=models.UniqueConstraint(fields=('catalogue_revision', 'equipment_offering_revision'), name='reference_spec_member_equipment_offer'),
        ),
        migrations.AddConstraint(
            model_name='specificationcataloguemembership',
            constraint=models.UniqueConstraint(fields=('catalogue_revision', 'compatibility_rule_revision'), name='reference_spec_member_compat_rule'),
        ),
        migrations.AddConstraint(
            model_name='specificationevidencelink',
            constraint=models.CheckConstraint(condition=models.Q(
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', False), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', False), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', False), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', False), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', False)),
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', False), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', True), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', False), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                models.Q(('assertion__isnull', True), ('catalogue_revision__isnull', True), ('compatibility_rule_revision__isnull', False), ('definition_revision__isnull', True), ('equipment_item_revision__isnull', True), ('equipment_offering_revision__isnull', True), ('transmission_description_revision__isnull', True), ('transmission_offering_revision__isnull', True)),
                _connector='OR'
            ), name='reference_spec_evidence_one_owner'),
        ),
        migrations.AddConstraint(
            model_name='specificationevidencelink',
            constraint=models.UniqueConstraint(fields=('equipment_item_revision', 'position'), name='reference_spec_link_equipment_item'),
        ),
        migrations.AddConstraint(
            model_name='specificationevidencelink',
            constraint=models.UniqueConstraint(fields=('equipment_offering_revision', 'position'), name='reference_spec_link_equipment_offer'),
        ),
        migrations.AddConstraint(
            model_name='specificationevidencelink',
            constraint=models.UniqueConstraint(fields=('compatibility_rule_revision', 'position'), name='reference_spec_link_compat_rule'),
        ),
        migrations.AddConstraint(
            model_name='equipmentitemrevision',
            constraint=models.UniqueConstraint(fields=('item', 'revision_number'), name='reference_equipment_item_revision'),
        ),
        migrations.AddConstraint(
            model_name='equipmentitemrevision',
            constraint=models.CheckConstraint(condition=models.Q(('revision_number__gte', 1)), name='reference_equipment_item_positive'),
        ),
        migrations.AddConstraint(
            model_name='equipmentitemrevision',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('revision_number', 1), ('supersedes__isnull', True)), models.Q(('revision_number__gt', 1), ('supersedes__isnull', False)), _connector='OR'), name='reference_equipment_item_predecessor'),
        ),
        migrations.AddConstraint(
            model_name='equipmentofferingrevision',
            constraint=models.UniqueConstraint(fields=('offering', 'revision_number'), name='reference_equipment_offer_revision'),
        ),
        migrations.AddConstraint(
            model_name='equipmentofferingrevision',
            constraint=models.CheckConstraint(condition=models.Q(('revision_number__gte', 1)), name='reference_equipment_offer_positive'),
        ),
        migrations.AddConstraint(
            model_name='equipmentofferingrevision',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('revision_number', 1), ('supersedes__isnull', True)), models.Q(('revision_number__gt', 1), ('supersedes__isnull', False)), _connector='OR'), name='reference_equipment_offer_predecessor'),
        ),
        migrations.AddConstraint(
            model_name='compatibilityrulerevision',
            constraint=models.UniqueConstraint(fields=('rule', 'revision_number'), name='reference_compat_rule_revision'),
        ),
        migrations.AddConstraint(
            model_name='compatibilityrulerevision',
            constraint=models.CheckConstraint(condition=models.Q(('revision_number__gte', 1)), name='reference_compat_rule_positive'),
        ),
        migrations.AddConstraint(
            model_name='compatibilityrulerevision',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('revision_number', 1), ('supersedes__isnull', True)), models.Q(('revision_number__gt', 1), ('supersedes__isnull', False)), _connector='OR'), name='reference_compat_rule_predecessor'),
        ),
    ]
