"""Backend MySQL que permite servidores 5.7 (Django 5.x exige 8.0.11).

Django activa/desactiva funciones según la versión real del servidor, así que
solo se relaja la verificación de versión mínima y se recupera la sintaxis de
renombrar columnas de 5.7. Con MySQL 8 se comporta igual que el backend estándar.
"""
from django.db.backends.mysql import base, features, schema


class DatabaseFeatures(features.DatabaseFeatures):
    minimum_database_version = (5, 7, 8)


class DatabaseSchemaEditor(schema.DatabaseSchemaEditor):
    @property
    def sql_rename_column(self):
        # "ALTER TABLE ... RENAME COLUMN" existe a partir de MySQL 8.0.4.
        if not self.connection.mysql_is_mariadb and self.connection.mysql_version < (8, 0, 4):
            return "ALTER TABLE %(table)s CHANGE %(old_column)s %(new_column)s %(type)s"
        return super().sql_rename_column


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
    SchemaEditorClass = DatabaseSchemaEditor
