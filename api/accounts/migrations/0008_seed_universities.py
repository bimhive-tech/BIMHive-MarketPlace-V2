"""Starter list for the signup university dropdown.

Without rows the dropdown has nothing to offer and every student falls through
to the "Other" free-text box, so the field ships with the Egyptian universities
that actually run architecture/engineering programmes — BIMHIVE's home market.
It is a starting point, not a closed list: staff add to it in Django admin, and
"Other" still accepts anything.

Idempotent (get_or_create by name) and non-destructive in reverse, so it never
touches a row someone has since edited or deactivated.
"""

from django.db import migrations

EGYPT_UNIVERSITIES = [
    "Ain Shams University",
    "Al-Azhar University",
    "Alamein International University",
    "Alexandria University",
    "Arab Academy for Science, Technology and Maritime Transport",
    "Assiut University",
    "Aswan University",
    "Badr University in Cairo",
    "Beni-Suef University",
    "Benha University",
    "British University in Egypt",
    "Cairo University",
    "Damietta University",
    "Delta University for Science and Technology",
    "Egypt-Japan University of Science and Technology",
    "Egyptian Chinese University",
    "Egyptian Russian University",
    "Fayoum University",
    "Future University in Egypt",
    "Galala University",
    "German University in Cairo",
    "Heliopolis University",
    "Helwan University",
    "Higher Technological Institute",
    "Kafrelsheikh University",
    "King Salman International University",
    "Mansoura University",
    "Menoufia University",
    "Minia University",
    "Misr International University",
    "Misr University for Science and Technology",
    "Modern Academy in Maadi",
    "Nile University",
    "October 6 University",
    "Pharos University in Alexandria",
    "Port Said University",
    "Sohag University",
    "South Valley University",
    "Suez Canal University",
    "Tanta University",
    "The American University in Cairo",
    "Zagazig University",
]


def seed(apps, schema_editor):
    University = apps.get_model("accounts", "University")
    for name in EGYPT_UNIVERSITIES:
        University.objects.get_or_create(name=name, defaults={"country": "EG"})


def unseed(apps, schema_editor):
    """Deliberately a no-op: a rollback shouldn't delete rows staff may have
    edited, and an orphaned university only ever shows up as a dropdown entry.
    """


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_signup_student_university")]

    operations = [migrations.RunPython(seed, unseed)]
