from django.db import migrations


def fix_menu_table_if_needed(apps, schema_editor):
    """La tabla `menu` en algunas bases de datos (las que ya existian antes de
    esta migracion) fue sobrescrita en algun momento por una tabla de datos de
    alimentos heredada del sistema legado (food_name, kcal_100g, prot_g...),
    con columnas que no coinciden con el modelo Menu (date_ini, date_fin,
    user_id). En una base de datos nueva, 0001_initial ya crea la tabla
    correctamente, por lo que aqui se comprueba el estado real antes de
    actuar: si la tabla ya tiene la columna `date_ini` no hay nada que hacer.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'menu' AND COLUMN_NAME = 'date_ini'"
        )
        (already_correct,) = cursor.fetchone()
        if already_correct:
            return

        cursor.execute("RENAME TABLE `menu` TO `menu_legacy_unused_food_data`;")
        cursor.execute(
            "CREATE TABLE `menu` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, "
            "`date_ini` date NOT NULL, `date_fin` date NOT NULL, `user_id` bigint NOT NULL);"
        )
        cursor.execute(
            "ALTER TABLE `menu` ADD CONSTRAINT `menu_user_id_ed5e005d_fk_user_id` "
            "FOREIGN KEY (`user_id`) REFERENCES `user` (`id`);"
        )
        cursor.execute(
            "ALTER TABLE `menu_intake` DROP FOREIGN KEY `menu_intake_menu_id_699ad3c4_fk_menu_id`;"
        )
        cursor.execute(
            "ALTER TABLE `menu_intake` ADD CONSTRAINT `menu_intake_menu_id_699ad3c4_fk_menu_id` "
            "FOREIGN KEY (`menu_id`) REFERENCES `menu` (`id`);"
        )


def undo_fix_menu_table_if_needed(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'menu_legacy_unused_food_data'"
        )
        (legacy_table_exists,) = cursor.fetchone()
        if not legacy_table_exists:
            return

        cursor.execute(
            "ALTER TABLE `menu_intake` DROP FOREIGN KEY `menu_intake_menu_id_699ad3c4_fk_menu_id`;"
        )
        cursor.execute("DROP TABLE `menu`;")
        cursor.execute("RENAME TABLE `menu_legacy_unused_food_data` TO `menu`;")
        cursor.execute(
            "ALTER TABLE `menu_intake` ADD CONSTRAINT `menu_intake_menu_id_699ad3c4_fk_menu_id` "
            "FOREIGN KEY (`menu_id`) REFERENCES `menu` (`id`);"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('Menus', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_menu_table_if_needed, undo_fix_menu_table_if_needed),
    ]
