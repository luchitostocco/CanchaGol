from django.db import migrations


def cargar_modalidades(apps, schema_editor):
    TipoCancha = apps.get_model("agenda", "TipoCancha")
    for codigo in ("F5", "F7", "F8", "F11"):
        TipoCancha.objects.using(schema_editor.connection.alias).get_or_create(codigo=codigo)


class Migration(migrations.Migration):
    dependencies = [("agenda", "0001_initial")]
    operations = [migrations.RunPython(cargar_modalidades, migrations.RunPython.noop)]
