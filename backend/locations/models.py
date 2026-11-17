from django.db import models

# Addresses (domicilios). The country is always Mexico and the state and the municipality come
# from INEGI's web service (see inegi.py): they are NOT catalog tables here, the address just
# keeps the chosen names as text, like the colonia and the street.
# Python names are in English; table and column names in the database are in Spanish
# (db_table / db_column).


class Address(models.Model):
    """
    Domicilio: the state and the municipality (names from INEGI), the colonia and the street
    as free text, and the exterior and interior numbers.
    Belongs to one user.
    """

    state = models.CharField("estado", max_length=100, db_column="estado")
    municipality = models.CharField("municipio", max_length=100, db_column="municipio")
    neighborhood = models.CharField("colonia", max_length=150, db_column="colonia")
    street = models.CharField("calle", max_length=150, db_column="calle")
    # Text, not integers: numbers can be "12-A", "S/N", "B-3"...
    exterior_number = models.CharField(
        "número exterior", max_length=20, db_column="numero_exterior"
    )
    interior_number = models.CharField(
        "número interior", max_length=20, blank=True, db_column="numero_interior"
    )

    class Meta:
        db_table = "domicilios"
        verbose_name = "domicilio"
        verbose_name_plural = "domicilios"

    def __str__(self):
        return f"{self.street} {self.exterior_number}, {self.neighborhood}, {self.municipality}, {self.state}"
