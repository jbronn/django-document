from django.db.migrations.operations.base import Operation


class AddJSONIndex(Operation):
    """
    Adds a GIN index on PostgreSQL jsonb field.
    """

    sql = 'CREATE INDEX %(name)s ON %(table)s USING GIN (%(columns)s)%(extra)s'
    sql_path_ops = 'CREATE INDEX %(name)s ON %(table)s USING GIN (%(columns)s jsonb_path_ops)%(extra)s'

    def __init__(self, model_name, field_name, path_ops=False):
        self.model_name = model_name
        self.field_name = field_name
        self.path_ops = path_ops

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)

        if self.allow_migrate_model(schema_editor.connection.alias, model):
            field = model._meta.get_field(self.field_name)

            if self.path_ops:
                sql = self.sql_path_ops
            else:
                sql = self.sql

            schema_editor.deferred_sql.append(
                schema_editor._create_index_sql(model, [field], sql=sql, suffix='_gin')
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)

        if self.allow_migrate_model(schema_editor.connection.alias, model):
            field = model._meta.get_field(self.field_name)

            schema_editor.deferred_sql.append(
                schema_editor.sql_delete_index % {
                    'name': schema_editor._create_index_name(model, [field.column], suffix='_gin')
                }
            )

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'field_name': self.field_name,
            'path_ops': self.path_ops
        }
        return (
            self.__class__.__name__,
            [],
            kwargs,
        )

    def describe(self):
        return 'Create GIN index on field %s of model %s' % (
            self.field_name,
            self.model_name,
        )


class AddUniqueKeyIndex(Operation):
    """
    Adds an index and constraint to ensure that a jsonb field has unique value
    for the specified key.
    """

    uniq_sql = (
        'CREATE UNIQUE INDEX %%(name)s ON %%(table)s '
        '(((%%(columns)s)->>%(key)s::%(value_type)s))%%(extra)s'
    )

    add_check_sql = (
        'ALTER TABLE %%(table)s ADD CONSTRAINT %%(name)s '
        'CHECK (%%(columns)s ? %(key)s)%%(extra)s'
    )

    del_check_sql = 'ALTER TABLE %(table)s DROP CONSTRAINT %(name)s'

    def __init__(self, model_name, field_name, key, value_type='text'):
        self.model_name = model_name
        self.field_name = field_name
        self.key = key
        self.value_type = value_type
        self.suffix = '_%s_uniq' % self.key

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)

        if self.allow_migrate_model(schema_editor.connection.alias, model):
            field = model._meta.get_field(self.field_name)

            uniq_sql = self.uniq_sql % {
                'key': schema_editor.quote_value(self.key),
                'value_type': self.value_type
            }

            check_sql = self.add_check_sql % {
                'key': schema_editor.quote_value(self.key),
            }

            schema_editor.deferred_sql.extend([
                schema_editor._create_index_sql(model, [field], sql=uniq_sql,
                                                suffix=self.suffix),
                schema_editor._create_index_sql(model, [field], sql=check_sql,
                                                suffix=self.suffix),
            ])

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)

        if self.allow_migrate_model(schema_editor.connection.alias, model):
            field = model._meta.get_field(self.field_name)

            idx_name = schema_editor._create_index_name(
                model, [field.column], suffix=self.suffix
            )
            
            schema_editor.deferred_sql.extend([
                self.del_check_sql % {
                    'name': schema_editor.quote_name(idx_name),
                    'table': schema_editor.quote_name(model._meta.db_table),
                },
                schema_editor.sql_delete_index % {
                    'name': schema_editor.quote_name(idx_name)
                }
            ])

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'field_name': self.field_name,
            'key': self.key,
            'value_type': self.value_type
        }
        return (
            self.__class__.__name__,
            [],
            kwargs,
        )

    def describe(self):
        return 'Create unique index on %s (%s::%s) of model %s' % (
            self.field_name,
            self.key,
            self.value_type,
            self.model_name,
        )
